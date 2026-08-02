#!/usr/bin/env python3
"""Frozen identities and authorization for F2/F3 behavioral diagnostics."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from scripts.f1_eval_utils import EvaluationSafetyError, sha256_file
from scripts.f1_safety_eval_utils import (
    BOOTSTRAP_SAMPLES,
    EXPECTED_CAPABILITY_SHA256,
    EXPECTED_OVERCORRECTION_SHA256,
    SEED,
    load_capability_records,
    load_overcorrection_records,
    paired_binary_comparison,
    select_highest_logit,
)
from scripts.f2_f3_eval_utils import ARM_SPECS, validate_adapter_checkpoint


CONFIRMATION = "RUN_MATCHED_F2_F3_SAFETY_DIAGNOSTICS_TIMEOUT_SAFE"
RUN_ID = "F2-F3__gemma3-4b-it__safety-diagnostics__s3407__r01"
SAFE_STOP_ELAPSED_SECONDS = 34_200
SYSTEMS = ("F2-P1", "F3-P1")
STAGES = (
    "F2-P1_overcorrection",
    "F2-P1_capability",
    "F3-P1_overcorrection",
    "F3-P1_capability",
)
EXPECTED_STAGE_RECORDS = {
    "F2-P1_overcorrection": 154,
    "F2-P1_capability": 1_000,
    "F3-P1_overcorrection": 154,
    "F3-P1_capability": 1_000,
}
REFERENCE_PREDICTION_SHA256 = {
    "B0_overcorrection": "81fc3910d8012272d191389ed3547c6e9ed0d234beb39f2fd7ecb9db4d6ce6fd",
    "F1-P1_overcorrection": "5ceb4fe380e9c957463f9521490a88381ae556709b48d82ee1ad761f13dac600",
    "B0_capability": "95bd39db97d269b706b303551a332710d4c94e6e2c5f3683329118feb046a34a",
    "F1-P1_capability": "222deeb7983f31b3cd8d8da400b724beeaf3c74b44db14256310da15bc3b93b0",
}
APPROVAL_PATTERN = re.compile(
    r"https://github\.com/ALBA7OOTH-Research-Lab/Musahhih/"
    r"issues/200#issuecomment-[1-9][0-9]*"
)


def require_execution_authorization(
    confirmation: str | None,
    approved_commit: str | None,
    approval_reference: str | None,
    *,
    repository: Path,
) -> None:
    """Require an exact issue-#200 GO and exact checked-out commit."""

    if confirmation != CONFIRMATION:
        raise EvaluationSafetyError("exact F2/F3 diagnostic confirmation required")
    if not approved_commit or not re.fullmatch(r"[0-9a-f]{40}", approved_commit):
        raise EvaluationSafetyError("approved protocol commit must be lowercase SHA-1")
    if not approval_reference or not APPROVAL_PATTERN.fullmatch(approval_reference):
        raise EvaluationSafetyError("approval must be an issue #200 comment URL")
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


__all__ = [
    "APPROVAL_PATTERN",
    "ARM_SPECS",
    "BOOTSTRAP_SAMPLES",
    "CONFIRMATION",
    "EXPECTED_CAPABILITY_SHA256",
    "EXPECTED_OVERCORRECTION_SHA256",
    "EXPECTED_STAGE_RECORDS",
    "RUN_ID",
    "REFERENCE_PREDICTION_SHA256",
    "SAFE_STOP_ELAPSED_SECONDS",
    "SEED",
    "STAGES",
    "SYSTEMS",
    "EvaluationSafetyError",
    "load_capability_records",
    "load_overcorrection_records",
    "paired_binary_comparison",
    "require_execution_authorization",
    "select_highest_logit",
    "sha256_file",
    "validate_adapter_checkpoint",
]
