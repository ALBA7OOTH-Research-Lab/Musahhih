#!/usr/bin/env python3
"""Execute the single matched F2/F3 Nahw-Passage evaluation when authorized."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import gc
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess

from scripts.f2_f3_eval_utils import (
    ARM_SPECS,
    BASE_MODEL_ID,
    BASE_MODEL_REVISION,
    BOOTSTRAP_SAMPLES,
    CONFIRMATION,
    EXPECTED_BASELINE_PREDICTIONS_SHA256,
    EXPECTED_F1_PREDICTIONS_SHA256,
    EXPECTED_TEST_SHA256,
    MAX_NEW_TOKENS,
    RUN_ID,
    SEED,
    EvaluationSafetyError,
    load_and_validate_nahw_records,
    load_validated_reference_predictions,
    matched_comparisons,
    require_execution_authorization,
    sha256_file,
    validate_adapter_checkpoint,
)
from scripts.nahw_baseline_utils import parse_model_response, summarize_predictions


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUTS = ROOT / "outputs"


def _versions() -> dict:
    packages = {}
    for name in ("torch", "transformers", "unsloth", "accelerate", "peft", "trl"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {"python": platform.python_version(), "packages": packages}


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def validate_outputs_root(path: Path) -> Path:
    """Keep all record-level final-test artifacts under an ignored tree."""

    resolved = Path(path).expanduser().resolve()
    if _is_relative_to(resolved, ROOT) and not _is_relative_to(
        resolved, DEFAULT_OUTPUTS.resolve()
    ):
        raise EvaluationSafetyError(
            "repository-local final outputs must stay under ignored outputs/"
        )
    return resolved


class AdapterGenerator:
    """Pinned 4-bit base plus one verified, unmerged private adapter."""

    def __init__(self, adapter: Path) -> None:
        self.adapter = Path(adapter)
        self.model = None
        self.processor = None
        self.runtime = _versions()

    def load(self) -> None:
        try:
            import torch
            from peft import PeftModel
            from unsloth import FastModel
        except (ImportError, OSError) as error:
            raise EvaluationSafetyError("GPU inference dependencies unavailable") from error
        if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
            raise EvaluationSafetyError("exactly one CUDA GPU is required")
        properties = torch.cuda.get_device_properties(0)
        if "P100" not in properties.name:
            raise EvaluationSafetyError("matched final evaluation requires a P100")
        try:
            base, self.processor = FastModel.from_pretrained(
                model_name=BASE_MODEL_ID,
                revision=BASE_MODEL_REVISION,
                max_seq_length=2048,
                dtype=None,
                load_in_4bit=True,
                full_finetuning=False,
            )
            self.model = PeftModel.from_pretrained(
                base, str(self.adapter), is_trainable=False
            )
            if hasattr(FastModel, "for_inference"):
                FastModel.for_inference(self.model)
            self.model.eval()
        except Exception as error:
            raise EvaluationSafetyError("unable to load pinned base and adapter") from error
        self.runtime.update(
            {
                "cuda": torch.version.cuda,
                "gpu": properties.name,
                "gpu_total_memory_bytes": properties.total_memory,
                "dtype_argument": None,
                "load_in_4bit": True,
                "adapter_merged": False,
            }
        )

    def __call__(self, prompt: str) -> str:
        if self.model is None or self.processor is None:
            self.load()
        messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
        inputs = self.processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(self.model.device)
        input_length = int(inputs["input_ids"].shape[-1])
        if input_length > 2048:
            raise EvaluationSafetyError("Nahw prompt exceeds 2048 tokens; no truncation")
        outputs = self.model.generate(
            **inputs, do_sample=False, max_new_tokens=MAX_NEW_TOKENS
        )
        return self.processor.decode(
            outputs[0][input_length:], skip_special_tokens=True
        )


def _release_generator(generator: AdapterGenerator) -> None:
    generator.model = None
    generator.processor = None
    del generator
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
    except (ImportError, RuntimeError):
        pass


def _generate_arm(
    *,
    arm: str,
    adapter: Path,
    records: list[dict],
    predictions_path: Path,
) -> tuple[list[dict], dict]:
    rows: list[dict] = []
    generator = AdapterGenerator(adapter)
    try:
        with predictions_path.open("x", encoding="utf-8", newline="\n") as stream:
            for record in records:
                raw = generator(record["prompt"])
                parsed, warnings = parse_model_response(raw)
                row = {
                    "record_id": record["id"],
                    "passage_id": record["passage_id"],
                    "source": record["source"],
                    "split": record["split"],
                    "passage": record["passage"],
                    "erroneous_word": record["error"],
                    "gold_correction": record["gold_correction"],
                    "full_prompt": record["prompt"],
                    "raw_model_response": raw,
                    "parsed_correction": parsed,
                    "exact_match": parsed == record["gold_correction"],
                    "parsing_warnings": warnings,
                }
                stream.write(
                    json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                )
                stream.flush()
                rows.append(row)
        if len(rows) != 511:
            raise EvaluationSafetyError(f"{arm} did not complete exactly 511 records")
        return rows, generator.runtime
    finally:
        _release_generator(generator)


def execute(
    args: argparse.Namespace,
    *,
    records: list[dict],
    b0_rows: list[dict],
    f1_rows: list[dict],
    adapter_meta: dict[str, dict],
) -> dict:
    run_id = RUN_ID.replace("__r01", f"__r{args.replicate:02d}")
    run_dir = validate_outputs_root(args.outputs_root) / run_id
    try:
        run_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise EvaluationSafetyError("run directory exists; never overwrite") from error

    public_summary_path = run_dir / "public_summary.json"
    log_path = run_dir / "run.log"
    arm_rows: dict[str, list[dict]] = {}
    runtimes: dict[str, dict] = {}
    completed = {"F2-P1": 0, "F3-P1": 0}
    status = "invalid"
    try:
        for arm, adapter in (
            ("F2-P1", args.f2_adapter),
            ("F3-P1", args.f3_adapter),
        ):
            rows, runtime = _generate_arm(
                arm=arm,
                adapter=adapter,
                records=records,
                predictions_path=run_dir / f"{arm.lower()}_predictions.jsonl",
            )
            arm_rows[arm] = rows
            runtimes[arm] = runtime
            completed[arm] = len(rows)

        comparisons = matched_comparisons(
            b0_rows=b0_rows,
            f1_rows=f1_rows,
            f2_rows=arm_rows["F2-P1"],
            f3_rows=arm_rows["F3-P1"],
            bootstrap_samples=BOOTSTRAP_SAMPLES,
            seed=SEED,
        )
        arm_metrics = {}
        for arm, rows in arm_rows.items():
            warning_counts = Counter(
                warning for row in rows for warning in row["parsing_warnings"]
            )
            arm_metrics[arm] = {
                "counts": summarize_predictions(rows),
                "warning_counts": dict(sorted(warning_counts.items())),
                "predictions_sha256": sha256_file(
                    run_dir / f"{arm.lower()}_predictions.jsonl"
                ),
            }
        status = "complete"
        summary = {
            "schema_version": 1,
            "experiment_id": run_id,
            "run_status": status,
            "created_utc": datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat(),
            "git_commit": args.approved_protocol_commit,
            "approval": {
                "approved_protocol_commit": args.approved_protocol_commit,
                "approval_reference": args.approval_reference,
            },
            "models": adapter_meta,
            "data": {
                "name": "Nahw-Passage",
                "split": "test",
                "records": 511,
                "input_sha256": EXPECTED_TEST_SHA256,
            },
            "decoding": {
                "do_sample": False,
                "temperature_argument": None,
                "max_new_tokens": MAX_NEW_TOKENS,
                "seed": SEED,
            },
            "parser": "scripts.nahw_baseline_utils.parse_model_response",
            "arm_metrics": arm_metrics,
            "comparisons": comparisons,
            "reference_predictions": {
                "B0_sha256": EXPECTED_BASELINE_PREDICTIONS_SHA256,
                "F1-P1_sha256": EXPECTED_F1_PREDICTIONS_SHA256,
            },
            "runtime": runtimes,
            "safeguards": {
                "contains_corpus_text": False,
                "training_executed": False,
                "test_pilot_executed": False,
                "checkpoint_changed": False,
                "prompt_or_parser_changed": False,
                "qalb_test_used": False,
                "f1_rerun": False,
                "development_metric_read": False,
                "adapter_merged": False,
                "repeat_run_authorized": False,
            },
        }
        public_summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        log_path.write_text("matched final evaluation completed\n", encoding="utf-8")
        return summary
    except Exception as error:
        for arm in ("F2-P1", "F3-P1"):
            predictions_path = run_dir / f"{arm.lower()}_predictions.jsonl"
            if predictions_path.is_file():
                with predictions_path.open("rb") as stream:
                    completed[arm] = sum(1 for line in stream if line.strip())
            else:
                completed[arm] = 0
        failure = {
            "schema_version": 1,
            "experiment_id": run_id,
            "run_status": status,
            "created_utc": datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat(),
            "completed_records": completed,
            "error_type": type(error).__name__,
            "contains_corpus_text": False,
        }
        public_summary_path.write_text(
            json.dumps(failure, indent=2) + "\n", encoding="utf-8"
        )
        log_path.write_text(
            "run invalid; preserve artifacts and review issue #96\n", encoding="utf-8"
        )
        raise EvaluationSafetyError(
            "matched final evaluation failed; artifacts preserved"
        ) from error


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--f2-adapter", type=Path, required=True)
    parser.add_argument("--f3-adapter", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--baseline-predictions", type=Path, required=True)
    parser.add_argument("--f1-predictions", type=Path, required=True)
    parser.add_argument("--outputs-root", type=Path, default=DEFAULT_OUTPUTS)
    parser.add_argument("--replicate", type=int, default=1)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirmation")
    parser.add_argument("--approved-protocol-commit")
    parser.add_argument("--approval-reference")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        if not args.execute:
            print(
                json.dumps(
                    {
                        "status": "disabled",
                        "inference_executed": False,
                        "final_test_accessed": False,
                    },
                    indent=2,
                )
            )
            return
        if args.replicate != 1:
            raise EvaluationSafetyError("only frozen replicate 1 is permitted")
        require_execution_authorization(
            args.confirmation,
            args.approved_protocol_commit,
            args.approval_reference,
            repository=ROOT,
        )
        adapter_meta = {
            "F2-P1": validate_adapter_checkpoint(
                args.f2_adapter, ARM_SPECS["F2-P1"]
            ),
            "F3-P1": validate_adapter_checkpoint(
                args.f3_adapter, ARM_SPECS["F3-P1"]
            ),
        }
        records = load_and_validate_nahw_records(args.input)
        b0_rows = load_validated_reference_predictions(
            args.baseline_predictions,
            expected_sha256=EXPECTED_BASELINE_PREDICTIONS_SHA256,
            label="B0",
        )
        f1_rows = load_validated_reference_predictions(
            args.f1_predictions,
            expected_sha256=EXPECTED_F1_PREDICTIONS_SHA256,
            label="F1-P1",
        )
        expected_ids = {row["id"] for row in records}
        for label, rows in (("B0", b0_rows), ("F1-P1", f1_rows)):
            observed = {row.get("record_id", row.get("id")) for row in rows}
            if observed != expected_ids:
                raise EvaluationSafetyError(
                    f"{label} predictions do not align with frozen Nahw IDs"
                )
        validate_outputs_root(args.outputs_root)
        summary = execute(
            args,
            records=records,
            b0_rows=b0_rows,
            f1_rows=f1_rows,
            adapter_meta=adapter_meta,
        )
        print(
            json.dumps(
                {
                    "experiment_id": summary["experiment_id"],
                    "run_status": summary["run_status"],
                },
                indent=2,
            )
        )
    except (EvaluationSafetyError, OSError) as error:
        raise SystemExit(f"ERROR: {error}") from error


if __name__ == "__main__":
    main()
