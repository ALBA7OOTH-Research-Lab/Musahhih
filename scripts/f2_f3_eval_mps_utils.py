#!/usr/bin/env python3
"""Frozen issue #179 activation for the NVIDIA MPS batch-16 canary."""

from __future__ import annotations

import re


ISSUE = 179
CANARY_CONFIRMATION = "RUN_F2_F3_BATCH16_MPS_CANARY"
COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
APPROVAL_PATTERN = re.compile(
    r"https://github\.com/ALBA7OOTH-Research-Lab/Musahhih/"
    r"issues/179#issuecomment-[1-9][0-9]*"
)


class EvaluationMpsError(ValueError):
    """Raised before the issue #179 MPS canary can cross its gate."""


def validate_mps_activation(
    *,
    approved_commit: str,
    actual_commit: str,
    approval_reference: str,
    confirmation: str,
) -> dict:
    if (
        not COMMIT_PATTERN.fullmatch(approved_commit)
        or approved_commit != actual_commit
    ):
        raise EvaluationMpsError("approved repository commit mismatch")
    if not APPROVAL_PATTERN.fullmatch(approval_reference):
        raise EvaluationMpsError("approval must be an issue #179 comment URL")
    if confirmation != CANARY_CONFIRMATION:
        raise EvaluationMpsError("MPS canary confirmation mismatch")
    return {
        "stage": "mps-canary",
        "approved_commit": approved_commit,
        "approval_reference": approval_reference,
        "attempt_id": approval_reference.rsplit("issuecomment-", 1)[-1],
        "contains_corpus_text": False,
    }


__all__ = [
    "APPROVAL_PATTERN",
    "CANARY_CONFIRMATION",
    "COMMIT_PATTERN",
    "EvaluationMpsError",
    "ISSUE",
    "validate_mps_activation",
]
