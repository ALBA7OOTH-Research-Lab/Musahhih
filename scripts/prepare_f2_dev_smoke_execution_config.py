#!/usr/bin/env python3
"""Create the private activation file for the F2-P1 development smoke."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


CONFIG_FILENAME = "f2_dev_smoke_execution_config.json"
CONFIRMATION = "RUN_F2_P1_PRIVATE_DEV_SMOKE_25"
COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
APPROVAL_PATTERN = re.compile(
    r"https://github\.com/ALBA7OOTH-Research-Lab/Musahhih/"
    r"issues/82#issuecomment-[0-9]+"
)


class F2DevSmokeConfigError(ValueError):
    """Raised before an invalid or ambiguous activation file is written."""


def build_execution_config(
    *,
    approved_workflow_commit: str,
    approval_reference: str,
    confirmation: str,
) -> dict[str, str]:
    """Return the strict, text-free activation mapping."""

    if not COMMIT_PATTERN.fullmatch(approved_workflow_commit):
        raise F2DevSmokeConfigError(
            "Approved workflow commit must be 40 lowercase hex characters"
        )
    if not APPROVAL_PATTERN.fullmatch(approval_reference):
        raise F2DevSmokeConfigError(
            "Approval reference must be an issue #82 comment URL"
        )
    if confirmation != CONFIRMATION:
        raise F2DevSmokeConfigError("Private development confirmation mismatch")
    return {
        "stage": "private-dev-smoke",
        "approved_workflow_commit": approved_workflow_commit,
        "approval_reference": approval_reference,
        "confirmation": confirmation,
    }


def write_execution_config(config: dict[str, str], output_path: Path) -> Path:
    """Write once under the exact ignored/private filename."""

    if output_path.name != CONFIG_FILENAME:
        raise F2DevSmokeConfigError(f"Output filename must be {CONFIG_FILENAME}")
    if output_path.exists():
        raise F2DevSmokeConfigError(
            "Execution config already exists; refusing to overwrite it"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-workflow-commit", required=True)
    parser.add_argument("--approval-reference", required=True)
    parser.add_argument("--confirmation", required=True)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = build_execution_config(
        approved_workflow_commit=args.approved_workflow_commit,
        approval_reference=args.approval_reference,
        confirmation=args.confirmation,
    )
    output_path = write_execution_config(config, args.output)
    print(
        json.dumps(
            {
                "output": str(output_path),
                "stage": config["stage"],
                "approved_workflow_commit": config["approved_workflow_commit"],
                "contains_corpus_text": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
