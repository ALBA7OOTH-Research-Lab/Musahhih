#!/usr/bin/env python3
"""Frozen activation contract for the issue #185 aggregate audit."""

from __future__ import annotations

import re


ISSUE = 185
CONFIRMATION = "AGGREGATE_F2_F3_RTX3090_RESULTS"
SOURCE_ATTEMPT_ID = "5155890101"
EVALUATION_COMMIT = "e004e625a00c9c1c6fac7e2dbc0e7bc450fbad17"
EVALUATION_ROOT = "/private/evaluations/issue-183"
OUTPUT_ROOT = "/private/evaluations/issue-185"
COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
APPROVAL_PATTERN = re.compile(
    r"https://github\.com/ALBA7OOTH-Research-Lab/Musahhih/"
    r"issues/185#issuecomment-[1-9][0-9]*"
)


class Rtx3090AggregateError(ValueError):
    """Raised before the issue #185 aggregate can cross its frozen gate."""


def validate_activation(
    *, approved_commit: str, actual_commit: str,
    approval_reference: str, confirmation: str,
) -> dict:
    if (
        not COMMIT_PATTERN.fullmatch(approved_commit)
        or approved_commit != actual_commit
    ):
        raise Rtx3090AggregateError("approved repository commit mismatch")
    if not APPROVAL_PATTERN.fullmatch(approval_reference):
        raise Rtx3090AggregateError("approval must be an issue #185 comment URL")
    if confirmation != CONFIRMATION:
        raise Rtx3090AggregateError("aggregate confirmation mismatch")
    return {
        "stage": "rtx3090-five-seed-aggregate",
        "approved_commit": approved_commit,
        "approval_reference": approval_reference,
        "attempt_id": approval_reference.rsplit("issuecomment-", 1)[-1],
        "source_attempt_id": SOURCE_ATTEMPT_ID,
        "evaluation_commit": EVALUATION_COMMIT,
        "contains_corpus_text": False,
    }


__all__ = [
    "APPROVAL_PATTERN", "COMMIT_PATTERN", "CONFIRMATION", "EVALUATION_COMMIT",
    "EVALUATION_ROOT", "ISSUE", "OUTPUT_ROOT", "Rtx3090AggregateError",
    "SOURCE_ATTEMPT_ID", "validate_activation",
]
