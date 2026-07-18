#!/usr/bin/env python3
"""Preflight or execute the single frozen F1-P1 Nahw-Passage evaluation."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess

from scripts.f1_eval_utils import (
    BASE_MODEL_ID,
    BASE_MODEL_REVISION,
    BOOTSTRAP_SAMPLES,
    CONFIRMATION,
    EXPECTED_TEST_SHA256,
    MAX_NEW_TOKENS,
    RUN_ID,
    SEED,
    EvaluationSafetyError,
    load_validated_baseline_predictions,
    load_and_validate_nahw_records,
    paired_comparison,
    require_execution_authorization,
    sha256_file,
    validate_adapter_checkpoint,
)
from scripts.nahw_baseline_utils import parse_model_response, summarize_predictions
from scripts.prepare_nahw_eval import PROMPT


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "processed" / "nahw_gec_test.jsonl"
DEFAULT_BASELINE = ROOT / "outputs" / "baseline_full_predictions.jsonl"
DEFAULT_OUTPUTS = ROOT / "outputs"


def _git_sha() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True,
            capture_output=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


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
    """Keep text-bearing outputs ignored when written inside the repository."""

    resolved = Path(path).expanduser().resolve()
    if _is_relative_to(resolved, ROOT) and not _is_relative_to(
        resolved, DEFAULT_OUTPUTS.resolve()
    ):
        raise EvaluationSafetyError(
            "repository-local final outputs must stay under the ignored outputs/ tree"
        )
    return resolved


class AdapterGenerator:
    """Immutable-revision 4-bit base plus the verified unmerged LoRA adapter."""

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
            raise EvaluationSafetyError("GPU inference dependencies are unavailable") from error
        if not torch.cuda.is_available():
            raise EvaluationSafetyError("CUDA GPU is required for final evaluation")
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
        properties = torch.cuda.get_device_properties(0)
        self.runtime.update({
            "cuda": torch.version.cuda,
            "gpu": properties.name,
            "gpu_total_memory_bytes": properties.total_memory,
            "dtype_argument": None,
            "load_in_4bit": True,
        })

    def __call__(self, prompt: str) -> str:
        if self.model is None or self.processor is None:
            self.load()
        messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
        inputs = self.processor.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=True,
            return_dict=True, return_tensors="pt",
        ).to(self.model.device)
        input_length = inputs["input_ids"].shape[-1]
        outputs = self.model.generate(
            **inputs, do_sample=False, max_new_tokens=MAX_NEW_TOKENS
        )
        return self.processor.decode(outputs[0][input_length:], skip_special_tokens=True)


def execute(
    args: argparse.Namespace,
    records: list[dict],
    adapter_meta: dict,
    baseline_rows: list[dict],
) -> dict:
    run_id = RUN_ID.replace("__r01", f"__r{args.replicate:02d}")
    run_dir = validate_outputs_root(args.outputs_root) / run_id
    try:
        run_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise EvaluationSafetyError("run directory already exists; never overwrite it") from error
    predictions_path = run_dir / "predictions.jsonl"
    summary_path = run_dir / "summary.json"
    log_path = run_dir / "run.log"
    rows: list[dict] = []
    generator = AdapterGenerator(Path(args.adapter))
    status = "invalid"
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
                    "normalized_gold_value": record["gold_correction"],
                    "exact_match": parsed == record["gold_correction"],
                    "parsing_warnings": warnings,
                }
                stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                stream.flush()
                rows.append(row)
        if len(rows) != 511:
            raise EvaluationSafetyError("final run did not complete exactly 511 records")
        comparison = paired_comparison(
            baseline_rows, rows,
            bootstrap_samples=BOOTSTRAP_SAMPLES, seed=SEED,
        )
        status = "complete"
        warning_counts = Counter(
            warning for row in rows for warning in row["parsing_warnings"]
        )
        summary = {
            "schema_version": 1,
            "experiment_id": run_id,
            "run_status": status,
            "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "git_commit": _git_sha(),
            "approval": {
                "approved_protocol_commit": args.approved_protocol_commit,
                "approval_reference": args.approval_reference,
            },
            "model": {
                "base_model_id": BASE_MODEL_ID,
                "base_model_revision": BASE_MODEL_REVISION,
                "selected_checkpoint": "checkpoint-250",
                **adapter_meta,
            },
            "data": {"name": "Nahw-Passage", "split": "test", "records": 511,
                     "input_sha256": EXPECTED_TEST_SHA256},
            "prompt_template": PROMPT,
            "decoding": {"do_sample": False, "temperature_argument": None,
                         "max_new_tokens": MAX_NEW_TOKENS, "seed": SEED},
            "parser": "scripts.nahw_baseline_utils.parse_model_response",
            "counts": summarize_predictions(rows),
            "warning_counts": dict(sorted(warning_counts.items())),
            "paired_comparison_to_b0": comparison,
            "predictions_sha256": sha256_file(predictions_path),
            "baseline_predictions_sha256": sha256_file(args.baseline_predictions),
            "runtime": generator.runtime,
            "safeguards": {"training": False, "adapter_merged": False,
                           "test_pilot": False, "overwrite": False},
        }
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        log_path.write_text("run completed\n", encoding="utf-8")
        return summary
    except Exception as error:
        failure = {
            "schema_version": 1, "experiment_id": run_id, "run_status": status,
            "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "completed_records": len(rows), "error_type": type(error).__name__,
            "predictions_sha256": sha256_file(predictions_path) if predictions_path.exists() else None,
        }
        summary_path.write_text(json.dumps(failure, indent=2) + "\n", encoding="utf-8")
        log_path.write_text("run invalid; see execution issue\n", encoding="utf-8")
        raise EvaluationSafetyError("final evaluation failed; invalid artifacts preserved") from error


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--baseline-predictions", type=Path, default=DEFAULT_BASELINE)
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
        if args.replicate < 1 or args.replicate > 99:
            raise EvaluationSafetyError("replicate must be between 1 and 99")
        adapter_meta = validate_adapter_checkpoint(args.adapter)
        records = load_and_validate_nahw_records(args.input)
        validate_outputs_root(args.outputs_root)
        if not args.execute:
            print(json.dumps({"status": "preflight_passed", "inference_executed": False,
                              "records": len(records), "adapter": adapter_meta}, indent=2))
            return
        require_execution_authorization(
            args.confirmation, args.approved_protocol_commit, args.approval_reference,
            repository=ROOT,
        )
        if not Path(args.baseline_predictions).is_file():
            raise EvaluationSafetyError("accepted B0 prediction artifact is required")
        baseline_rows = load_validated_baseline_predictions(args.baseline_predictions)
        baseline_ids = {row.get("record_id", row.get("id")) for row in baseline_rows}
        test_ids = {row["id"] for row in records}
        if baseline_ids != test_ids:
            raise EvaluationSafetyError(
                "accepted B0 predictions do not align with frozen Nahw record IDs"
            )
        summary = execute(args, records, adapter_meta, baseline_rows)
        print(json.dumps({"experiment_id": summary["experiment_id"],
                          "run_status": summary["run_status"]}, indent=2))
    except (EvaluationSafetyError, OSError) as error:
        raise SystemExit(f"ERROR: {error}") from error


if __name__ == "__main__":
    main()
