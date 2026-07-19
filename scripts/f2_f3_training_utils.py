"""Frozen, text-safe configuration and execution gates for F2-P1/F3-P1."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.f1_training_utils import (
    LORA_TARGETS,
    MAX_SEQUENCE_LENGTH,
    MIN_HEADROOM_BYTES,
    MODEL_ID,
    MODEL_REVISION,
    TRAINING_CONFIG,
    memory_gate,
)


ARMS = ("F2-P1", "F3-P1")
TRAIN_RECORDS = 2000
COMMON_DEV_RECORDS = 975
SEED = 3407
EXPECTED_RECORD_SHA256 = {
    "F2-P1": "bbc48dcf78ddff1830661ad749fcc8f9fbfce8206f4f09cd9f4d6501823201d2",
    "F3-P1": "d16decebe559e9a25da41ef59f63ca95e339972e22b9659dfc763e071fbc1546",
    "development": "adfdeb0c2e5730357226ce4e5156c300679629142ea0576d32dea9ac3050a950",
}
GPU_SMOKE_CONFIRMATION = "RUN_F2_F3_LONGEST_RECORD_SMOKE"
FULL_TRAINING_CONFIRMATION = {
    "F2-P1": "RUN_F2_P1_TWO_EPOCH_TRAINING",
    "F3-P1": "RUN_F3_P1_TWO_EPOCH_TRAINING",
}


class F2F3TrainingGateError(ValueError):
    """Raised before model execution when a frozen workflow gate fails."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_arm(arm: str) -> str:
    if arm not in ARMS:
        raise F2F3TrainingGateError(f"Arm must be one of {ARMS}")
    return arm


def validate_private_records(path: Path, role: str) -> dict:
    if role not in (*ARMS, "development"):
        raise F2F3TrainingGateError("Unknown private record role")
    expected_hash = EXPECTED_RECORD_SHA256[role]
    if sha256_file(path) != expected_hash:
        raise F2F3TrainingGateError("Private record checksum mismatch")
    expected_count = COMMON_DEV_RECORDS if role == "development" else TRAIN_RECORDS
    expected_split = "development" if role == "development" else "train"
    allowed_sources = (
        {"QALB-2014-L1"}
        if role == "development"
        else {"Tibyan-corpus"}
        if role == "F2-P1"
        else {"QALB-2014-L1", "Tibyan-corpus"}
    )
    counts = {source: 0 for source in sorted(allowed_sources)}
    seen = set()
    try:
        with path.open(encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                row = json.loads(line)
                if set(row) != {
                    "record_id",
                    "prompt",
                    "completion",
                    "source",
                    "split",
                }:
                    raise F2F3TrainingGateError(
                        f"Private schema mismatch at row {line_number}"
                    )
                if (
                    row["split"] != expected_split
                    or row["source"] not in allowed_sources
                    or not isinstance(row["record_id"], str)
                    or row["record_id"] in seen
                    or not isinstance(row["prompt"], list)
                    or len(row["prompt"]) != 1
                    or row["prompt"][0].get("role") != "user"
                    or not isinstance(row["prompt"][0].get("content"), str)
                    or not isinstance(row["completion"], list)
                    or len(row["completion"]) != 1
                    or row["completion"][0].get("role") != "assistant"
                    or not isinstance(row["completion"][0].get("content"), str)
                ):
                    raise F2F3TrainingGateError(
                        f"Private role mismatch at row {line_number}"
                    )
                seen.add(row["record_id"])
                counts[row["source"]] += 1
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise F2F3TrainingGateError(
            f"Cannot read private records: {path.name}"
        ) from error
    if len(seen) != expected_count:
        raise F2F3TrainingGateError("Private record count mismatch")
    expected_sources = (
        {"Tibyan-corpus": TRAIN_RECORDS}
        if role == "F2-P1"
        else {
            "QALB-2014-L1": TRAIN_RECORDS // 2,
            "Tibyan-corpus": TRAIN_RECORDS // 2,
        }
        if role == "F3-P1"
        else {"QALB-2014-L1": COMMON_DEV_RECORDS}
    )
    if counts != expected_sources:
        raise F2F3TrainingGateError("Private provenance count mismatch")
    return {
        "filename": path.name,
        "sha256": expected_hash,
        "records": expected_count,
        "source_counts": counts,
        "contains_corpus_text": False,
    }


def require_execution_approval(
    approved_commit: str,
    actual_commit: str,
    approval_reference: str,
) -> None:
    if (
        not isinstance(approved_commit, str)
        or len(approved_commit) != 40
        or approved_commit != actual_commit
    ):
        raise F2F3TrainingGateError("Approved workflow commit mismatch")
    if not isinstance(approval_reference, str) or not approval_reference.startswith(
        "https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/69#"
    ):
        raise F2F3TrainingGateError("Workflow execution approval reference is missing")


def require_smoke_confirmation(
    confirmation: str,
    approved_commit: str,
    actual_commit: str,
    approval_reference: str,
) -> None:
    if confirmation != GPU_SMOKE_CONFIRMATION:
        raise F2F3TrainingGateError("GPU smoke confirmation is missing")
    require_execution_approval(
        approved_commit, actual_commit, approval_reference
    )


def require_full_training_confirmation(
    arm: str,
    confirmation: str,
    smoke_summary: dict,
    approved_commit: str,
    actual_commit: str,
    approval_reference: str,
) -> None:
    validate_arm(arm)
    if confirmation != FULL_TRAINING_CONFIRMATION[arm]:
        raise F2F3TrainingGateError("Full-training confirmation is missing")
    if not isinstance(smoke_summary, dict) or smoke_summary.get("passed") is not True:
        raise F2F3TrainingGateError("A passing arm-specific GPU smoke is required")
    if smoke_summary.get("arm") != arm:
        raise F2F3TrainingGateError("GPU smoke arm mismatch")
    if smoke_summary.get("workflow_commit") != actual_commit:
        raise F2F3TrainingGateError("GPU smoke workflow commit mismatch")
    require_execution_approval(
        approved_commit, actual_commit, approval_reference
    )


def run_id(arm: str, stage: str) -> str:
    validate_arm(arm)
    if stage not in {"smoke", "training"}:
        raise F2F3TrainingGateError("Unknown workflow stage")
    slug = "tibyan" if arm == "F2-P1" else "qalb-tibyan-50-50"
    suffix = "smoke" if stage == "smoke" else "train"
    return f"{arm}__gemma3-4b-it__{slug}__s{SEED}__r01__{suffix}"


__all__ = [
    "ARMS",
    "COMMON_DEV_RECORDS",
    "EXPECTED_RECORD_SHA256",
    "F2F3TrainingGateError",
    "FULL_TRAINING_CONFIRMATION",
    "GPU_SMOKE_CONFIRMATION",
    "LORA_TARGETS",
    "MAX_SEQUENCE_LENGTH",
    "MIN_HEADROOM_BYTES",
    "MODEL_ID",
    "MODEL_REVISION",
    "SEED",
    "TRAINING_CONFIG",
    "TRAIN_RECORDS",
    "memory_gate",
    "require_full_training_confirmation",
    "require_execution_approval",
    "require_smoke_confirmation",
    "run_id",
    "validate_arm",
    "validate_private_records",
]
