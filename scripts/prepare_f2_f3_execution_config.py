#!/usr/bin/env python3
"""Create a text-free private activation file for the guarded F2/F3 notebook."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # Support direct `python scripts/...py` execution.
    sys.path.insert(0, str(ROOT))

from scripts.f2_f3_training_utils import (  # noqa: E402
    FULL_TRAINING_CONFIRMATION,
    GPU_SMOKE_CONFIRMATION,
    validate_arm,
)


CONFIG_FILENAME = "f2_f3_execution_config.json"
STAGES = ("gpu-smoke", "full-training")
ISSUE_COMMENT_PATTERN = re.compile(
    r"https://github\.com/ALBA7OOTH-Research-Lab/Musahhih/"
    r"issues/69#issuecomment-[0-9]+"
)
COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")


class ExecutionConfigError(ValueError):
    """Raised before writing an invalid or ambiguous execution configuration."""


def build_execution_config(
    *,
    arm: str,
    stage: str,
    approved_workflow_commit: str,
    approval_reference: str,
    confirmation: str,
    prior_smoke_summary_path: str = "",
) -> dict[str, str]:
    """Return one strictly validated, corpus-text-free activation mapping."""

    validate_arm(arm)
    if stage not in STAGES:
        raise ExecutionConfigError(f"Stage must be one of {STAGES}")
    if not COMMIT_PATTERN.fullmatch(approved_workflow_commit):
        raise ExecutionConfigError("Approved workflow commit must be 40 lowercase hex characters")
    if not ISSUE_COMMENT_PATTERN.fullmatch(approval_reference):
        raise ExecutionConfigError("Approval reference must be an issue #69 comment URL")

    expected_confirmation = (
        GPU_SMOKE_CONFIRMATION
        if stage == "gpu-smoke"
        else FULL_TRAINING_CONFIRMATION[arm]
    )
    if confirmation != expected_confirmation:
        raise ExecutionConfigError("Confirmation does not match the selected arm and stage")
    if stage == "gpu-smoke" and prior_smoke_summary_path:
        raise ExecutionConfigError("A new smoke must not load a prior smoke summary")
    if stage == "full-training" and not prior_smoke_summary_path:
        raise ExecutionConfigError("Full training requires a private prior smoke-summary path")

    return {
        "arm": arm,
        "stage": stage,
        "approved_workflow_commit": approved_workflow_commit,
        "approval_reference": approval_reference,
        "confirmation": confirmation,
        "prior_smoke_summary_path": prior_smoke_summary_path,
    }


def write_execution_config(config: dict[str, str], output_path: Path) -> Path:
    """Write a new ignored/private config without replacing an existing artifact."""

    if output_path.name != CONFIG_FILENAME:
        raise ExecutionConfigError(f"Output filename must be {CONFIG_FILENAME}")
    if output_path.exists():
        raise ExecutionConfigError("Execution config already exists; refusing to overwrite it")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", required=True, choices=("F2-P1", "F3-P1"))
    parser.add_argument("--stage", required=True, choices=STAGES)
    parser.add_argument("--approved-workflow-commit", required=True)
    parser.add_argument("--approval-reference", required=True)
    parser.add_argument("--confirmation", required=True)
    parser.add_argument("--prior-smoke-summary-path", default="")
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = build_execution_config(
        arm=args.arm,
        stage=args.stage,
        approved_workflow_commit=args.approved_workflow_commit,
        approval_reference=args.approval_reference,
        confirmation=args.confirmation,
        prior_smoke_summary_path=args.prior_smoke_summary_path,
    )
    output_path = write_execution_config(config, args.output)
    print(
        json.dumps(
            {
                "output": str(output_path),
                "arm": config["arm"],
                "stage": config["stage"],
                "approved_workflow_commit": config["approved_workflow_commit"],
                "contains_corpus_text": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
