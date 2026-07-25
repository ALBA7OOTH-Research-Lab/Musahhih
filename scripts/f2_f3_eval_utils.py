#!/usr/bin/env python3
"""Fail-closed identities and paired analysis for matched F2/F3 evaluation."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import subprocess
from typing import Sequence

from scripts.f1_eval_utils import (
    BASE_MODEL_ID,
    BASE_MODEL_REVISION,
    BOOTSTRAP_SAMPLES,
    EXPECTED_BASELINE_PREDICTIONS_SHA256,
    EXPECTED_TEST_RECORDS,
    EXPECTED_TEST_SHA256,
    MAX_NEW_TOKENS,
    SEED,
    TARGET_MODULES,
    EvaluationSafetyError,
    load_and_validate_nahw_records,
    paired_comparison,
    sha256_file,
)


CONFIRMATION = "RUN_F2_F3_MATCHED_NAHW_FINAL_511"
RUN_ID = "F2-F3__gemma3-4b-it__nahw-passage__s3407__r01"
EXPECTED_F1_PREDICTIONS_SHA256 = (
    "8c4d0ca25b48776a08ea02984af6c5c3ec0bc830d2d1a6994e0fb5eef995faa3"
)
APPROVAL_PATTERN = re.compile(
    r"https://github\.com/ALBA7OOTH-Research-Lab/Musahhih/"
    r"issues/96#issuecomment-[1-9][0-9]*"
)


@dataclass(frozen=True)
class ArmSpec:
    arm: str
    checkpoint: str
    adapter_model_sha256: str
    adapter_config_sha256: str
    checkpoint_selection_sha256: str


ARM_SPECS = {
    "F2-P1": ArmSpec(
        arm="F2-P1",
        checkpoint="checkpoint-125",
        adapter_model_sha256=(
            "935fdf02c95189934e40629f877d8692d325ef22895cbaa03fdb7390b0cd7b3e"
        ),
        adapter_config_sha256=(
            "b07ab34155647961ea1de8fbfff0db8e17d00229da01f2b941a15a78499da986"
        ),
        checkpoint_selection_sha256=(
            "39edee5e31d79c791a4ab0b14b7b85b838e28bcc302d9e552f168a03ac870e1b"
        ),
    ),
    "F3-P1": ArmSpec(
        arm="F3-P1",
        checkpoint="checkpoint-250",
        adapter_model_sha256=(
            "95bd333caac28e08b40fcafe7bc033f323188e817d7c16ecbe7745b34c1b44dc"
        ),
        adapter_config_sha256=(
            "917893c00ea8f02f784ce21db4448b774e6a892fede6f484da18606bca884c21"
        ),
        checkpoint_selection_sha256=(
            "b4d1deda9b01b82b07abd2a21e999f92e132604ca0c8463830edd8d43dedfa81"
        ),
    ),
}


def _load_json(path: Path, label: str) -> dict:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EvaluationSafetyError(f"unable to read valid UTF-8 {label}") from error
    if not isinstance(value, dict):
        raise EvaluationSafetyError(f"{label} must be a JSON object")
    return value


def validate_adapter_checkpoint(adapter_path: Path, spec: ArmSpec) -> dict:
    """Verify one selected checkpoint and its immutable adapter bytes."""

    adapter_path = Path(adapter_path).expanduser().resolve()
    if adapter_path.name != spec.checkpoint or not adapter_path.is_dir():
        raise EvaluationSafetyError(
            f"{spec.arm} adapter must be the {spec.checkpoint} directory"
        )
    model_path = adapter_path / "adapter_model.safetensors"
    config_path = adapter_path / "adapter_config.json"
    selection_path = adapter_path.parent / "checkpoint_selection.json"
    expected_hashes = (
        (model_path, spec.adapter_model_sha256, "adapter model"),
        (config_path, spec.adapter_config_sha256, "adapter config"),
        (selection_path, spec.checkpoint_selection_sha256, "checkpoint selection"),
    )
    for path, expected, label in expected_hashes:
        if not path.is_file() or sha256_file(path) != expected:
            raise EvaluationSafetyError(f"{spec.arm} {label} SHA-256 mismatch")

    config = _load_json(config_path, f"{spec.arm} adapter config")
    selection = _load_json(selection_path, f"{spec.arm} checkpoint selection")
    expected_config = {
        "base_model_name_or_path": BASE_MODEL_ID,
        "peft_type": "LORA",
        "r": 16,
        "lora_alpha": 32,
        "lora_dropout": 0.0,
        "bias": "none",
        "inference_mode": True,
    }
    for field, expected in expected_config.items():
        if config.get(field) != expected:
            raise EvaluationSafetyError(f"{spec.arm} adapter config mismatch: {field}")
    if set(config.get("target_modules", [])) != TARGET_MODULES:
        raise EvaluationSafetyError(f"{spec.arm} adapter target_modules mismatch")
    auto_mapping = config.get("auto_mapping")
    if not isinstance(auto_mapping, dict) or auto_mapping.get(
        "base_model_class"
    ) != "Gemma3ForConditionalGeneration":
        raise EvaluationSafetyError(f"{spec.arm} adapter base model class mismatch")
    if selection.get("arm") != spec.arm:
        raise EvaluationSafetyError(f"{spec.arm} checkpoint-selection arm mismatch")
    if selection.get("selected_checkpoint") != spec.checkpoint:
        raise EvaluationSafetyError(f"{spec.arm} selected checkpoint mismatch")
    if len(selection.get("evaluations", [])) != 2:
        raise EvaluationSafetyError(f"{spec.arm} requires two frozen evaluations")
    return {
        "arm": spec.arm,
        "selected_checkpoint": spec.checkpoint,
        "adapter_model_sha256": spec.adapter_model_sha256,
        "adapter_config_sha256": spec.adapter_config_sha256,
        "checkpoint_selection_sha256": spec.checkpoint_selection_sha256,
        "adapter_merged": False,
    }


def load_validated_reference_predictions(
    path: Path,
    *,
    expected_sha256: str,
    label: str,
    expected_records: int = EXPECTED_TEST_RECORDS,
) -> list[dict]:
    """Load an immutable record-level reference prediction artifact."""

    path = Path(path).expanduser().resolve()
    if sha256_file(path) != expected_sha256:
        raise EvaluationSafetyError(f"{label} predictions SHA-256 mismatch")
    try:
        with path.open("r", encoding="utf-8") as stream:
            rows = [json.loads(line) for line in stream if line.strip()]
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EvaluationSafetyError(
            f"unable to read valid UTF-8 {label} predictions"
        ) from error
    if len(rows) != expected_records:
        raise EvaluationSafetyError(f"{label} prediction count mismatch")
    seen: set[str] = set()
    for row in rows:
        record_id = row.get("record_id", row.get("id"))
        if not isinstance(record_id, str) or record_id in seen:
            raise EvaluationSafetyError(f"invalid or duplicate {label} record ID")
        if not isinstance(row.get("exact_match"), bool):
            raise EvaluationSafetyError(f"{label} exact_match must be boolean")
        seen.add(record_id)
    return rows


def require_execution_authorization(
    confirmation: str | None,
    approved_commit: str | None,
    approval_reference: str | None,
    *,
    repository: Path,
) -> None:
    """Require exact issue #96 approval and exact checked-out commit."""

    if confirmation != CONFIRMATION:
        raise EvaluationSafetyError("exact matched final-evaluation confirmation required")
    if not approved_commit or not re.fullmatch(r"[0-9a-f]{40}", approved_commit):
        raise EvaluationSafetyError("approved protocol commit must be lowercase SHA-1")
    if not approval_reference or not APPROVAL_PATTERN.fullmatch(approval_reference):
        raise EvaluationSafetyError("approval must be an issue #96 comment URL")
    try:
        actual = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise EvaluationSafetyError("unable to verify exact protocol commit") from error
    if actual != approved_commit:
        raise EvaluationSafetyError("checkout is not the exact approved protocol commit")


