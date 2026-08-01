#!/usr/bin/env python3
"""Frozen issue #173 repair identities and activation checks."""

from __future__ import annotations

import re

from scripts.f2_f3_nautilus_utils import SEEDS, approval_attempt_id, validate_seed


ISSUE = 173
SOURCE_ATTEMPT_ID = "5144097114"
SOURCE_EVALUATION_COMMIT = "30290dd3a8bde5054555cc37ac422f3d1512d3ba"
SOURCE_PROGRESS_COUNTS = {
    3407: {"F2-P1": 511, "F3-P1": 237},
    3408: {"F2-P1": 236, "F3-P1": 511},
    3409: {"F2-P1": 511, "F3-P1": 237},
    3410: {"F2-P1": 237, "F3-P1": 511},
    3411: {"F2-P1": 511, "F3-P1": 237},
}
SOURCE_TERMINAL_STATES = {
    3407: "OOMKilled",
    3408: "JobSuspended",
    3409: "OOMKilled",
    3410: "JobSuspended",
    3411: "OOMKilled",
}
CANARY_CONFIRMATION = "RUN_F2_F3_EVAL_REPAIR_UTILIZATION_CANARY"
CONTINUATION_CONFIRMATION = "CONTINUE_F2_F3_EVAL_FROM_ATTEMPT_5144097114"
STAGES = ("utilization-canary", "continuation")
COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
APPROVAL_PATTERN = re.compile(
    r"https://github\.com/ALBA7OOTH-Research-Lab/Musahhih/"
    r"issues/173#issuecomment-[1-9][0-9]*"
)


class EvaluationRepairError(ValueError):
    """Raised before issue #173 can cross a frozen gate."""


def validate_repair_activation(
    *,
    stage: str,
    seed: int | None,
    approved_commit: str,
    actual_commit: str,
    approval_reference: str,
    confirmation: str,
) -> dict:
    if stage not in STAGES:
        raise EvaluationRepairError(f"stage must be one of {STAGES}")
    if (
        not COMMIT_PATTERN.fullmatch(approved_commit)
        or actual_commit != approved_commit
    ):
        raise EvaluationRepairError("approved repository commit mismatch")
    if not APPROVAL_PATTERN.fullmatch(approval_reference):
        raise EvaluationRepairError("approval must be an issue #173 comment URL")
    expected = {
        "utilization-canary": CANARY_CONFIRMATION,
        "continuation": CONTINUATION_CONFIRMATION,
    }[stage]
    if confirmation != expected:
        raise EvaluationRepairError("repair stage confirmation mismatch")
    if stage == "utilization-canary":
        if seed is not None:
            raise EvaluationRepairError("utilization canary must not select a seed")
    else:
        if seed is None:
            raise EvaluationRepairError("continuation requires one frozen seed")
        validate_seed(seed)
    return {
        "stage": stage,
        "seed": seed,
        "approved_commit": approved_commit,
        "approval_reference": approval_reference,
        "attempt_id": approval_attempt_id(approval_reference),
        "source_attempt_id": SOURCE_ATTEMPT_ID if seed is not None else None,
        "source_commit": SOURCE_EVALUATION_COMMIT if seed is not None else None,
        "contains_corpus_text": False,
    }


def validate_interrupted_source_identity(
    *, seed: int, source_attempt_id: str, source_commit: str
) -> dict:
    validate_seed(seed)
    if source_attempt_id != SOURCE_ATTEMPT_ID:
        raise EvaluationRepairError("interrupted source attempt mismatch")
    if source_commit != SOURCE_EVALUATION_COMMIT:
        raise EvaluationRepairError("interrupted source commit mismatch")
    return {
        "seed": seed,
        "source_attempt_id": source_attempt_id,
        "source_commit": source_commit,
        "terminal_state": SOURCE_TERMINAL_STATES[seed],
        "recorded_counts": dict(SOURCE_PROGRESS_COUNTS[seed]),
        "contains_corpus_text": False,
    }


__all__ = [
    "CANARY_CONFIRMATION",
    "CONTINUATION_CONFIRMATION",
    "EvaluationRepairError",
    "SOURCE_ATTEMPT_ID",
    "SOURCE_EVALUATION_COMMIT",
    "SOURCE_PROGRESS_COUNTS",
    "SOURCE_TERMINAL_STATES",
    "validate_interrupted_source_identity",
    "validate_repair_activation",
]
