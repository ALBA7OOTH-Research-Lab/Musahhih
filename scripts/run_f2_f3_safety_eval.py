#!/usr/bin/env python3
"""Run the authorized, timeout-safe F2/F3 behavioral diagnostics."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import gc
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import shutil
import time

from scripts.f1_eval_utils import BASE_MODEL_ID, BASE_MODEL_REVISION
from scripts.f2_f3_safety_eval_utils import (
    ARM_SPECS,
    BOOTSTRAP_SAMPLES,
    CONFIRMATION,
    EXPECTED_CAPABILITY_SHA256,
    EXPECTED_OVERCORRECTION_SHA256,
    EXPECTED_STAGE_RECORDS,
    REFERENCE_PREDICTION_SHA256,
    RUN_ID,
    SAFE_STOP_ELAPSED_SECONDS,
    SEED,
    STAGES,
    SYSTEMS,
    EvaluationSafetyError,
    load_capability_records,
    load_overcorrection_records,
    paired_binary_comparison,
    require_execution_authorization,
    select_highest_logit,
    sha256_file,
    validate_adapter_checkpoint,
)
from scripts.nahw_baseline_utils import parse_model_response


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUTS = ROOT / "data" / "processed" / "f1_safety_eval"
DEFAULT_OUTPUTS = ROOT / "outputs"
PROGRESS_SCHEMA_VERSION = 1
MAX_SEQUENCE_LENGTH = 2_048
MAX_NEW_TOKENS = 32
EXPECTED_PYTHON = "3.12.13"
EXPECTED_CUDA = "12.4"
EXPECTED_PACKAGES = {
    "torch": "2.6.0+cu124",
    "transformers": "4.56.2",
    "unsloth": "2026.7.3",
    "accelerate": "1.13.0",
    "peft": "0.19.1",
    "trl": "0.22.2",
}


class TimeBudgetExhausted(Exception):
    """Signal a planned metric-free stop before Kaggle's hard cutoff."""


class KernelTimeBudget:
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
        if self._now() - self.kernel_start_epoch_seconds < -300:
            raise EvaluationSafetyError("kernel start time is in the future")

    def elapsed_seconds(self) -> int:
        return max(0, int(self._now() - self.kernel_start_epoch_seconds))

    def require_next_record_budget(self) -> None:
        if self.elapsed_seconds() >= self.safe_stop_elapsed_seconds:
            raise TimeBudgetExhausted


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def validate_outputs_root(path: Path) -> Path:
    resolved = Path(path).expanduser().resolve()
    if _is_relative_to(resolved, ROOT) and not _is_relative_to(
        resolved, DEFAULT_OUTPUTS.resolve()
    ):
        raise EvaluationSafetyError(
            "repository-local diagnostic outputs must stay under ignored outputs/"
        )
    return resolved


def _fsync_stream(stream) -> None:
    stream.flush()
    os.fsync(stream.fileno())


def _fsync_path(path: Path) -> None:
    with path.open("rb") as stream:
        os.fsync(stream.fileno())


