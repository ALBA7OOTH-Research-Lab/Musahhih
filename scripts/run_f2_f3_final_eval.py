#!/usr/bin/env python3
"""Execute the single matched F2/F3 Nahw-Passage evaluation when authorized."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import gc
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import time

from scripts.f2_f3_eval_utils import (
    ARM_SPECS,
    BASE_MODEL_ID,
    BASE_MODEL_REVISION,
    BOOTSTRAP_SAMPLES,
    EXPECTED_BASELINE_PREDICTIONS_SHA256,
    EXPECTED_F1_PREDICTIONS_SHA256,
    EXPECTED_TEST_SHA256,
    MAX_NEW_TOKENS,
    RUN_ID,
    SAFE_STOP_ELAPSED_SECONDS,
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
PROGRESS_SCHEMA_VERSION = 1


class TimeBudgetExhausted(Exception):
    """Signal a planned, output-preserving stop before Kaggle's hard cutoff."""


class KernelTimeBudget:
    """Conservative wall-clock guard measured from the private wrapper start."""

    def __init__(
        self,
        kernel_start_epoch_seconds: float,
        *,
        now=time.time,
        safe_stop_elapsed_seconds: int = SAFE_STOP_ELAPSED_SECONDS,
    ) -> None:
        self.kernel_start_epoch_seconds = float(kernel_start_epoch_seconds)
        self._now = now
        self.safe_stop_elapsed_seconds = int(safe_stop_elapsed_seconds)
        started_ago = self._now() - self.kernel_start_epoch_seconds
        if started_ago < -300:
            raise EvaluationSafetyError("kernel start time is in the future")

    def elapsed_seconds(self) -> int:
        return max(0, int(self._now() - self.kernel_start_epoch_seconds))

    def require_next_record_budget(self) -> None:
        if self.elapsed_seconds() >= self.safe_stop_elapsed_seconds:
            raise TimeBudgetExhausted


def _fsync_stream(stream) -> None:
    stream.flush()
    os.fsync(stream.fileno())


def _write_json_atomic(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        )
        _fsync_stream(stream)
    temporary.replace(path)


