"""Fail-closed configuration helpers for the F2/F3 Nautilus replication."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

from scripts.f2_f3_training_utils import APPROVAL_REFERENCE_PATTERN, ARMS


SEEDS = (3407, 3408, 3409, 3410, 3411)
STAGES = ("a100-preflight", "paired-training")
PAIR_CONFIRMATION = "RUN_F2_F3_NAUTILUS_FIVE_SEED_TRAINING"
PREFLIGHT_CONFIRMATION = "RUN_F2_F3_NAUTILUS_A100_PREFLIGHT"
COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
NAMESPACE = "aiea-interns"
PVC_NAME = "musahhih-f2-f3-replication"
INPUT_FILENAMES = (
    "f2_train_records.jsonl",
    "f3_train_records.jsonl",
    "common_dev_records.jsonl",
)


class NautilusReplicationError(ValueError):
    """Raised before cluster execution when the replication contract fails."""


def arm_order(seed: int) -> tuple[str, str]:
    """Balance which arm runs first while keeping each seed deterministic."""
    validate_seed(seed)
    return ARMS if (seed - SEEDS[0]) % 2 == 0 else tuple(reversed(ARMS))


def validate_seed(seed: int) -> int:
    if seed not in SEEDS:
        raise NautilusReplicationError(f"Seed must be one of {SEEDS}")
    return seed


def validate_activation(
    *,
    stage: str,
    seed: int | None,
    approved_commit: str,
    actual_commit: str,
    approval_reference: str,
    confirmation: str,
) -> dict:
    if stage not in STAGES:
        raise NautilusReplicationError(f"Stage must be one of {STAGES}")
    if (
        not COMMIT_PATTERN.fullmatch(approved_commit)
        or approved_commit != actual_commit
    ):
        raise NautilusReplicationError("Approved repository commit mismatch")
    if not APPROVAL_REFERENCE_PATTERN.fullmatch(approval_reference):
        raise NautilusReplicationError(
            "Approval reference must be a Musahhih issue-comment URL"
        )
    expected = (
        PREFLIGHT_CONFIRMATION if stage == "a100-preflight" else PAIR_CONFIRMATION
    )
    if confirmation != expected:
        raise NautilusReplicationError("Stage confirmation mismatch")
    if stage == "a100-preflight":
        if seed is not None:
            raise NautilusReplicationError("A100 preflight must not select a seed")
        order = None
    else:
        if seed is None:
            raise NautilusReplicationError("Paired training requires one seed")
        validate_seed(seed)
        order = list(arm_order(seed))
    return {
        "stage": stage,
        "seed": seed,
        "arm_order": order,
        "approved_commit": approved_commit,
        "approval_reference": approval_reference,
        "contains_corpus_text": False,
    }


def atomic_write_json(path: Path, payload: dict) -> None:
    """Write a durable JSON state file without exposing partial content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise NautilusReplicationError(f"Refusing to overwrite {path.name}")
    handle, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
        if os.name != "nt":
            descriptor = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
    except Exception:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def a100_preflight(torch_module) -> dict:
    """Execute CUDA before any private path is opened."""
    if not torch_module.cuda.is_available():
        raise NautilusReplicationError("CUDA is unavailable")
    if torch_module.cuda.device_count() != 1:
        raise NautilusReplicationError("Exactly one visible GPU is required")
    properties = torch_module.cuda.get_device_properties(0)
    if "A100" not in properties.name or (properties.major, properties.minor) != (
        8,
        0,
    ):
        raise NautilusReplicationError(
            f"Expected one NVIDIA A100 (8.0), found {properties.name!r} "
            f"({properties.major}.{properties.minor})"
        )
    observed = torch_module.ones(1, device="cuda").sum().item()
    torch_module.cuda.synchronize()
    if observed != 1:
        raise NautilusReplicationError("CUDA operation returned an invalid result")
    return {
        "gpu": properties.name,
        "cuda_capability": f"{properties.major}.{properties.minor}",
        "visible_gpu_count": 1,
        "total_memory_bytes": int(properties.total_memory),
        "cuda_operation_passed": True,
        "contains_corpus_text": False,
    }


__all__ = [
    "INPUT_FILENAMES",
    "NAMESPACE",
    "NautilusReplicationError",
    "PAIR_CONFIRMATION",
    "PREFLIGHT_CONFIRMATION",
    "PVC_NAME",
    "SEEDS",
    "STAGES",
    "a100_preflight",
    "arm_order",
    "atomic_write_json",
    "validate_activation",
    "validate_seed",
]
