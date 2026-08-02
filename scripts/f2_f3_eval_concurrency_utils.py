#!/usr/bin/env python3
"""Frozen issue #177 identities for concurrent batch-16 evaluation repair."""

from __future__ import annotations

import re

from scripts.f2_f3_eval_repair_utils import (
    SOURCE_ATTEMPT_ID,
    SOURCE_EVALUATION_COMMIT,
    SOURCE_PROGRESS_COUNTS,
    SOURCE_TERMINAL_STATES,
)
from scripts.f2_f3_nautilus_utils import validate_seed


ISSUE = 177
WORKER_COUNT = 5
CONCURRENT_BATCH_SIZE = 16
CANARY_CONFIRMATION = "RUN_F2_F3_BATCH16_CONCURRENCY_CANARY"
CONTINUATION_CONFIRMATION = (
    "CONTINUE_F2_F3_EVAL_CONCURRENT_BATCH16_FROM_ATTEMPT_5144097114"
)
STAGES = ("concurrency-canary", "continuation")
COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
APPROVAL_PATTERN = re.compile(
    r"https://github\.com/ALBA7OOTH-Research-Lab/Musahhih/"
    r"issues/177#issuecomment-[1-9][0-9]*"
)
INCOMPLETE_ARMS = {
    seed: next(arm for arm, count in counts.items() if count < 511)
    for seed, counts in SOURCE_PROGRESS_COUNTS.items()
}


class EvaluationConcurrencyError(ValueError):
    """Raised before an issue #177 execution boundary can be crossed."""


def _attempt_id(reference: str) -> str:
    return reference.rsplit("issuecomment-", 1)[-1]


def validate_concurrency_activation(
    *,
    stage: str,
    seed: int | None,
    approved_commit: str,
    actual_commit: str,
    approval_reference: str,
    confirmation: str,
) -> dict:
    if stage not in STAGES:
        raise EvaluationConcurrencyError(f"stage must be one of {STAGES}")
    if (
        not COMMIT_PATTERN.fullmatch(approved_commit)
        or actual_commit != approved_commit
    ):
        raise EvaluationConcurrencyError("approved repository commit mismatch")
    if not APPROVAL_PATTERN.fullmatch(approval_reference):
        raise EvaluationConcurrencyError("approval must be an issue #177 comment URL")
    expected = {
        "concurrency-canary": CANARY_CONFIRMATION,
        "continuation": CONTINUATION_CONFIRMATION,
    }[stage]
    if confirmation != expected:
        raise EvaluationConcurrencyError("concurrency stage confirmation mismatch")
    if stage == "concurrency-canary":
        if seed is not None:
            raise EvaluationConcurrencyError("concurrency canary must not select a seed")
    else:
        if seed is None:
            raise EvaluationConcurrencyError("continuation requires one frozen seed")
        validate_seed(seed)
    return {
        "stage": stage,
        "seed": seed,
        "approved_commit": approved_commit,
        "approval_reference": approval_reference,
        "attempt_id": _attempt_id(approval_reference),
        "source_attempt_id": SOURCE_ATTEMPT_ID if seed is not None else None,
        "source_commit": SOURCE_EVALUATION_COMMIT if seed is not None else None,
        "contains_corpus_text": False,
    }


__all__ = [
    "APPROVAL_PATTERN",
    "CANARY_CONFIRMATION",
    "COMMIT_PATTERN",
    "CONCURRENT_BATCH_SIZE",
    "CONTINUATION_CONFIRMATION",
    "EvaluationConcurrencyError",
    "INCOMPLETE_ARMS",
    "ISSUE",
    "SOURCE_ATTEMPT_ID",
    "SOURCE_EVALUATION_COMMIT",
    "SOURCE_PROGRESS_COUNTS",
    "SOURCE_TERMINAL_STATES",
    "WORKER_COUNT",
    "validate_concurrency_activation",
]