def _read_json_object(path: Path, label: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EvaluationSafetyError(f"invalid {label}") from error
    if not isinstance(value, dict):
        raise EvaluationSafetyError(f"{label} must be a JSON object")
    return value


def _read_prediction_rows(path: Path, label: str) -> list[dict]:
    if not path.is_file():
        return []
    try:
        with path.open("r", encoding="utf-8") as stream:
            rows = [json.loads(line) for line in stream if line.strip()]
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EvaluationSafetyError(f"invalid private {label} prefix") from error
    if not all(isinstance(row, dict) for row in rows):
        raise EvaluationSafetyError(f"invalid private {label} prefix rows")
    return rows


def _fsync_path(path: Path) -> None:
    with path.open("rb") as stream:
        os.fsync(stream.fileno())


def _validate_prediction_prefix(
    rows: list[dict], records: list[dict], *, arm: str
) -> None:
    if len(rows) > len(records):
        raise EvaluationSafetyError(f"{arm} resume prefix is too long")
    for index, row in enumerate(rows):
        record = records[index]
        expected = {
            "record_id": record["id"],
            "passage_id": record["passage_id"],
            "source": record["source"],
            "split": record["split"],
            "passage": record["passage"],
            "erroneous_word": record["error"],
            "gold_correction": record["gold_correction"],
            "full_prompt": record["prompt"],
        }
        if any(row.get(field) != value for field, value in expected.items()):
            raise EvaluationSafetyError(f"{arm} resume prefix record mismatch")
        if not isinstance(row.get("raw_model_response"), str):
            raise EvaluationSafetyError(f"{arm} resume prefix response mismatch")
        if not isinstance(row.get("parsed_correction"), str):
            raise EvaluationSafetyError(f"{arm} resume prefix parse mismatch")
        if not isinstance(row.get("parsing_warnings"), list):
            raise EvaluationSafetyError(f"{arm} resume prefix warnings mismatch")
        if row.get("exact_match") is not (
            row["parsed_correction"] == record["gold_correction"]
        ):
            raise EvaluationSafetyError(f"{arm} resume prefix score mismatch")


def load_resume_prefixes(
    resume_from: Path | None,
    *,
    records: list[dict],
    approved_protocol_commit: str,
) -> tuple[dict[str, tuple[list[dict], Path | None]], dict[str, dict]]:
    """Verify a private timed handoff without regenerating completed records."""

    empty = {"F2-P1": ([], None), "F3-P1": ([], None)}
    if resume_from is None:
        return empty, {}
    resume_dir = Path(resume_from).expanduser().resolve()
    if _is_relative_to(resume_dir, ROOT) and not _is_relative_to(
        resume_dir, DEFAULT_OUTPUTS.resolve()
    ):
        raise EvaluationSafetyError(
            "repository-local resume artifacts must stay under ignored outputs/"
        )
    summary = _read_json_object(
        resume_dir / "public_summary.json", "resume public summary"
    )
    progress = _read_json_object(resume_dir / "progress.json", "resume progress")
    if summary.get("run_status") != "incomplete_time_budget":
        raise EvaluationSafetyError("resume source is not a timed handoff")
    if summary.get("git_commit") != approved_protocol_commit:
        raise EvaluationSafetyError("resume source protocol commit mismatch")
    if progress.get("schema_version") != PROGRESS_SCHEMA_VERSION:
        raise EvaluationSafetyError("resume progress schema mismatch")
    if progress.get("git_commit") != approved_protocol_commit:
        raise EvaluationSafetyError("resume progress protocol commit mismatch")
    if progress.get("experiment_id") != RUN_ID:
        raise EvaluationSafetyError("resume progress experiment mismatch")

    prefixes: dict[str, tuple[list[dict], Path | None]] = {}
    completed = progress.get("completed_records")
    hashes = progress.get("prediction_sha256")
    runtimes = progress.get("runtime")
    if (
        not isinstance(completed, dict)
        or not isinstance(hashes, dict)
        or not isinstance(runtimes, dict)
    ):
        raise EvaluationSafetyError("resume progress fields are invalid")
    for arm in ("F2-P1", "F3-P1"):
        path = resume_dir / f"{arm.lower()}_predictions.jsonl"
        rows = _read_prediction_rows(path, arm)
        _validate_prediction_prefix(rows, records, arm=arm)
        if completed.get(arm) != len(rows):
            raise EvaluationSafetyError(f"{arm} resume count mismatch")
        expected_hash = hashes.get(arm)
        if rows:
            if not isinstance(expected_hash, str) or sha256_file(path) != expected_hash:
                raise EvaluationSafetyError(f"{arm} resume SHA-256 mismatch")
            if not isinstance(runtimes.get(arm), dict):
                raise EvaluationSafetyError(f"{arm} resume runtime metadata missing")
            prefixes[arm] = (rows, path)
        else:
            if expected_hash is not None or path.exists():
                raise EvaluationSafetyError(f"{arm} empty resume prefix mismatch")
            prefixes[arm] = ([], None)
    if len(prefixes["F2-P1"][0]) < len(records) and prefixes["F3-P1"][0]:
        raise EvaluationSafetyError("F3 resume rows exist before F2 completion")
    return prefixes, runtimes


def _progress_payload(
    *,
    approved_protocol_commit: str,
    completed: dict[str, int],
    prediction_paths: dict[str, Path],
    runtimes: dict[str, dict],
    budget: KernelTimeBudget,
    status: str,
) -> dict:
    hashes = {
        arm: sha256_file(path) if path.is_file() else None
        for arm, path in prediction_paths.items()
    }
    return {
        "schema_version": PROGRESS_SCHEMA_VERSION,
        "experiment_id": RUN_ID,
        "git_commit": approved_protocol_commit,
        "status": status,
        "completed_records": dict(completed),
        "prediction_sha256": hashes,
        "runtime": runtimes,
        "elapsed_seconds": budget.elapsed_seconds(),
        "contains_corpus_text": False,
    }


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
    prefix_rows: list[dict],
    budget: KernelTimeBudget,
    progress_callback,
) -> tuple[list[dict], dict]:
    rows = list(prefix_rows)
    if len(rows) < len(records):
        budget.require_next_record_budget()
    mode = "a" if predictions_path.is_file() else "x"
    generator = AdapterGenerator(adapter)
    try:
        with predictions_path.open(mode, encoding="utf-8", newline="\n") as stream:
            for record in records[len(rows) :]:
                budget.require_next_record_budget()
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
                _fsync_stream(stream)
                rows.append(row)
                progress_callback(len(rows), generator.runtime)
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
    progress_path = run_dir / "progress.json"
    log_path = run_dir / "run.log"
    arm_rows: dict[str, list[dict]] = {}
    runtimes: dict[str, dict]
    completed = {"F2-P1": 0, "F3-P1": 0}
    prediction_paths = {
        arm: run_dir / f"{arm.lower()}_predictions.jsonl"
        for arm in ("F2-P1", "F3-P1")
    }
    budget = KernelTimeBudget(args.kernel_start_epoch_seconds)
    prefixes, runtimes = load_resume_prefixes(
        args.resume_from,
        records=records,
        approved_protocol_commit=args.approved_protocol_commit,
    )
    for arm, (rows, _) in prefixes.items():
        completed[arm] = len(rows)
    for arm, (_, source_path) in prefixes.items():
        if source_path is not None:
            shutil.copyfile(source_path, prediction_paths[arm])
            _fsync_path(prediction_paths[arm])

    def persist_progress(status: str = "running") -> None:
        _write_json_atomic(
            progress_path,
            _progress_payload(
                approved_protocol_commit=args.approved_protocol_commit,
                completed=completed,
                prediction_paths=prediction_paths,
                runtimes=runtimes,
                budget=budget,
                status=status,
            ),
        )

    persist_progress()
    status = "invalid"
    try:
        for arm, adapter in (
            ("F2-P1", args.f2_adapter),
            ("F3-P1", args.f3_adapter),
        ):
            prefix_rows, _ = prefixes[arm]
            if len(prefix_rows) == len(records):
                arm_rows[arm] = prefix_rows
                completed[arm] = len(prefix_rows)
                continue

            def on_progress(
                count: int, runtime: dict, *, current_arm: str = arm
            ) -> None:
                completed[current_arm] = count
                runtimes[current_arm] = runtime
                persist_progress()

            rows, runtime = _generate_arm(
                arm=arm,
                adapter=adapter,
                records=records,
                predictions_path=prediction_paths[arm],
                prefix_rows=prefix_rows,
                budget=budget,
                progress_callback=on_progress,
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
        persist_progress(status)
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
        _write_json_atomic(public_summary_path, summary)
        log_path.write_text("matched final evaluation completed\n", encoding="utf-8")
        return summary
    except TimeBudgetExhausted:
        for arm, path in prediction_paths.items():
            completed[arm] = (
                sum(1 for line in path.open("rb") if line.strip())
                if path.is_file()
                else 0
            )
        status = "incomplete_time_budget"
        persist_progress(status)
        summary = {
            "schema_version": 2,
            "experiment_id": run_id,
            "run_status": status,
            "created_utc": datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat(),
            "git_commit": args.approved_protocol_commit,
            "completed_records": completed,
            "prediction_sha256": {
                arm: sha256_file(path) if path.is_file() else None
                for arm, path in prediction_paths.items()
            },
            "elapsed_seconds": budget.elapsed_seconds(),
            "safe_stop_elapsed_seconds": SAFE_STOP_ELAPSED_SECONDS,
            "runtime": runtimes,
            "contains_corpus_text": False,
            "metrics_reported": False,
            "resume_requires_fresh_authorization": True,
        }
        _write_json_atomic(public_summary_path, summary)
        log_path.write_text(
            "safe wall-time stop; private handoff preserved; fresh GO required\n",
            encoding="utf-8",
        )
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
        _write_json_atomic(public_summary_path, failure)
        log_path.write_text(
            "run invalid; preserve artifacts and review issue #98\n", encoding="utf-8"
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
    parser.add_argument("--resume-from", type=Path)
    parser.add_argument("--kernel-start-epoch-seconds", type=float)
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
        if args.kernel_start_epoch_seconds is None:
            raise EvaluationSafetyError("kernel start epoch is required")
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
