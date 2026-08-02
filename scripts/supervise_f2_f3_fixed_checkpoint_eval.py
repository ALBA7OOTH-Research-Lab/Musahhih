#!/usr/bin/env python3
"""Supervise one issue #192 seed with a durable no-progress guard."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from scripts.f2_f3_fixed_checkpoint_utils import (
    OUTPUT_ROOT,
    validate_activation,
)
from scripts.run_f2_f3_final_eval import _write_json_atomic
from scripts.run_f2_f3_nautilus_pair import actual_commit


NO_PROGRESS_SECONDS = 1_200
POLL_SECONDS = 10


def _progress_count(path: Path) -> int | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        values = [payload["completed_records"][arm] for arm in ("F2-P1", "F3-P1")]
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError):
        return None
    if not all(isinstance(value, int) and 0 <= value <= 511 for value in values):
        return None
    return sum(values)


def _stop(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=30)


def supervise(
    *, command: list[str], progress_path: Path, summary_path: Path,
    activation: dict, popen_factory=subprocess.Popen,
    now=time.monotonic, sleep=time.sleep,
) -> int:
    process = popen_factory(command)
    started = now()
    last_progress = started
    last_count: int | None = None
    while process.poll() is None:
        observed = _progress_count(progress_path)
        if observed is not None and observed != last_count:
            last_count = observed
            last_progress = now()
        if now() - last_progress >= NO_PROGRESS_SECONDS:
            _stop(process)
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            if not summary_path.exists():
                _write_json_atomic(summary_path, {
                    "schema_version": 1,
                    "run_status": "incomplete_resource_guard",
                    "guard_reason": "no_progress_timeout",
                    "seed": activation["seed"],
                    "approved_commit": activation["approved_commit"],
                    "attempt_id": activation["attempt_id"],
                    "completed_records_total": last_count,
                    "metrics_reported": False,
                    "resume_requires_fresh_authorization": True,
                    "automatic_retry": False,
                    "contains_corpus_text": False,
                })
            return 91
        sleep(POLL_SECONDS)
    return process.wait()


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
        raise RuntimeError("fixed-checkpoint output root mismatch")
    attempt_root = args.output_root / f"seed-{args.seed}" / "attempts" / activation["attempt_id"]
    command = [
        sys.executable, "-m", "scripts.run_f2_f3_fixed_checkpoint_eval",
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
