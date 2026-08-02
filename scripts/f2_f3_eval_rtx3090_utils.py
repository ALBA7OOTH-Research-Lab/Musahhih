#!/usr/bin/env python3
"""Frozen issue #183 RTX 3090 five-seed evaluation recovery contract."""

from __future__ import annotations

import re

from scripts.f2_f3_nautilus_utils import validate_seed


ISSUE = 183
CONFIRMATION = "RUN_F2_F3_RTX3090_FIVE_SEED_EVAL"
BATCH_SIZE = 16
SAFE_STOP_ELAPSED_SECONDS = 39_600
JOB_DEADLINE_SECONDS = 43_200
NO_PROGRESS_SECONDS = 1_200
GPU_NAME = "NVIDIA GeForce RTX 3090"
GPU_PRODUCT = "NVIDIA-GeForce-RTX-3090"
OUTPUT_ROOT = "/private/evaluations/issue-183"
COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
APPROVAL_PATTERN = re.compile(
    r"https://github\.com/ALBA7OOTH-Research-Lab/Musahhih/"
    r"issues/183#issuecomment-[1-9][0-9]*"
)


class Rtx3090RecoveryError(ValueError):
    """Raised before the issue #183 recovery can cross its frozen gate."""


def validate_activation(
    *, seed: int, approved_commit: str, actual_commit: str,
    approval_reference: str, confirmation: str,
) -> dict:
    validate_seed(seed)
    if (
        not COMMIT_PATTERN.fullmatch(approved_commit)
        or approved_commit != actual_commit
    ):
        raise Rtx3090RecoveryError("approved repository commit mismatch")
    if not APPROVAL_PATTERN.fullmatch(approval_reference):
        raise Rtx3090RecoveryError("approval must be an issue #183 comment URL")
    if confirmation != CONFIRMATION:
        raise Rtx3090RecoveryError("RTX 3090 recovery confirmation mismatch")
    return {
        "stage": "rtx3090-five-seed-evaluation",
        "seed": seed,
        "approved_commit": approved_commit,
        "approval_reference": approval_reference,
        "attempt_id": approval_reference.rsplit("issuecomment-", 1)[-1],
        "fresh_from_record_zero": True,
        "source_prefixes_reused": False,
        "contains_corpus_text": False,
    }


def rtx3090_preflight(torch_module) -> dict:
    """Execute CUDA and verify one exact 24 GB-class RTX 3090."""

    if not torch_module.cuda.is_available():
        raise Rtx3090RecoveryError("CUDA is unavailable")
    if torch_module.cuda.device_count() != 1:
        raise Rtx3090RecoveryError("exactly one visible GPU is required")
    properties = torch_module.cuda.get_device_properties(0)
    if (
        properties.name != GPU_NAME
        or (properties.major, properties.minor) != (8, 6)
        or int(properties.total_memory) < 23 * 1024**3
    ):
        raise Rtx3090RecoveryError(
            f"expected one 24 GB RTX 3090 (8.6), found {properties.name!r} "
            f"({properties.major}.{properties.minor})"
        )
    observed = torch_module.ones(1, device="cuda").sum().item()
    torch_module.cuda.synchronize()
    if observed != 1:
        raise Rtx3090RecoveryError("CUDA operation returned an invalid result")
    return {
        "gpu": properties.name,
        "cuda_capability": "8.6",
        "visible_gpu_count": 1,
        "total_memory_bytes": int(properties.total_memory),
        "cuda_operation_passed": True,
        "contains_corpus_text": False,
    }


__all__ = [
    "APPROVAL_PATTERN", "BATCH_SIZE", "COMMIT_PATTERN", "CONFIRMATION",
    "GPU_NAME", "GPU_PRODUCT", "ISSUE", "JOB_DEADLINE_SECONDS",
    "NO_PROGRESS_SECONDS", "OUTPUT_ROOT", "Rtx3090RecoveryError",
    "SAFE_STOP_ELAPSED_SECONDS", "rtx3090_preflight", "validate_activation",
]