def matched_comparisons(
    *,
    b0_rows: Sequence[dict],
    f1_rows: Sequence[dict],
    f2_rows: Sequence[dict],
    f3_rows: Sequence[dict],
    bootstrap_samples: int = BOOTSTRAP_SAMPLES,
    seed: int = SEED,
) -> dict:
    """Return the preregistered primary and staged secondary comparisons."""

    return {
        "primary_f3_minus_f2": paired_comparison(
            f2_rows, f3_rows, bootstrap_samples=bootstrap_samples, seed=seed
        ),
        "secondary_f2_minus_b0": paired_comparison(
            b0_rows, f2_rows, bootstrap_samples=bootstrap_samples, seed=seed
        ),
        "secondary_f3_minus_b0": paired_comparison(
            b0_rows, f3_rows, bootstrap_samples=bootstrap_samples, seed=seed
        ),
        "secondary_f2_minus_f1": paired_comparison(
            f1_rows, f2_rows, bootstrap_samples=bootstrap_samples, seed=seed
        ),
        "secondary_f3_minus_f1": paired_comparison(
            f1_rows, f3_rows, bootstrap_samples=bootstrap_samples, seed=seed
        ),
    }


__all__ = [
    "ARM_SPECS",
    "BASE_MODEL_ID",
    "BASE_MODEL_REVISION",
    "BOOTSTRAP_SAMPLES",
    "CONFIRMATION",
    "EXPECTED_BASELINE_PREDICTIONS_SHA256",
    "EXPECTED_F1_PREDICTIONS_SHA256",
    "EXPECTED_TEST_RECORDS",
    "EXPECTED_TEST_SHA256",
    "MAX_NEW_TOKENS",
    "RUN_ID",
    "SEED",
    "EvaluationSafetyError",
    "load_and_validate_nahw_records",
    "load_validated_reference_predictions",
    "matched_comparisons",
    "require_execution_authorization",
    "sha256_file",
    "validate_adapter_checkpoint",
]
