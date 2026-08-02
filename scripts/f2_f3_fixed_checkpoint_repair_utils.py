#!/usr/bin/env python3
"""Frozen issue #194 activation for two pre-test batch-stability repairs."""

from __future__ import annotations

import re

from scripts.f2_f3_nautilus_utils import approval_attempt_id


ISSUE = 194
FAILED_SEEDS = (3407, 3409)
SOURCE_COMMIT = "6b77efafd53660d2b98557b93cff983e91dbbf27"
SOURCE_ATTEMPT_ID = "5157509573"
SOURCE_JOBS = {
    3407: "musahhih-f2-f3-fixed-s3407-a57509573",
    3409: "musahhih-f2-f3-fixed-s3409-a57509573",
}
CONFIRMATION = "RUN_F2_F3_FIXED_CHECKPOINT_BATCH_STABILITY_REPAIR"
OUTPUT_ROOT = "/private/evaluations/issue-194"
BATCH_SIZE = 16
SAFE_STOP_ELAPSED_SECONDS = 39_600
JOB_DEADLINE_SECONDS = 43_200
GPU_NAME = "NVIDIA GeForce RTX 3090"
GPU_PRODUCT = "NVIDIA-GeForce-RTX-3090"
COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
APPROVAL_PATTERN = re.compile(
    r"https://github\.com/ALBA7OOTH-Research-Lab/Musahhih/"
    r"issues/194#issuecomment-[1-9][0-9]*"
)


class FixedCheckpointRepairError(ValueError):
    """Raised before the issue #194 replacement gate can be crossed."""


def validate_activation(
    *, seed: int, approved_commit: str, actual_commit: str,
    approval_reference: str, confirmation: str,
) -> dict:
    if seed not in FAILED_SEEDS:
        raise FixedCheckpointRepairError("only failed seeds 3407 and 3409 are eligible")
    if (
        not COMMIT_PATTERN.fullmatch(approved_commit)
        or approved_commit != actual_commit
    ):
        raise FixedCheckpointRepairError("approved repository commit mismatch")
    if not APPROVAL_PATTERN.fullmatch(approval_reference):
        raise FixedCheckpointRepairError("approval must be an issue #194 comment URL")
    if confirmation != CONFIRMATION:
        raise FixedCheckpointRepairError("batch-stability repair confirmation mismatch")
    return {
        "stage": "fixed-checkpoint-batch-stability-repair",
        "seed": seed,
        "approved_commit": approved_commit,
        "approval_reference": approval_reference,
        "attempt_id": approval_attempt_id(approval_reference),
        "source_commit": SOURCE_COMMIT,
        "source_attempt_id": SOURCE_ATTEMPT_ID,
        "source_job": SOURCE_JOBS[seed],
        "fresh_from_record_zero": True,
        "source_predictions_reused": False,
        "contains_corpus_text": False,
    }


__all__ = [
    "APPROVAL_PATTERN", "BATCH_SIZE", "COMMIT_PATTERN", "CONFIRMATION",
    "FAILED_SEEDS", "FixedCheckpointRepairError", "GPU_NAME", "GPU_PRODUCT",
    "ISSUE", "JOB_DEADLINE_SECONDS", "OUTPUT_ROOT", "SAFE_STOP_ELAPSED_SECONDS",
    "SOURCE_ATTEMPT_ID", "SOURCE_COMMIT", "SOURCE_JOBS", "validate_activation",
]
