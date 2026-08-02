#!/usr/bin/env python3
"""Supervise one issue #194 replacement with the existing no-progress guard."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from scripts.f2_f3_fixed_checkpoint_repair_utils import OUTPUT_ROOT, validate_activation
from scripts.run_f2_f3_nautilus_pair import actual_commit
from scripts.supervise_f2_f3_fixed_checkpoint_eval import supervise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--training-root", required=True, type=Path)
    parser.add_argument("--test-input-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--kernel-start-epoch-seconds", required=True, type=float)
    parser.add_argument("--approved-commit", required=True)
    parser.add_argument("--approval-reference", required=True)
    parser.add_argument("--confirmation", required=True)
    args = parser.parse_args()
    activation = validate_activation(
        seed=args.seed,
        approved_commit=args.approved_commit,
        actual_commit=actual_commit(),
        approval_reference=args.approval_reference,
        confirmation=args.confirmation,
    )
    if args.output_root.as_posix() != OUTPUT_ROOT:
        raise RuntimeError("repair output root mismatch")
    attempt_root = args.output_root / f"seed-{args.seed}" / "attempts" / activation["attempt_id"]
    command = [
        sys.executable, "-m", "scripts.run_f2_f3_fixed_checkpoint_repair",
        "--seed", str(args.seed),
        "--training-root", str(args.training_root),
        "--test-input-root", str(args.test_input_root),
        "--output-root", str(args.output_root),
        "--kernel-start-epoch-seconds", str(args.kernel_start_epoch_seconds),
        "--approved-commit", args.approved_commit,
        "--approval-reference", args.approval_reference,
        "--confirmation", args.confirmation,
    ]
    try:
        code = supervise(
            command=command,
            progress_path=attempt_root / "progress.json",
            summary_path=attempt_root / "public_summary.json",
            activation=activation,
        )
    except BaseException as error:
        print(json.dumps({
            "status": "failed",
            "error_type": type(error).__name__,
            "error_message_sha256": hashlib.sha256(
                str(error).encode("utf-8", errors="replace")
            ).hexdigest(),
            "contains_corpus_text": False,
        }, sort_keys=True))
        raise
    print(json.dumps({
        "status": "complete" if code == 0 else "failed",
        "worker_exit_code": code,
        "seed": args.seed,
        "metrics_printed": False,
        "contains_corpus_text": False,
    }, sort_keys=True))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
