#!/usr/bin/env python3
"""Safeguarded prompt-baseline run scaffolding.

This module prepares canonical experiment artifact directories and metadata.
Full model inference remains an explicit runtime step; final Nahw-Passage runs
are disabled unless the caller opts in deliberately.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import time

from scripts.baseline_prompts import (
    PromptDemo,
    prompt_sha256,
    render_b1_prompt,
    render_b2_prompt,
)
from scripts.nahw_baseline_utils import parse_model_response


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUTS = ROOT / "outputs"
DEFAULT_MAX_NEW_TOKENS = 32
SAFE_STOP_ELAPSED_SECONDS = 34_200
PROGRESS_SCHEMA_VERSION = 1
FINAL_CONFIRMATION = "RUN_B1_B2_NAHW_FINAL_TIMEOUT_SAFE"
FINAL_MODEL_ID = "unsloth/gemma-3-4b-it-unsloth-bnb-4bit"
FINAL_MODEL_REVISION = "316726ca0bd24aa323bfaf86e8a379ee1176d1fe"
FINAL_INPUT_SHA256 = (
    "acb3cfd204b35d5415532fbd32a4a5231b553fae329ab8f48e8454609e10279b"
)
FINAL_B1_BUNDLE_SHA256 = (
    "760674f0d6cc85c48b2be18d175b87e2025cd3d01fde31a6e25afaa08f9fc11a"
)
APPROVAL_PATTERN = re.compile(
    r"https://github\.com/ALBA7OOTH-Research-Lab/Musahhih/"
    r"issues/[1-9][0-9]*#issuecomment-[1-9][0-9]*"
)
PRIVATE_REPOSITORY_ROOTS = (
    ROOT / "data" / "processed",
    DEFAULT_OUTPUTS,
)
EXPERIMENT_ID_RE = re.compile(
    r"^(B[0-2]|F[1-4])-P[0-9]+__"
    r"[a-z0-9][a-z0-9.-]*__"
    r"[a-z0-9][a-z0-9.-]*__"
    r"s[0-9]+__r[0-9]{2}$"
)


class RunSafetyError(ValueError):
    """Raised when a baseline run would violate a frozen safety rule."""


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
            raise RunSafetyError("kernel start time is in the future")

    def elapsed_seconds(self) -> int:
        return max(0, int(self._now() - self.kernel_start_epoch_seconds))

    def require_next_record_budget(self) -> None:
        if self.elapsed_seconds() >= self.safe_stop_elapsed_seconds:
            raise TimeBudgetExhausted


@dataclass(frozen=True)
class PromptRecord:
    record_id: str
    passage: str
    error: str
    gold_correction: str | None
    metadata: dict


@dataclass(frozen=True)
class RunConfig:
    experiment_id: str
    protocol_id: str
    model_slug: str
    evaluation_slug: str
    seed: int
    replicate: int


class GemmaGenerator:
    """Lazy, revision-pinned greedy Gemma generation backend."""

    def __init__(
        self,
        model_id: str,
        revision: str,
        max_new_tokens: int,
        *,
        seed: int = 3407,
        require_p100: bool = False,
    ) -> None:
        self.model_id = model_id
        self.revision = revision
        self.max_new_tokens = max_new_tokens
        self.seed = seed
        self.require_p100 = require_p100
        self.processor = None
        self.model = None
        self.metadata = {
            "backend": "unsloth",
            "model_id": model_id,
            "model_revision": revision,
            "max_new_tokens": max_new_tokens,
            "do_sample": False,
            "temperature": None,
            "seed": seed,
            "python_version": platform.python_version(),
        }

    def _load(self) -> None:
        try:
            import torch
            from unsloth import FastModel
        except (ImportError, OSError) as error:
            raise RunSafetyError("Gemma inference dependencies are unavailable") from error

        if self.require_p100:
            if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
                raise RunSafetyError(
                    "B1/B2 final execution requires exactly one CUDA device"
                )
            device_name = torch.cuda.get_device_name(0)
            if "P100" not in device_name.upper():
                raise RunSafetyError("B1/B2 final execution requires a P100 GPU")
        else:
            device_name = (
                torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
            )
        torch.manual_seed(self.seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(self.seed)
            dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
            device = "cuda"
        else:
            dtype = torch.float32
            device = "cpu"
        try:
            self.model, self.processor = FastModel.from_pretrained(
                model_name=self.model_id,
                revision=self.revision,
                max_seq_length=2048,
                dtype=dtype,
                load_in_4bit=True,
                full_finetuning=False,
            )
            self.model.eval()
        except Exception as error:
            raise RunSafetyError("unable to initialize pinned Gemma backend") from error
        self.metadata.update(
            {
                "torch_version": torch.__version__,
                "transformers_version": importlib.metadata.version("transformers"),
                "unsloth_version": importlib.metadata.version("unsloth"),
                "device": device,
                "dtype": str(dtype),
                "load_in_4bit": True,
                "cuda_available": torch.cuda.is_available(),
                "cuda_device_count": (
                    torch.cuda.device_count() if torch.cuda.is_available() else 0
                ),
                "device_name": device_name,
                "require_p100": self.require_p100,
            }
        )

    def __call__(self, prompt: str) -> str:
        if self.model is None or self.processor is None:
            self._load()
        messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
        inputs = self.processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(self.model.device)
        input_length = inputs["input_ids"].shape[-1]
        if input_length > 2048:
            raise RunSafetyError("rendered prompt exceeds the frozen 2048-token limit")
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=self.max_new_tokens,
            do_sample=False,
        )
        return self.processor.decode(
            outputs[0][input_length:],
            skip_special_tokens=True,
        )


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def validate_private_path(path: Path, *, label: str) -> Path:
    """Reject text-bearing repository paths outside ignored private roots."""

    resolved = Path(path).expanduser().resolve()
    if _is_relative_to(resolved, ROOT) and not any(
        _is_relative_to(resolved, root) for root in PRIVATE_REPOSITORY_ROOTS
    ):
        raise RunSafetyError(
            f"{label} path inside the repository must stay under "
            "data/processed/ or outputs/"
        )
    return resolved


def _require_string(value: object, *, field: str, line_number: int) -> str:
    if not isinstance(value, str):
        raise RunSafetyError(f"{field} must be a string at input line {line_number}")
    return value


def load_prompt_records(path: Path) -> list[PromptRecord]:
    """Load private prompt records without logging text-bearing fields."""

    input_path = validate_private_path(path, label="input")
    records: list[PromptRecord] = []
    seen_ids: set[str] = set()
    try:
        with input_path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as error:
                    raise RunSafetyError(
                        f"invalid JSON at input line {line_number}"
                    ) from error
                if not isinstance(payload, dict):
                    raise RunSafetyError(
                        f"input line {line_number} must be a JSON object"
                    )
                record_id = _require_string(
                    payload.get("record_id"),
                    field="record_id",
                    line_number=line_number,
                )
                if not record_id:
                    raise RunSafetyError(
                        f"record_id must be non-empty at input line {line_number}"
                    )
                if record_id in seen_ids:
                    raise RunSafetyError(f"duplicate record_id at input line {line_number}")
                passage = _require_string(
                    payload.get("passage"),
                    field="passage",
                    line_number=line_number,
                )
                error = _require_string(
                    payload.get("error"),
                    field="error",
                    line_number=line_number,
                )
                if not error:
                    raise RunSafetyError(
                        f"error must be non-empty at input line {line_number}"
                    )
                gold = payload.get("gold_correction")
                if gold is not None and not isinstance(gold, str):
                    raise RunSafetyError(
                        "gold_correction must be a string or null at "
                        f"input line {line_number}"
                    )
                metadata = payload.get("metadata", {})
                if not isinstance(metadata, dict):
                    raise RunSafetyError(
                        f"metadata must be an object at input line {line_number}"
                    )
                records.append(
                    PromptRecord(
                        record_id=record_id,
                        passage=passage,
                        error=error,
                        gold_correction=gold,
                        metadata=metadata,
                    )
                )
                seen_ids.add(record_id)
    except OSError as error:
        raise RunSafetyError("unable to read private input file") from error
    if not records:
        raise RunSafetyError("private input file contains no records")
    return records


def load_b1_demos(path: Path) -> list[PromptDemo]:
    """Load exactly five demonstrations from the existing private bundle."""

    bundle_path = validate_private_path(path, label="bundle")
    try:
        payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RunSafetyError("unable to read valid private B1 bundle") from error
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise RunSafetyError("B1 bundle must use schema_version 1")
    rows = payload.get("demonstrations")
    if not isinstance(rows, list) or len(rows) != 5:
        raise RunSafetyError("B1 bundle must contain exactly five demonstrations")
    demos: list[PromptDemo] = []
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise RunSafetyError(f"B1 demonstration {index} must be an object")
        values = []
        for field in ("source", "error", "correction"):
            value = row.get(field)
            if not isinstance(value, str):
                raise RunSafetyError(
                    f"B1 demonstration {index} {field} must be a string"
                )
            values.append(value)
        demos.append(PromptDemo(*values))
    return demos


def load_protocol_demos(
    protocol_id: str,
    bundle_path: Path | None,
) -> list[PromptDemo]:
    if protocol_id == "B1-P1":
        if bundle_path is None:
            raise RunSafetyError("B1-P1 requires --bundle")
        return load_b1_demos(bundle_path)
    if protocol_id == "B2-P1":
        if bundle_path is not None:
            raise RunSafetyError("B2-P1 does not accept --bundle")
        return []
    raise RunSafetyError(f"Unsupported prompt protocol: {protocol_id}")


def validate_output_root(
    outputs_root: Path,
    *,
    allow_outside_private_output: bool,
) -> Path:
    resolved = Path(outputs_root).expanduser().resolve()
    if not allow_outside_private_output and not _is_relative_to(
        resolved, DEFAULT_OUTPUTS
    ):
        raise RunSafetyError(
            "private outputs must stay under outputs/ unless "
            "--allow-outside-private-output is set"
        )
    validate_private_path(resolved, label="output")
    return resolved


def render_record_prompt(
    protocol_id: str,
    demos: list[PromptDemo],
    record: PromptRecord,
) -> str:
    if protocol_id == "B1-P1":
        return render_b1_prompt(demos, record.passage, record.error)
    if protocol_id == "B2-P1":
        if demos:
            raise RunSafetyError("B2-P1 cannot render with demonstrations")
        return render_b2_prompt(record.passage, record.error)
    raise RunSafetyError(f"Unsupported prompt protocol: {protocol_id}")


def aggregate_prompt_sha256(prompt_hashes: list[str]) -> str:
    return hashlib.sha256("\n".join(prompt_hashes).encode("utf-8")).hexdigest()


def summarize_prompt_predictions(
    rows: list[dict],
    *,
    expected_records: int,
) -> dict:
    scored = [row for row in rows if row["exact_match"] is not None]
    return {
        "number_of_records": expected_records,
        "completed_records": len(rows),
        "number_scored": len(scored),
        "number_correct": sum(row["exact_match"] is True for row in scored),
        "invalid_or_empty_count": sum(
            not row["parsed_correction"] for row in rows
        ),
        "suspicious_output_count": sum(
            bool(set(row["parsing_warnings"]) - {"outer_formatting_removed"})
            for row in rows
        ),
        "multi_token_count": sum(
            "multiple_words" in row["parsing_warnings"] for row in rows
        ),
    }


def _fsync_stream(stream) -> None:
    stream.flush()
    os.fsync(stream.fileno())


def _fsync_path(path: Path) -> None:
    with Path(path).open("r+b") as stream:
        os.fsync(stream.fileno())


def _write_json_atomic(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        )
        _fsync_stream(stream)
    temporary.replace(path)


def _write_summary(path: Path, summary: dict) -> None:
    _write_json_atomic(path, summary)


def _read_json_object(path: Path, *, label: str) -> dict:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RunSafetyError(f"invalid {label}") from error
    if not isinstance(value, dict):
        raise RunSafetyError(f"{label} must be a JSON object")
    return value


def _read_prediction_rows(path: Path, *, label: str) -> list[dict]:
    if not Path(path).is_file():
        return []
    try:
        with Path(path).open("r", encoding="utf-8") as stream:
            rows = [json.loads(line) for line in stream if line.strip()]
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RunSafetyError(f"invalid private {label} prediction prefix") from error
    if not all(isinstance(row, dict) for row in rows):
        raise RunSafetyError(f"invalid private {label} prediction rows")
    return rows


def _prediction_row(
    *,
    record: PromptRecord,
    prompt: str,
    raw_response: str,
) -> dict:
    parsed, warnings = parse_model_response(raw_response)
    exact_match = (
        parsed == record.gold_correction
        if record.gold_correction is not None
        else None
    )
    return {
        "record_id": record.record_id,
        "metadata": record.metadata,
        "prompt": prompt,
        "prompt_sha256": prompt_sha256(prompt),
        "raw_response": raw_response,
        "parsed_correction": parsed,
        "parsing_warnings": warnings,
        "gold_correction": record.gold_correction,
        "exact_match": exact_match,
    }


def _validate_prediction_prefix(
    rows: list[dict],
    records: list[PromptRecord],
    demos: list[PromptDemo],
    *,
    protocol_id: str,
) -> None:
    expected_keys = {
        "record_id",
        "metadata",
        "prompt",
        "prompt_sha256",
        "raw_response",
        "parsed_correction",
        "parsing_warnings",
        "gold_correction",
        "exact_match",
    }
    if len(rows) > len(records):
        raise RunSafetyError("resume prediction prefix is too long")
    for index, row in enumerate(rows):
        record = records[index]
        prompt = render_record_prompt(protocol_id, demos, record)
        if set(row) != expected_keys:
            raise RunSafetyError("resume prediction row schema mismatch")
        expected = {
            "record_id": record.record_id,
            "metadata": record.metadata,
            "prompt": prompt,
            "prompt_sha256": prompt_sha256(prompt),
            "gold_correction": record.gold_correction,
        }
        if any(row.get(field) != value for field, value in expected.items()):
            raise RunSafetyError("resume prediction record mismatch")
        if not isinstance(row.get("raw_response"), str):
            raise RunSafetyError("resume prediction response mismatch")
        if not isinstance(row.get("parsed_correction"), str):
            raise RunSafetyError("resume prediction parse mismatch")
        warnings = row.get("parsing_warnings")
        if not isinstance(warnings, list) or not all(
            isinstance(warning, str) for warning in warnings
        ):
            raise RunSafetyError("resume prediction warnings mismatch")
        expected_parse, expected_warnings = parse_model_response(row["raw_response"])
        if (
            row["parsed_correction"] != expected_parse
            or warnings != expected_warnings
        ):
            raise RunSafetyError("resume prediction parser consistency mismatch")
        expected_exact = (
            row["parsed_correction"] == record.gold_correction
            if record.gold_correction is not None
            else None
        )
        if row.get("exact_match") is not expected_exact:
            raise RunSafetyError("resume prediction score mismatch")


def _execution_identity(
    config: RunConfig,
    *,
    input_path: Path,
    prompt_template_path: Path,
    bundle_path: Path | None,
    model_id: str,
    model_revision: str,
    max_new_tokens: int,
    approved_protocol_commit: str | None,
) -> dict:
    return {
        "experiment_id": config.experiment_id,
        "protocol_id": config.protocol_id,
        "seed": config.seed,
        "input_sha256": sha256_file(input_path),
        "prompt_template_sha256": sha256_file(prompt_template_path),
        "bundle_sha256": sha256_file(bundle_path),
        "model_id": model_id,
        "model_revision": model_revision,
        "max_new_tokens": max_new_tokens,
        "approved_protocol_commit": approved_protocol_commit,
    }


def _load_resume_prefix(
    resume_from: Path | None,
    *,
    records: list[PromptRecord],
    demos: list[PromptDemo],
    config: RunConfig,
    identity: dict,
) -> tuple[list[dict], Path | None, dict]:
    if resume_from is None:
        return [], None, {}
    resume_dir = validate_private_path(resume_from, label="resume").resolve()
    if _is_relative_to(resume_dir, ROOT) and not _is_relative_to(
        resume_dir, DEFAULT_OUTPUTS.resolve()
    ):
        raise RunSafetyError(
            "repository-local resume artifacts must stay under outputs/"
        )
    summary = _read_json_object(
        resume_dir / "summary.json", label="resume summary"
    )
    progress = _read_json_object(
        resume_dir / "progress.json", label="resume progress"
    )
    if summary.get("run_status") != "incomplete_time_budget":
        raise RunSafetyError("resume source is not a timed handoff")
    if progress.get("schema_version") != PROGRESS_SCHEMA_VERSION:
        raise RunSafetyError("resume progress schema mismatch")
    if progress.get("status") != "incomplete_time_budget":
        raise RunSafetyError("resume progress status mismatch")
    if progress.get("identity") != identity:
        raise RunSafetyError("resume execution identity mismatch")
    if progress.get("contains_corpus_text") is not False:
        raise RunSafetyError("resume progress privacy marker mismatch")
    if summary.get("execution_identity") != identity:
        raise RunSafetyError("resume summary identity mismatch")
    if summary.get("metrics_reported") is not False:
        raise RunSafetyError("resume source reports a partial metric")
    if summary.get("contains_corpus_text") is not False:
        raise RunSafetyError("resume summary privacy marker mismatch")
    if summary.get("git_commit") != identity.get("approved_protocol_commit"):
        raise RunSafetyError("resume source commit mismatch")
    predictions_path = resume_dir / "predictions.jsonl"
    rows = _read_prediction_rows(
        predictions_path, label=config.protocol_id
    )
    _validate_prediction_prefix(
        rows, records, demos, protocol_id=config.protocol_id
    )
    if progress.get("completed_records") != len(rows):
        raise RunSafetyError("resume completed-record count mismatch")
    if summary.get("completed_records") != len(rows):
        raise RunSafetyError("resume summary completed-record count mismatch")
    expected_hash = progress.get("prediction_sha256")
    if summary.get("prediction_sha256") != expected_hash:
        raise RunSafetyError("resume summary prediction hash mismatch")
    if predictions_path.is_file():
        if not isinstance(expected_hash, str):
            raise RunSafetyError("resume prediction hash missing")
        if sha256_file(predictions_path) != expected_hash:
            raise RunSafetyError("resume prediction SHA-256 mismatch")
    elif expected_hash is not None:
        raise RunSafetyError("missing resume prediction prefix mismatch")
    runtime = progress.get("runtime")
    if not isinstance(runtime, dict):
        raise RunSafetyError("resume runtime metadata mismatch")
    return rows, predictions_path if predictions_path.is_file() else None, runtime


def _progress_payload(
    *,
    identity: dict,
    predictions_path: Path,
    completed_records: int,
    runtime: dict,
    budget: KernelTimeBudget | None,
    status: str,
) -> dict:
    return {
        "schema_version": PROGRESS_SCHEMA_VERSION,
        "status": status,
        "identity": identity,
        "completed_records": completed_records,
        "prediction_sha256": (
            sha256_file(predictions_path) if predictions_path.is_file() else None
        ),
        "runtime": dict(runtime),
        "elapsed_seconds": budget.elapsed_seconds() if budget is not None else None,
        "contains_corpus_text": False,
    }


def execute_run(
    config: RunConfig,
    records: list[PromptRecord],
    demos: list[PromptDemo],
    generate: Callable[[str], str],
    *,
    outputs_root: Path,
    input_path: Path,
    prompt_template_path: Path,
    bundle_path: Path | None = None,
    runtime_metadata: dict | None = None,
    allow_outside_private_output: bool = False,
    budget: KernelTimeBudget | None = None,
    resume_from: Path | None = None,
    model_id: str = "",
    model_revision: str = "",
    max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS,
    approved_protocol_commit: str | None = None,
) -> dict:
    """Execute a private prompt run while retaining auditable failure artifacts."""

    validate_experiment_id(config.experiment_id)
    if not records:
        raise RunSafetyError("prompt inference requires at least one record")
    if config.protocol_id == "B1-P1" and len(demos) != 5:
        raise RunSafetyError("B1-P1 requires exactly five demonstrations")
    if config.protocol_id == "B2-P1" and demos:
        raise RunSafetyError("B2-P1 cannot execute with demonstrations")
    input_path = validate_private_path(input_path, label="input")
    prompt_template_path = Path(prompt_template_path).expanduser().resolve()
    if bundle_path is not None:
        bundle_path = validate_private_path(bundle_path, label="bundle")
    try:
        sha256_file(input_path)
        sha256_file(prompt_template_path)
        sha256_file(bundle_path)
    except OSError as error:
        raise RunSafetyError("unable to hash required run input") from error
    safe_outputs = validate_output_root(
        outputs_root,
        allow_outside_private_output=allow_outside_private_output,
    )
    identity = _execution_identity(
        config,
        input_path=input_path,
        prompt_template_path=prompt_template_path,
        bundle_path=bundle_path,
        model_id=model_id,
        model_revision=model_revision,
        max_new_tokens=max_new_tokens,
        approved_protocol_commit=approved_protocol_commit,
    )
    prefix_rows, prefix_path, resume_runtime = _load_resume_prefix(
        resume_from,
        records=records,
        demos=demos,
        config=config,
        identity=identity,
    )
    run_dir = prepare_run_directory(safe_outputs, config.experiment_id)
    predictions_path = run_dir / "predictions.jsonl"
    summary_path = run_dir / "summary.json"
    progress_path = run_dir / "progress.json"
    log_path = run_dir / "run.log"
    prediction_rows = list(prefix_rows)
    prompt_hashes = [row["prompt_sha256"] for row in prefix_rows]
    effective_runtime = runtime_metadata if runtime_metadata is not None else {}
    for field, value in resume_runtime.items():
        effective_runtime.setdefault(field, value)
    if prefix_path is not None:
        shutil.copyfile(prefix_path, predictions_path)
        _fsync_path(predictions_path)

    def persist_progress(status: str) -> None:
        _write_json_atomic(
            progress_path,
            _progress_payload(
                identity=identity,
                predictions_path=predictions_path,
                completed_records=len(prediction_rows),
                runtime=effective_runtime,
                budget=budget,
                status=status,
            ),
        )

    persist_progress("running")
    try:
        mode = "a" if predictions_path.is_file() else "x"
        with predictions_path.open(mode, encoding="utf-8", newline="\n") as stream:
            for record in records[len(prediction_rows) :]:
                if budget is not None:
                    budget.require_next_record_budget()
                prompt = render_record_prompt(config.protocol_id, demos, record)
                raw_response = generate(prompt)
                if not isinstance(raw_response, str):
                    raise TypeError("generation backend must return a string")
                row = _prediction_row(
                    record=record,
                    prompt=prompt,
                    raw_response=raw_response,
                )
                stream.write(
                    json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                )
                _fsync_stream(stream)
                prediction_rows.append(row)
                prompt_hashes.append(row["prompt_sha256"])
                persist_progress("running")
        if len(prediction_rows) != len(records):
            raise RunSafetyError("prompt inference did not complete every record")
        persist_progress("complete")
        summary = build_summary(
            config,
            input_path=input_path,
            prompt_template_path=prompt_template_path,
            predictions_path=predictions_path,
            bundle_path=bundle_path,
            run_status="complete",
        )
        summary.update(
            {
                "aggregate_prompt_sha256": aggregate_prompt_sha256(prompt_hashes),
                "counts": summarize_prompt_predictions(
                    prediction_rows,
                    expected_records=len(records),
                ),
                "runtime": effective_runtime,
                "execution_identity": identity,
                "metrics_reported": True,
            }
        )
        _write_summary(summary_path, summary)
        with log_path.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write("run completed\n")
        return summary
    except TimeBudgetExhausted:
        persist_progress("incomplete_time_budget")
        handoff_summary = build_summary(
            config,
            input_path=input_path,
            prompt_template_path=prompt_template_path,
            predictions_path=(
                predictions_path if predictions_path.exists() else None
            ),
            bundle_path=bundle_path,
            run_status="incomplete_time_budget",
        )
        handoff_summary.update(
            {
                "schema_version": 2,
                "completed_records": len(prediction_rows),
                "expected_records": len(records),
                "elapsed_seconds": (
                    budget.elapsed_seconds() if budget is not None else None
                ),
                "safe_stop_elapsed_seconds": (
                    budget.safe_stop_elapsed_seconds
                    if budget is not None
                    else SAFE_STOP_ELAPSED_SECONDS
                ),
                "runtime": effective_runtime,
                "execution_identity": identity,
                "metrics_reported": False,
                "contains_corpus_text": False,
                "resume_requires_fresh_authorization": True,
            }
        )
        _write_summary(summary_path, handoff_summary)
        with log_path.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(
                "safe wall-time stop; private handoff preserved; "
                "fresh GO required\n"
            )
        return handoff_summary
    except Exception as error:
        persist_progress("invalid")
        invalid_summary = build_summary(
            config,
            input_path=input_path,
            prompt_template_path=prompt_template_path,
            predictions_path=(predictions_path if predictions_path.exists() else None),
            bundle_path=bundle_path,
            run_status="invalid",
        )
        if config.evaluation_slug == "nahw-passage":
            counts = {
                "number_of_records": len(records),
                "completed_records": len(prediction_rows),
            }
            metrics_reported = False
        else:
            counts = summarize_prompt_predictions(
                prediction_rows,
                expected_records=len(records),
            )
            metrics_reported = True
        invalid_summary.update(
            {
                "aggregate_prompt_sha256": aggregate_prompt_sha256(prompt_hashes),
                "counts": counts,
                "runtime": effective_runtime,
                "execution_identity": identity,
                "metrics_reported": metrics_reported,
                "error_type": type(error).__name__,
            }
        )
        _write_summary(summary_path, invalid_summary)
        with log_path.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write("run invalid: inference execution failed\n")
        raise RunSafetyError("inference execution failed; run preserved as invalid") from error


def experiment_id(
    protocol_id: str,
    model_slug: str,
    evaluation_slug: str,
    seed: int,
    replicate: int,
) -> str:
    run_id = f"{protocol_id}__{model_slug}__{evaluation_slug}__s{seed}__r{replicate:02d}"
    return validate_experiment_id(run_id)


def validate_experiment_id(run_id: str) -> str:
    if not EXPERIMENT_ID_RE.fullmatch(run_id):
        raise RunSafetyError(f"Invalid experiment ID: {run_id}")
    return run_id


def assert_final_eval_allowed(evaluation_slug: str, *, confirm_final_eval: bool) -> None:
    if evaluation_slug == "nahw-passage" and not confirm_final_eval:
        raise RunSafetyError(
            "Nahw-Passage final evaluation requires explicit confirmation"
        )


def prepare_run_directory(outputs_root: Path, run_id: str) -> Path:
    run_id = validate_experiment_id(run_id)
    run_dir = Path(outputs_root) / run_id
    try:
        run_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise RunSafetyError(f"Run directory already exists: {run_dir}") from error
    return run_dir


def sha256_file(path: Path | None) -> str | None:
    if path is None:
        return None
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit_sha() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def require_final_execution_authorization(
    *,
    confirmation: str | None,
    approved_protocol_commit: str | None,
    approval_reference: str | None,
    model_id: str,
    model_revision: str,
    max_new_tokens: int,
    config: RunConfig,
    input_path: Path,
    bundle_path: Path | None,
    record_count: int,
) -> None:
    """Fail closed on every frozen B1/B2 Nahw final-execution identity."""

    if confirmation != FINAL_CONFIRMATION:
        raise RunSafetyError("exact B1/B2 final confirmation is required")
    if not approved_protocol_commit or not re.fullmatch(
        r"[0-9a-f]{40}", approved_protocol_commit
    ):
        raise RunSafetyError("approved protocol commit must be lowercase SHA-1")
    if git_commit_sha() != approved_protocol_commit:
        raise RunSafetyError("checkout is not the exact approved protocol commit")
    if not approval_reference or not APPROVAL_PATTERN.fullmatch(approval_reference):
        raise RunSafetyError("approval must be a Musahhih issue-comment URL")
    if model_id != FINAL_MODEL_ID or model_revision != FINAL_MODEL_REVISION:
        raise RunSafetyError("B1/B2 final model identity mismatch")
    if max_new_tokens != DEFAULT_MAX_NEW_TOKENS:
        raise RunSafetyError("B1/B2 final max_new_tokens must remain 32")
    if config.seed != 3407 or config.evaluation_slug != "nahw-passage":
        raise RunSafetyError("B1/B2 final seed or evaluation identity mismatch")
    if record_count != 511 or sha256_file(input_path) != FINAL_INPUT_SHA256:
        raise RunSafetyError("B1/B2 frozen final input identity mismatch")
    if config.protocol_id == "B1-P1":
        if bundle_path is None or sha256_file(bundle_path) != FINAL_B1_BUNDLE_SHA256:
            raise RunSafetyError("B1-P1 frozen bundle identity mismatch")
    elif bundle_path is not None:
        raise RunSafetyError("B2-P1 final execution cannot use a bundle")


def build_summary(
    config: RunConfig,
    *,
    input_path: Path,
    prompt_template_path: Path,
    predictions_path: Path | None = None,
    bundle_path: Path | None = None,
    run_status: str = "planned",
) -> dict:
    """Build a corpus-text-free summary from artifact hashes."""

    validate_experiment_id(config.experiment_id)
    return {
        "schema_version": 1,
        "experiment_id": config.experiment_id,
        "run_status": run_status,
        "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "git_commit": git_commit_sha(),
        "config": asdict(config),
        "input_sha256": sha256_file(input_path),
        "prompt_template_sha256": sha256_file(prompt_template_path),
        "bundle_sha256": sha256_file(bundle_path),
        "prediction_sha256": sha256_file(predictions_path),
        "artifact_layout": {
            "predictions": "predictions.jsonl",
            "progress": "progress.json",
            "summary": "summary.json",
            "log": "run.log",
        },
        "safeguards": {
            "nahw_passage_requires_explicit_confirmation": True,
            "overwrite_existing_run_directory": False,
            "summary_contains_private_text": False,
            "per_record_fsync": True,
            "atomic_progress_manifest": True,
            "partial_metrics_reported": False,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-id", required=True, choices=("B1-P1", "B2-P1"))
    parser.add_argument("--model-slug", default="gemma3-4b-it")
    parser.add_argument("--model", default=FINAL_MODEL_ID)
    parser.add_argument("--model-revision")
    parser.add_argument("--max-new-tokens", type=int, default=DEFAULT_MAX_NEW_TOKENS)
    parser.add_argument("--evaluation-slug", required=True)
    parser.add_argument("--seed", type=int, default=3407)
    parser.add_argument("--replicate", type=int, default=1)
    parser.add_argument("--outputs-root", type=Path, default=DEFAULT_OUTPUTS)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--prompt-template", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, default=None)
    parser.add_argument("--confirm-final-eval", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--kernel-start-epoch-seconds", type=float)
    parser.add_argument("--resume-from", type=Path)
    parser.add_argument("--confirmation")
    parser.add_argument("--approved-protocol-commit")
    parser.add_argument("--approval-reference")
    parser.add_argument("--allow-outside-private-output", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        assert_final_eval_allowed(
            args.evaluation_slug,
            confirm_final_eval=args.confirm_final_eval,
        )
        if args.max_new_tokens <= 0:
            raise RunSafetyError("--max-new-tokens must be positive")
        if args.execute and not args.model_revision:
            raise RunSafetyError("--execute requires --model-revision")
        if args.resume_from is not None and not args.execute:
            raise RunSafetyError("--resume-from requires --execute")
        safe_outputs = validate_output_root(
            args.outputs_root,
            allow_outside_private_output=args.allow_outside_private_output,
        )
        input_path = validate_private_path(args.input, label="input")
        prompt_template_path = Path(args.prompt_template).expanduser().resolve()
        bundle_path = (
            validate_private_path(args.bundle, label="bundle")
            if args.bundle is not None
            else None
        )
        run_id = experiment_id(
            args.protocol_id,
            args.model_slug,
            args.evaluation_slug,
            args.seed,
            args.replicate,
        )
        config = RunConfig(
            experiment_id=run_id,
            protocol_id=args.protocol_id,
            model_slug=args.model_slug,
            evaluation_slug=args.evaluation_slug,
            seed=args.seed,
            replicate=args.replicate,
        )
        if args.execute:
            is_final = args.evaluation_slug == "nahw-passage"
            if is_final:
                if args.kernel_start_epoch_seconds is None:
                    raise RunSafetyError(
                        "B1/B2 final execution requires wrapper start time"
                    )
                require_final_execution_authorization(
                    confirmation=args.confirmation,
                    approved_protocol_commit=args.approved_protocol_commit,
                    approval_reference=args.approval_reference,
                    model_id=args.model,
                    model_revision=args.model_revision,
                    max_new_tokens=args.max_new_tokens,
                    config=config,
                    input_path=input_path,
                    bundle_path=bundle_path,
                    record_count=511,
                )
                budget = KernelTimeBudget(args.kernel_start_epoch_seconds)
            else:
                if args.resume_from is not None:
                    raise RunSafetyError(
                        "timeout-safe resume is restricted to the final gate"
                    )
                budget = None
            records = load_prompt_records(input_path)
            if is_final and len(records) != 511:
                raise RunSafetyError("B1/B2 frozen final record count mismatch")
            demos = load_protocol_demos(args.protocol_id, bundle_path)
            generator = GemmaGenerator(
                args.model,
                args.model_revision,
                args.max_new_tokens,
                seed=args.seed,
                require_p100=is_final,
            )
            summary = execute_run(
                config,
                records,
                demos,
                generator,
                outputs_root=safe_outputs,
                input_path=input_path,
                prompt_template_path=prompt_template_path,
                bundle_path=bundle_path,
                runtime_metadata=generator.metadata,
                allow_outside_private_output=args.allow_outside_private_output,
                budget=budget,
                resume_from=args.resume_from,
                model_id=args.model,
                model_revision=args.model_revision,
                max_new_tokens=args.max_new_tokens,
                approved_protocol_commit=args.approved_protocol_commit,
            )
            run_dir = safe_outputs / run_id
        else:
            run_dir = prepare_run_directory(safe_outputs, run_id)
            summary = build_summary(
                config,
                input_path=input_path,
                prompt_template_path=prompt_template_path,
                bundle_path=bundle_path,
                run_status="planned",
            )
            _write_summary(run_dir / "summary.json", summary)
            with (run_dir / "run.log").open(
                "w", encoding="utf-8", newline="\n"
            ) as stream:
                stream.write("planned run scaffold created; model inference not executed\n")
    except (RunSafetyError, OSError) as error:
        raise SystemExit(f"ERROR: {error}") from error
    print(
        json.dumps(
            {
                "experiment_id": run_id,
                "run_dir": str(run_dir),
                "run_status": summary["run_status"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
