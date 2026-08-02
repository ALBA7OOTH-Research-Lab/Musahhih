#!/usr/bin/env python3
"""Frozen identities for issue #192 fixed-checkpoint sensitivity evaluation."""

from __future__ import annotations

from pathlib import Path
import re

from scripts.f2_f3_multiseed_eval_utils import TRAINING_COMMIT
from scripts.f2_f3_nautilus_utils import arm_order, approval_attempt_id, validate_seed
from scripts.run_f2_f3_nautilus_pair import validate_completed_arm


ISSUE = 192
CONFIRMATION = "RUN_F2_F3_FIXED_CHECKPOINT_SENSITIVITY"
OUTPUT_ROOT = "/private/evaluations/issue-192"
BATCH_SIZE = 16
SAFE_STOP_ELAPSED_SECONDS = 39_600
JOB_DEADLINE_SECONDS = 43_200
GPU_NAME = "NVIDIA GeForce RTX 3090"
GPU_PRODUCT = "NVIDIA-GeForce-RTX-3090"
COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
APPROVAL_PATTERN = re.compile(
    r"https://github\.com/ALBA7OOTH-Research-Lab/Musahhih/"
    r"issues/192#issuecomment-[1-9][0-9]*"
)


class FixedCheckpointError(ValueError):
    """Raised before the fixed-checkpoint gate can be crossed."""


def validate_activation(
    *, seed: int, approved_commit: str, actual_commit: str,
    approval_reference: str, confirmation: str,
) -> dict:
    validate_seed(seed)
    if (
        not COMMIT_PATTERN.fullmatch(approved_commit)
        or approved_commit != actual_commit
    ):
        raise FixedCheckpointError("approved repository commit mismatch")
    if not APPROVAL_PATTERN.fullmatch(approval_reference):
        raise FixedCheckpointError("approval must be an issue #192 comment URL")
    if confirmation != CONFIRMATION:
        raise FixedCheckpointError("fixed-checkpoint confirmation mismatch")
    return {
        "stage": "fixed-checkpoint-sensitivity-evaluation",
        "seed": seed,
        "approved_commit": approved_commit,
        "approval_reference": approval_reference,
        "attempt_id": approval_attempt_id(approval_reference),
        "contains_corpus_text": False,
    }


def validate_unselected_training_pair(seed_root: Path, seed: int) -> dict[str, dict]:
    """Validate both epochs and return only each arm's unselected checkpoint."""

    validate_seed(seed)
    seed_root = Path(seed_root)
    pair_path = seed_root / "99_pair_complete.json"
    try:
        import json

        pair = json.loads(pair_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        raise FixedCheckpointError("cannot read pair completion") from error
    expected_order = arm_order(seed)
    if (
        not isinstance(pair, dict)
        or pair.get("seed") != seed
        or pair.get("arm_order") != list(expected_order)
        or pair.get("completed_arms") != list(expected_order)
        or pair.get("workflow_commit") != TRAINING_COMMIT
        or pair.get("contains_corpus_text") is not False
        or pair.get("nahw_passage_used") is not False
        or pair.get("qalb_test_used") is not False
    ):
        raise FixedCheckpointError("pair completion contract mismatch")

    result: dict[str, dict] = {}
    expected_checkpoints = {"checkpoint-125", "checkpoint-250"}
    for position, arm in enumerate(expected_order, 1):
        try:
            selection = validate_completed_arm(
                seed_root=seed_root,
                position=position,
                arm=arm,
                seed=seed,
                workflow_commit=TRAINING_COMMIT,
            )
        except RuntimeError as error:
            raise FixedCheckpointError(
                f"{arm} completed-checkpoint validation failed"
            ) from error
        if selection is None:
            raise FixedCheckpointError(f"{arm} completion is missing")
        selected = selection.get("selected_checkpoint")
        identities = selection.get("checkpoints")
        if selected not in expected_checkpoints or not isinstance(identities, list):
            raise FixedCheckpointError(f"{arm} checkpoint contract mismatch")
        by_name = {item.get("checkpoint"): item for item in identities}
        if set(by_name) != expected_checkpoints:
            raise FixedCheckpointError(f"{arm} epoch checkpoint identities mismatch")
        unselected = next(iter(expected_checkpoints - {selected}))
        identity = by_name[unselected]
        result[arm] = {
            "arm": arm,
            "seed": seed,
            "checkpoint": unselected,
            "checkpoint_policy": "unselected_epoch_checkpoint",
            "selected_checkpoint": selected,
            "adapter_path": seed_root / arm.lower() / unselected,
            "adapter_model_bytes": identity["adapter_model_bytes"],
            "adapter_model_sha256": identity["adapter_model_sha256"],
            "adapter_config_sha256": identity["adapter_config_sha256"],
            "training_commit": TRAINING_COMMIT,
            "adapter_merged": False,
            "contains_corpus_text": False,
        }
    return result


__all__ = [
    "APPROVAL_PATTERN", "BATCH_SIZE", "COMMIT_PATTERN", "CONFIRMATION",
    "FixedCheckpointError", "GPU_NAME", "GPU_PRODUCT", "ISSUE",
    "JOB_DEADLINE_SECONDS", "OUTPUT_ROOT", "SAFE_STOP_ELAPSED_SECONDS",
    "validate_activation", "validate_unselected_training_pair",
]