def _write_json_atomic(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
        _fsync_stream(stream)
    temporary.replace(path)


def _read_json_object(path: Path, label: str) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EvaluationSafetyError(f"invalid {label}") from error
    if not isinstance(payload, dict):
        raise EvaluationSafetyError(f"{label} must be a JSON object")
    return payload


def _read_rows(path: Path, label: str) -> list[dict]:
    if not path.is_file():
        return []
    try:
        with path.open("r", encoding="utf-8") as stream:
            rows = [json.loads(line) for line in stream if line.strip()]
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EvaluationSafetyError(f"invalid private {label} prefix") from error
    if not all(isinstance(row, dict) for row in rows):
        raise EvaluationSafetyError(f"invalid private {label} rows")
    return rows


def _stage_path(run_dir: Path, stage: str) -> Path:
    return run_dir / f"{stage.lower().replace('-', '_')}_predictions.jsonl"


def _validate_overcorrection_prefix(rows: list[dict], records: list[dict], stage: str) -> None:
    if len(rows) > len(records):
        raise EvaluationSafetyError(f"{stage} prefix is too long")
    for index, row in enumerate(rows):
        record = records[index]
        if any(row.get(field) != value for field, value in record.items()):
            raise EvaluationSafetyError(f"{stage} frozen record mismatch")
        if not isinstance(row.get("raw_model_response"), str):
            raise EvaluationSafetyError(f"{stage} response mismatch")
        if not isinstance(row.get("parsed_correction"), str):
            raise EvaluationSafetyError(f"{stage} parse mismatch")
        warnings = row.get("parsing_warnings")
        if not isinstance(warnings, list) or not all(isinstance(item, str) for item in warnings):
            raise EvaluationSafetyError(f"{stage} warning mismatch")
        suspicious = bool(set(warnings) - {"outer_formatting_removed"})
        expected = row["parsed_correction"] == record["gold_unchanged_token"] and not suspicious
        if row.get("unchanged_exact") is not expected:
            raise EvaluationSafetyError(f"{stage} score mismatch")


def _validate_capability_prefix(rows: list[dict], records: list[dict], stage: str) -> None:
    if len(rows) > len(records):
        raise EvaluationSafetyError(f"{stage} prefix is too long")
    for index, row in enumerate(rows):
        record = records[index]
        if any(row.get(field) != value for field, value in record.items()):
            raise EvaluationSafetyError(f"{stage} frozen record mismatch")
        logits = row.get("candidate_logits")
        if (
            not isinstance(logits, dict)
            or set(logits) != set(record["choices"])
            or not all(isinstance(value, (int, float)) and math.isfinite(value) for value in logits.values())
        ):
            raise EvaluationSafetyError(f"{stage} candidate logits mismatch")
        expected_prediction = select_highest_logit(record["choices"], logits)
        if row.get("predicted_choice") != expected_prediction:
            raise EvaluationSafetyError(f"{stage} prediction mismatch")
        if row.get("exact_match") is not (expected_prediction == record["gold_choice"]):
            raise EvaluationSafetyError(f"{stage} score mismatch")


def load_reference_predictions(
    paths: dict[str, Path],
    *,
    overcorrection_records: list[dict],
    capability_records: list[dict],
) -> dict[str, list[dict]]:
    """Load immutable B0/F1 references and recompute their private contracts."""

    if set(paths) != set(REFERENCE_PREDICTION_SHA256):
        raise EvaluationSafetyError("B0/F1 reference prediction set mismatch")
    references = {}
    for label, path in paths.items():
        resolved = Path(path).expanduser().resolve()
        if sha256_file(resolved) != REFERENCE_PREDICTION_SHA256[label]:
            raise EvaluationSafetyError(f"{label} reference SHA-256 mismatch")
        rows = _read_rows(resolved, label)
        system, endpoint = label.split("_", 1)
        if any(row.get("system_id") != system for row in rows):
            raise EvaluationSafetyError(f"{label} reference system mismatch")
        if endpoint == "overcorrection":
            if len(rows) != len(overcorrection_records):
                raise EvaluationSafetyError(f"{label} reference count mismatch")
            _validate_overcorrection_prefix(rows, overcorrection_records, label)
        else:
            if len(rows) != len(capability_records):
                raise EvaluationSafetyError(f"{label} reference count mismatch")
            _validate_capability_prefix(rows, capability_records, label)
        references[label] = rows
    return references


def load_resume_prefixes(
    resume_from: Path | None,
    *,
    overcorrection_records: list[dict],
    capability_records: list[dict],
    approved_protocol_commit: str,
) -> tuple[dict[str, tuple[list[dict], Path | None]], dict[str, dict]]:
    empty = {stage: ([], None) for stage in STAGES}
    if resume_from is None:
        return empty, {}
    resume_dir = Path(resume_from).expanduser().resolve()
    if _is_relative_to(resume_dir, ROOT) and not _is_relative_to(
        resume_dir, DEFAULT_OUTPUTS.resolve()
    ):
        raise EvaluationSafetyError("repository-local resume must stay under ignored outputs/")
    summary = _read_json_object(resume_dir / "public_summary.json", "resume summary")
    progress = _read_json_object(resume_dir / "progress.json", "resume progress")
    if summary.get("run_status") != "incomplete_time_budget":
        raise EvaluationSafetyError("resume source is not a timed handoff")
    if summary.get("git_commit") != approved_protocol_commit:
        raise EvaluationSafetyError("resume summary commit mismatch")
    if progress.get("schema_version") != PROGRESS_SCHEMA_VERSION:
        raise EvaluationSafetyError("resume progress schema mismatch")
    if progress.get("experiment_family") != RUN_ID:
        raise EvaluationSafetyError("resume experiment mismatch")
    if progress.get("git_commit") != approved_protocol_commit:
        raise EvaluationSafetyError("resume progress commit mismatch")
    completed = progress.get("completed_records")
    hashes = progress.get("prediction_sha256")
    runtimes = progress.get("runtime")
    if not all(isinstance(value, dict) for value in (completed, hashes, runtimes)):
        raise EvaluationSafetyError("resume progress fields are invalid")

    prefixes: dict[str, tuple[list[dict], Path | None]] = {}
    earlier_incomplete = False
    for stage in STAGES:
        path = _stage_path(resume_dir, stage)
        rows = _read_rows(path, stage)
        records = overcorrection_records if stage.endswith("overcorrection") else capability_records
        if stage.endswith("overcorrection"):
            _validate_overcorrection_prefix(rows, records, stage)
        else:
            _validate_capability_prefix(rows, records, stage)
        if completed.get(stage) != len(rows):
            raise EvaluationSafetyError(f"{stage} resume count mismatch")
        if earlier_incomplete and rows:
            raise EvaluationSafetyError("resume stages are out of order")
        if len(rows) < EXPECTED_STAGE_RECORDS[stage]:
            earlier_incomplete = True
        expected_hash = hashes.get(stage)
        if rows:
            if not isinstance(expected_hash, str) or sha256_file(path) != expected_hash:
                raise EvaluationSafetyError(f"{stage} resume SHA-256 mismatch")
            prefixes[stage] = (rows, path)
        else:
            if expected_hash is not None or path.exists():
                raise EvaluationSafetyError(f"{stage} empty prefix mismatch")
            prefixes[stage] = ([], None)
    for system in SYSTEMS:
        if any(prefixes[f"{system}_{kind}"][0] for kind in ("overcorrection", "capability")):
            if not isinstance(runtimes.get(system), dict):
                raise EvaluationSafetyError(f"{system} runtime metadata missing")
    return prefixes, runtimes


def _versions() -> dict:
    packages = {}
    for name in EXPECTED_PACKAGES:
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {"python": platform.python_version(), "packages": packages}


class FrozenSystem:
    def __init__(self, system_id: str, adapter_path: Path) -> None:
        if system_id not in SYSTEMS:
            raise EvaluationSafetyError("unknown diagnostic system")
        self.system_id = system_id
        self.adapter_path = Path(adapter_path)
        self.model = None
        self.processor = None
        self.torch = None
        self.candidate_token_ids: dict[str, int] = {}

    def load(self) -> dict:
        try:
            import torch
            from peft import PeftModel
            from unsloth import FastModel
        except (ImportError, OSError) as error:
            raise EvaluationSafetyError("GPU inference dependencies unavailable") from error
        if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
            raise EvaluationSafetyError("exactly one CUDA GPU is required")
        properties = torch.cuda.get_device_properties(0)
        versions = _versions()
        if "P100" not in properties.name.upper():
            raise EvaluationSafetyError("matched diagnostics require a Kaggle P100")
        if versions["python"] != EXPECTED_PYTHON or versions["packages"] != EXPECTED_PACKAGES:
            raise EvaluationSafetyError("package runtime differs from frozen F1 diagnostics")
        if torch.version.cuda != EXPECTED_CUDA:
            raise EvaluationSafetyError("CUDA version differs from frozen F1 diagnostics")
        torch.manual_seed(SEED)
        torch.cuda.manual_seed_all(SEED)
        try:
            base, self.processor = FastModel.from_pretrained(
                model_name=BASE_MODEL_ID,
                revision=BASE_MODEL_REVISION,
                max_seq_length=MAX_SEQUENCE_LENGTH,
                dtype=None,
                load_in_4bit=True,
                full_finetuning=False,
            )
            self.model = PeftModel.from_pretrained(base, str(self.adapter_path), is_trainable=False)
            if hasattr(FastModel, "for_inference"):
                FastModel.for_inference(self.model)
            self.model.eval()
        except Exception as error:
            raise EvaluationSafetyError(f"unable to load pinned {self.system_id}") from error
        tokenizer = getattr(self.processor, "tokenizer", None)
        if tokenizer is None:
            raise EvaluationSafetyError("pinned processor has no tokenizer")
        for letter in "ABCDE":
            token_ids = tokenizer(letter, add_special_tokens=False)["input_ids"]
            if len(token_ids) != 1:
                raise EvaluationSafetyError("ArabicMMLU answer letters must be one token")
            self.candidate_token_ids[letter] = token_ids[0]
        if len(set(self.candidate_token_ids.values())) != 5:
            raise EvaluationSafetyError("ArabicMMLU answer token IDs must be distinct")
        self.torch = torch
        return {
            **versions,
            "cuda": torch.version.cuda,
            "gpu": properties.name,
            "gpu_total_memory_bytes": properties.total_memory,
            "base_model_id": BASE_MODEL_ID,
            "base_model_revision": BASE_MODEL_REVISION,
            "load_in_4bit": True,
            "adapter_merged": False,
            "candidate_token_ids": dict(self.candidate_token_ids),
        }

    def _chat_inputs(self, prompt: str):
        messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
        inputs = self.processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(self.model.device)
        if inputs["input_ids"].shape[-1] > MAX_SEQUENCE_LENGTH:
            raise EvaluationSafetyError("input exceeds frozen sequence limit")
        return inputs

    def generate_correction(self, prompt: str) -> str:
        inputs = self._chat_inputs(prompt)
        input_length = inputs["input_ids"].shape[-1]
        with self.torch.inference_mode():
            output = self.model.generate(**inputs, do_sample=False, max_new_tokens=MAX_NEW_TOKENS)
        return self.processor.decode(output[0][input_length:], skip_special_tokens=True)

    def score_choices(self, prompt: str, choices: list[str]) -> tuple[str, dict[str, float]]:
        inputs = self._chat_inputs(prompt)
        with self.torch.inference_mode():
            next_logits = self.model(**inputs).logits[0, -1]
        scores = {
            choice: float(next_logits[self.candidate_token_ids[choice]].item())
            for choice in choices
        }
        return select_highest_logit(choices, scores), scores

    def close(self) -> None:
        self.model = None
        self.processor = None
        self.candidate_token_ids = {}
        gc.collect()
        try:
            if self.torch is not None and self.torch.cuda.is_available():
                self.torch.cuda.empty_cache()
                self.torch.cuda.synchronize()
        except RuntimeError:
            # Cleanup cannot replace a planned timeout handoff or the original
            # model/evaluation error; process exit will release the GPU.
            pass
        self.torch = None


def _progress_payload(
    *,
    approved_commit: str,
    run_id: str,
    completed: dict[str, int],
    paths: dict[str, Path],
    runtimes: dict[str, dict],
    budget: KernelTimeBudget,
    status: str,
) -> dict:
    return {
        "schema_version": PROGRESS_SCHEMA_VERSION,
        "experiment_family": RUN_ID,
        "experiment_id": run_id,
        "git_commit": approved_commit,
        "status": status,
        "completed_records": dict(completed),
        "prediction_sha256": {
            stage: sha256_file(path) if path.is_file() else None
            for stage, path in paths.items()
        },
        "runtime": runtimes,
        "elapsed_seconds": budget.elapsed_seconds(),
        "contains_corpus_text": False,
    }


def _system_counts(over_rows: list[dict], capability_rows: list[dict]) -> dict:
    unchanged = sum(row["unchanged_exact"] for row in over_rows)
    correct = sum(row["exact_match"] for row in capability_rows)
    return {
        "overcorrection": {
            "records": len(over_rows),
            "unchanged_exact": unchanged,
            "unchanged_accuracy": unchanged / len(over_rows),
            "overcorrection_rate": 1.0 - unchanged / len(over_rows),
            "empty_outputs": sum(not row["parsed_correction"] for row in over_rows),
            "suspicious_outputs": sum(
                bool(set(row["parsing_warnings"]) - {"outer_formatting_removed"})
                for row in over_rows
            ),
            "warning_counts": dict(sorted(Counter(
                warning for row in over_rows for warning in row["parsing_warnings"]
            ).items())),
        },
        "capability": {
            "records": len(capability_rows),
            "correct": correct,
            "micro_accuracy": correct / len(capability_rows),
        },
    }


def execute(
    args: argparse.Namespace,
    *,
    overcorrection_records: list[dict],
    capability_records: list[dict],
    adapter_meta: dict[str, dict],
    reference_rows: dict[str, list[dict]],
    model_factory=FrozenSystem,
) -> dict:
    run_id = RUN_ID.replace("__r01", f"__r{args.replicate:02d}")
    run_dir = validate_outputs_root(args.outputs_root) / run_id
    try:
        run_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise EvaluationSafetyError("run directory exists; never overwrite") from error
    paths = {stage: _stage_path(run_dir, stage) for stage in STAGES}
    progress_path = run_dir / "progress.json"
    public_summary_path = run_dir / "public_summary.json"
    budget = KernelTimeBudget(args.kernel_start_epoch_seconds)
    prefixes, runtimes = load_resume_prefixes(
        args.resume_from,
        overcorrection_records=overcorrection_records,
        capability_records=capability_records,
        approved_protocol_commit=args.approved_protocol_commit,
    )
    rows = {stage: list(prefixes[stage][0]) for stage in STAGES}
    for stage, (_, source) in prefixes.items():
        if source is not None:
            shutil.copyfile(source, paths[stage])
            _fsync_path(paths[stage])
    completed = {stage: len(rows[stage]) for stage in STAGES}

    def persist(status: str = "running") -> None:
        _write_json_atomic(
            progress_path,
            _progress_payload(
                approved_commit=args.approved_protocol_commit,
                run_id=run_id,
                completed=completed,
                paths=paths,
                runtimes=runtimes,
                budget=budget,
                status=status,
            ),
        )

    persist()
    try:
        for system in SYSTEMS:
            over_stage = f"{system}_overcorrection"
            capability_stage = f"{system}_capability"
            if (
                completed[over_stage] == len(overcorrection_records)
                and completed[capability_stage] == len(capability_records)
            ):
                continue
            budget.require_next_record_budget()
            model = model_factory(system, Path(args.f2_adapter if system == "F2-P1" else args.f3_adapter))
            try:
                runtimes[system] = model.load()
                persist()
                if completed[over_stage] < len(overcorrection_records):
                    mode = "a" if paths[over_stage].is_file() else "x"
                    with paths[over_stage].open(mode, encoding="utf-8", newline="\n") as stream:
                        for record in overcorrection_records[completed[over_stage]:]:
                            budget.require_next_record_budget()
                            raw = model.generate_correction(record["prompt"])
                            parsed, warnings = parse_model_response(raw)
                            suspicious = bool(set(warnings) - {"outer_formatting_removed"})
                            row = {
                                **record,
                                "system_id": system,
                                "raw_model_response": raw,
                                "parsed_correction": parsed,
                                "parsing_warnings": warnings,
                                "unchanged_exact": parsed == record["gold_unchanged_token"] and not suspicious,
                            }
                            line = json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                            stream.write(line)
                            _fsync_stream(stream)
                            rows[over_stage].append(row)
                            completed[over_stage] += 1
                            persist()
                if completed[capability_stage] < len(capability_records):
                    mode = "a" if paths[capability_stage].is_file() else "x"
                    with paths[capability_stage].open(mode, encoding="utf-8", newline="\n") as stream:
                        for record in capability_records[completed[capability_stage]:]:
                            budget.require_next_record_budget()
                            prediction, logits = model.score_choices(record["prompt"], record["choices"])
                            row = {
                                **record,
                                "system_id": system,
                                "candidate_logits": logits,
                                "predicted_choice": prediction,
                                "exact_match": prediction == record["gold_choice"],
                            }
                            line = json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                            stream.write(line)
                            _fsync_stream(stream)
                            rows[capability_stage].append(row)
                            completed[capability_stage] += 1
                            persist()
            finally:
                model.close()
        if any(completed[stage] != EXPECTED_STAGE_RECORDS[stage] for stage in STAGES):
            raise EvaluationSafetyError("diagnostic stage count mismatch")
    except TimeBudgetExhausted:
        persist("incomplete_time_budget")
        progress = _read_json_object(progress_path, "progress")
        summary = {
            "schema_version": 1,
            "experiment_id": run_id,
            "run_status": "incomplete_time_budget",
            "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "git_commit": args.approved_protocol_commit,
            "approval_reference": args.approval_reference,
            "completed_records": progress["completed_records"],
            "prediction_sha256": progress["prediction_sha256"],
            "elapsed_seconds": budget.elapsed_seconds(),
            "safe_stop_elapsed_seconds": SAFE_STOP_ELAPSED_SECONDS,
            "metrics_reported": False,
            "resume_requires_fresh_authorization": True,
            "contains_corpus_text": False,
        }
        _write_json_atomic(public_summary_path, summary)
        return summary
    except Exception as error:
        persist("invalid")
        _write_json_atomic(
            run_dir / "failure.json",
            {
                "schema_version": 1,
                "experiment_id": run_id,
                "run_status": "invalid",
                "git_commit": args.approved_protocol_commit,
                "error_type": type(error).__name__,
                "completed_records": dict(completed),
                "contains_corpus_text": False,
            },
        )
        raise

    systems = {
        system: {
            **_system_counts(
                rows[f"{system}_overcorrection"],
                rows[f"{system}_capability"],
            ),
            "runtime": runtimes[system],
            "adapter": adapter_meta[system],
            "prediction_sha256": {
                "overcorrection": sha256_file(paths[f"{system}_overcorrection"]),
                "capability": sha256_file(paths[f"{system}_capability"]),
            },
        }
        for system in SYSTEMS
    }
    over_comparisons = {
        "primary_f3_minus_f2": paired_binary_comparison(
            rows["F2-P1_overcorrection"],
            rows["F3-P1_overcorrection"],
            outcome_field="unchanged_exact",
            bootstrap_samples=BOOTSTRAP_SAMPLES,
            seed=SEED,
        ),
        "staged_f2_minus_b0": paired_binary_comparison(
            reference_rows["B0_overcorrection"],
            rows["F2-P1_overcorrection"],
            outcome_field="unchanged_exact",
            bootstrap_samples=BOOTSTRAP_SAMPLES,
            seed=SEED,
        ),
        "staged_f3_minus_b0": paired_binary_comparison(
            reference_rows["B0_overcorrection"],
            rows["F3-P1_overcorrection"],
            outcome_field="unchanged_exact",
            bootstrap_samples=BOOTSTRAP_SAMPLES,
            seed=SEED,
        ),
        "staged_f2_minus_f1": paired_binary_comparison(
            reference_rows["F1-P1_overcorrection"],
            rows["F2-P1_overcorrection"],
            outcome_field="unchanged_exact",
            bootstrap_samples=BOOTSTRAP_SAMPLES,
            seed=SEED,
        ),
        "staged_f3_minus_f1": paired_binary_comparison(
            reference_rows["F1-P1_overcorrection"],
            rows["F3-P1_overcorrection"],
            outcome_field="unchanged_exact",
            bootstrap_samples=BOOTSTRAP_SAMPLES,
            seed=SEED,
        ),
    }
    capability_comparisons = {
        "primary_f3_minus_f2": paired_binary_comparison(
            rows["F2-P1_capability"],
            rows["F3-P1_capability"],
            outcome_field="exact_match",
            stratum_field="task",
            bootstrap_samples=BOOTSTRAP_SAMPLES,
            seed=SEED,
        ),
        "staged_f2_minus_b0": paired_binary_comparison(
            reference_rows["B0_capability"],
            rows["F2-P1_capability"],
            outcome_field="exact_match",
            stratum_field="task",
            bootstrap_samples=BOOTSTRAP_SAMPLES,
            seed=SEED,
        ),
        "staged_f3_minus_b0": paired_binary_comparison(
            reference_rows["B0_capability"],
            rows["F3-P1_capability"],
            outcome_field="exact_match",
            stratum_field="task",
            bootstrap_samples=BOOTSTRAP_SAMPLES,
            seed=SEED,
        ),
        "staged_f2_minus_f1": paired_binary_comparison(
            reference_rows["F1-P1_capability"],
            rows["F2-P1_capability"],
            outcome_field="exact_match",
            stratum_field="task",
            bootstrap_samples=BOOTSTRAP_SAMPLES,
            seed=SEED,
        ),
        "staged_f3_minus_f1": paired_binary_comparison(
            reference_rows["F1-P1_capability"],
            rows["F3-P1_capability"],
            outcome_field="exact_match",
            stratum_field="task",
            bootstrap_samples=BOOTSTRAP_SAMPLES,
            seed=SEED,
        ),
    }
    reference_systems = {
        system: {
            "overcorrection": _system_counts(
                reference_rows[f"{system}_overcorrection"],
                reference_rows[f"{system}_capability"],
            )["overcorrection"],
            "capability": _system_counts(
                reference_rows[f"{system}_overcorrection"],
                reference_rows[f"{system}_capability"],
            )["capability"],
            "prediction_sha256": {
                "overcorrection": REFERENCE_PREDICTION_SHA256[f"{system}_overcorrection"],
                "capability": REFERENCE_PREDICTION_SHA256[f"{system}_capability"],
            },
            "comparison_status": "immutable_staged_reference",
        }
        for system in ("B0", "F1-P1")
    }
    summary = {
        "schema_version": 1,
        "experiment_id": run_id,
        "run_status": "complete",
        "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "git_commit": args.approved_protocol_commit,
        "approval_reference": args.approval_reference,
        "data": {
            "overcorrection": {"records": 154, "input_sha256": EXPECTED_OVERCORRECTION_SHA256},
            "capability": {"records": 1_000, "input_sha256": EXPECTED_CAPABILITY_SHA256},
        },
        "comparisons": {
            "overcorrection_unchanged_accuracy": over_comparisons,
            "arabicmmlu_micro_accuracy": capability_comparisons,
        },
        "systems": {**reference_systems, **systems},
        "elapsed_seconds": budget.elapsed_seconds(),
        "metrics_reported": True,
        "safeguards": {
            "training": False,
            "checkpoint_selection": False,
            "nahw_passage_used": False,
            "qalb_test_used": False,
            "new_data_selection": False,
            "per_record_fsync": True,
            "atomic_progress_manifest": True,
            "resume_requires_fresh_authorization": True,
            "contains_corpus_text": False,
        },
    }
    persist("complete")
    _write_json_atomic(public_summary_path, summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--f2-adapter", type=Path, required=True)
    parser.add_argument("--f3-adapter", type=Path, required=True)
    parser.add_argument("--overcorrection-input", type=Path, default=DEFAULT_INPUTS / "overcorrection.jsonl")
    parser.add_argument("--capability-input", type=Path, default=DEFAULT_INPUTS / "arabicmmlu.jsonl")
    parser.add_argument("--b0-overcorrection-predictions", type=Path, required=True)
    parser.add_argument("--f1-overcorrection-predictions", type=Path, required=True)
    parser.add_argument("--b0-capability-predictions", type=Path, required=True)
    parser.add_argument("--f1-capability-predictions", type=Path, required=True)
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
    if not args.execute:
        print(json.dumps({
            "status": "disabled",
            "private_input_accessed": False,
            "model_loaded": False,
            "inference_executed": False,
            "metrics_computed": False,
        }, indent=2))
        return
    try:
        if not 1 <= args.replicate <= 99:
            raise EvaluationSafetyError("replicate must be between 1 and 99")
        if args.kernel_start_epoch_seconds is None:
            raise EvaluationSafetyError("kernel start epoch seconds are required")
        require_execution_authorization(
            args.confirmation,
            args.approved_protocol_commit,
            args.approval_reference,
            repository=ROOT,
        )
        adapter_meta = {
            "F2-P1": validate_adapter_checkpoint(args.f2_adapter, ARM_SPECS["F2-P1"]),
            "F3-P1": validate_adapter_checkpoint(args.f3_adapter, ARM_SPECS["F3-P1"]),
        }
        overcorrection_records = load_overcorrection_records(args.overcorrection_input)
        capability_records = load_capability_records(args.capability_input)
        reference_rows = load_reference_predictions(
            {
                "B0_overcorrection": args.b0_overcorrection_predictions,
                "F1-P1_overcorrection": args.f1_overcorrection_predictions,
                "B0_capability": args.b0_capability_predictions,
                "F1-P1_capability": args.f1_capability_predictions,
            },
            overcorrection_records=overcorrection_records,
            capability_records=capability_records,
        )
        validate_outputs_root(args.outputs_root)
        summary = execute(
            args,
            overcorrection_records=overcorrection_records,
            capability_records=capability_records,
            adapter_meta=adapter_meta,
            reference_rows=reference_rows,
        )
        print(json.dumps({
            "experiment_id": summary["experiment_id"],
            "run_status": summary["run_status"],
        }, indent=2))
    except (EvaluationSafetyError, OSError) as error:
        raise SystemExit(f"ERROR: {error}") from error


if __name__ == "__main__":
    main()
