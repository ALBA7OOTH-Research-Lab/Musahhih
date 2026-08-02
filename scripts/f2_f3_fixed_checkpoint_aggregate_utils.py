#!/usr/bin/env python3
"""Frozen activation and source identities for issue #196 aggregation."""

from __future__ import annotations

import re


ISSUE = 196
CONFIRMATION = "AGGREGATE_F2_F3_FIXED_CHECKPOINT_RESULTS"
SELECTED_ROOT = "/private/evaluations/issue-183"
SELECTED_ATTEMPT_ID = "5155890101"
SELECTED_COMMIT = "e004e625a00c9c1c6fac7e2dbc0e7bc450fbad17"
UNSELECTED_ROOTS = {
    3407: "/private/evaluations/issue-194",
    3408: "/private/evaluations/issue-192",
    3409: "/private/evaluations/issue-194",
    3410: "/private/evaluations/issue-192",
    3411: "/private/evaluations/issue-192",
}
UNSELECTED_ATTEMPTS = {
    3407: "5158062318",
    3408: "5157509573",
    3409: "5158062318",
    3410: "5157509573",
    3411: "5157509573",
}
UNSELECTED_COMMITS = {
    3407: "3b2a30aa994071d5a51a51f62ee31df6cd13d958",
    3408: "6b77efafd53660d2b98557b93cff983e91dbbf27",
    3409: "3b2a30aa994071d5a51a51f62ee31df6cd13d958",
    3410: "6b77efafd53660d2b98557b93cff983e91dbbf27",
    3411: "6b77efafd53660d2b98557b93cff983e91dbbf27",
}
TRAINING_ROOT = "/private/outputs/issue-155"
OUTPUT_ROOT = "/private/evaluations/issue-196"
COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
APPROVAL_PATTERN = re.compile(
    r"https://github\.com/ALBA7OOTH-Research-Lab/Musahhih/"
    r"issues/196#issuecomment-[1-9][0-9]*"
)


class FixedCheckpointAggregateError(ValueError):
    """Raised before the issue #196 aggregate gate can be crossed."""


def validate_activation(
    *, approved_commit: str, actual_commit: str,
    approval_reference: str, confirmation: str,
) -> dict:
    if (
        not COMMIT_PATTERN.fullmatch(approved_commit)
        or approved_commit != actual_commit
    ):
        raise FixedCheckpointAggregateError("approved repository commit mismatch")
    if not APPROVAL_PATTERN.fullmatch(approval_reference):
        raise FixedCheckpointAggregateError("approval must be an issue #196 comment URL")
    if confirmation != CONFIRMATION:
        raise FixedCheckpointAggregateError("aggregate confirmation mismatch")
    return {
        "stage": "f2-f3-fixed-checkpoint-aggregate",
        "approved_commit": approved_commit,
        "approval_reference": approval_reference,
        "attempt_id": approval_reference.rsplit("issuecomment-", 1)[-1],
        "contains_corpus_text": False,
    }


__all__ = [
    "APPROVAL_PATTERN", "COMMIT_PATTERN", "CONFIRMATION", "ISSUE",
    "OUTPUT_ROOT", "SELECTED_ATTEMPT_ID", "SELECTED_COMMIT", "SELECTED_ROOT",
    "TRAINING_ROOT", "UNSELECTED_ATTEMPTS", "UNSELECTED_COMMITS",
    "UNSELECTED_ROOTS", "FixedCheckpointAggregateError", "validate_activation",
]
