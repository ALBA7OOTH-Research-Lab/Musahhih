"""Frozen, text-safe configuration and gates for the F1-P1 Colab workflow."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


PROTOCOL_ID = "F1-P1"
MODEL_ID = "unsloth/gemma-3-4b-it-unsloth-bnb-4bit"
MODEL_REVISION = "316726ca0bd24aa323bfaf86e8a379ee1176d1fe"
MAX_SEQUENCE_LENGTH = 1024
TRAIN_RECORDS = 2000
SEEDS = (3407, 3408, 3409)
LORA_TARGETS = (
    "q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"
)
MIN_HEADROOM_BYTES = 1024**3
FULL_TRAINING_CONFIRMATION = "RUN_F1_P1_TWO_EPOCH_TRAINING"

TRAINING_CONFIG = {
    "num_train_epochs": 2,
    "per_device_train_batch_size": 1,
    "per_device_eval_batch_size": 1,
    "gradient_accumulation_steps": 16,
    "learning_rate": 2e-4,
    "lr_scheduler_type": "linear",
    "warmup_ratio": 0.03,
    "optim": "adamw_8bit",
    "weight_decay": 0.01,
    "max_grad_norm": 1.0,
    "logging_steps": 10,
    "packing": False,
}


class TrainingGateError(ValueError):
    """Raised before training when a frozen F1-P1 gate is not satisfied."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_private_jsonl(path: Path, expected_split: str, expected_count: int | None) -> dict:
    """Validate private records without returning or printing their text."""
    required = {"record_id", "prompt", "completion", "source", "split"}
    count = 0
    seen = set()
    max_serialized_bytes = 0
    try:
        with path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                row = json.loads(line)
                if not isinstance(row, dict) or set(row) != required:
                    raise TrainingGateError(f"Private record schema mismatch at row {line_number}")
                if row["split"] != expected_split or row["source"] != "QALB-2014-L1":
                    raise TrainingGateError(f"Private record role mismatch at row {line_number}")
                if not isinstance(row["record_id"], str) or row["record_id"] in seen:
                    raise TrainingGateError(f"Duplicate or invalid record ID at row {line_number}")
                if (
                    not isinstance(row["prompt"], list) or len(row["prompt"]) != 1
                    or row["prompt"][0].get("role") != "user"
                    or not isinstance(row["prompt"][0].get("content"), str)
                    or not isinstance(row["completion"], list) or len(row["completion"]) != 1
                    or row["completion"][0].get("role") != "assistant"
                    or not isinstance(row["completion"][0].get("content"), str)
                ):
                    raise TrainingGateError(f"Conversation schema mismatch at row {line_number}")
                seen.add(row["record_id"])
                count += 1
                max_serialized_bytes = max(max_serialized_bytes, len(line.encode("utf-8")))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise TrainingGateError(f"Cannot read private JSONL: {path.name}") from error
    if expected_count is not None and count != expected_count:
        raise TrainingGateError(f"Private record count mismatch: observed={count} expected={expected_count}")
    if count == 0:
        raise TrainingGateError("Private JSONL is empty")
    return {
        "filename": path.name,
        "sha256": sha256_file(path),
        "records": count,
        "max_serialized_bytes": max_serialized_bytes,
        "contains_corpus_text": False,
    }


def memory_gate(total_bytes: int, peak_reserved_bytes: int) -> dict:
    if not all(isinstance(value, int) and value >= 0 for value in (total_bytes, peak_reserved_bytes)):
        raise TrainingGateError("GPU memory values must be non-negative integers")
    headroom = total_bytes - peak_reserved_bytes
    passed = headroom >= MIN_HEADROOM_BYTES
    return {
        "total_bytes": total_bytes,
        "peak_reserved_bytes": peak_reserved_bytes,
        "headroom_bytes": headroom,
        "required_headroom_bytes": MIN_HEADROOM_BYTES,
        "passed": passed,
        "contains_corpus_text": False,
    }


def require_full_training_confirmation(confirmation: str, smoke_summary: dict) -> None:
    if confirmation != FULL_TRAINING_CONFIRMATION:
        raise TrainingGateError("Full F1-P1 training confirmation is missing")
    if not isinstance(smoke_summary, dict) or smoke_summary.get("passed") is not True:
        raise TrainingGateError("A passing one-batch GPU smoke summary is required")
