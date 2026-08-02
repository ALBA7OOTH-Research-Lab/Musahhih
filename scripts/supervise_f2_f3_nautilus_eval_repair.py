#!/usr/bin/env python3
"""Supervise one issue #175 continuation worker outside its inference call."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from scripts.f2_f3_eval_repair_utils import (
    CONTINUATION_CONFIRMATION,
    SOURCE_ATTEMPT_ID,
    SOURCE_EVALUATION_COMMIT,
    validate_repair_activation,
)
from scripts.run_f2_f3_final_eval import _write_json_atomic
from scripts.run_f2_f3_nautilus_multiseed_eval import (
    REPAIR_BATCH_SIZE,
    _require_private_absolute_path,
)
from scripts.run_f2_f3_nautilus_pair import actual_commit


NO_PROGRESS_TIMEOUT_SECONDS = 900
WORKER_WALLCLOCK_SECONDS = 21_600
MEMORY_HIGH_WATER_FRACTION = 0.85
POLL_SECONDS = 5


class EvaluationSupervisorError(RuntimeError):
    """Raised when a worker cannot be supervised without risking private state."""


def validate_canary_summary(root: Path, approved_commit: str) -> dict:
    try:
        summary = json.loads(
            (Path(root) / "public_summary.json").read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EvaluationSupervisorError("invalid repair canary summary") from error
    if (
        summary.get("status") != "complete"
        or summary.get("approved_commit") != approved_commit
        or summary.get("single_batch_equivalent") is not True
        or summary.get("batch_size") != REPAIR_BATCH_SIZE
        or summary.get("synthetic_generations") != 1024
        or summary.get("durability_probe_rows") != 1024
        or summary.get("per_row_fsync") is not True
        or not isinstance(summary.get("mean_gpu_utilization_percent"), (int, float))
        or summary["mean_gpu_utilization_percent"] < 40
        or not isinstance(summary.get("peak_memory_fraction"), (int, float))
        or summary["peak_memory_fraction"] >= 0.80
        or summary.get("nahw_passage_used") is not False
        or summary.get("metric_computed") is not False
        or summary.get("contains_corpus_text") is not False
    ):
        raise EvaluationSupervisorError("repair canary contract mismatch")
    return summary


def cgroup_memory() -> tuple[int, int] | None:
    candidates = (
        (Path("/sys/fs/cgroup/memory.current"), Path("/sys/fs/cgroup/memory.max")),
        (
            Path("/sys/fs/cgroup/memory/memory.usage_in_bytes"),
            Path("/sys/fs/cgroup/memory/memory.limit_in_bytes"),
        ),
    )
    for current_path, maximum_path in candidates:
        if not current_path.is_file() or not maximum_path.is_file():
            continue
        try:
            current = int(current_path.read_text(encoding="ascii").strip())
            maximum_text = maximum_path.read_text(encoding="ascii").strip()
            if maximum_text == "max":
                return None
            maximum = int(maximum_text)
        except (OSError, UnicodeError, ValueError):
            continue
        if current >= 0 and maximum > 0:
            return current, maximum
    return None


def _progress_count(progress_path: Path) -> tuple[int, dict] | None:
    try:
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EvaluationSupervisorError("invalid corpus-free worker progress") from error
    if progress.get("contains_corpus_text") is not False:
        raise EvaluationSupervisorError("worker progress privacy marker mismatch")
    counts = progress.get("completed_records")
    if not isinstance(counts, dict) or any(
        not isinstance(counts.get(arm), int) for arm in ("F2-P1", "F3-P1")
    ):
        raise EvaluationSupervisorError("worker progress counts are invalid")
    return sum(counts.values()), progress


def _stop_worker(process: subprocess.Popen) -> None:
    process.terminate()
    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=30)


def _write_guard_summary(
    *, attempt_root: Path, seed: int, activation: dict, reason: str, progress: dict | None
) -> dict:
    attempt_root.mkdir(parents=True, exist_ok=True)
    summary_path = attempt_root / "public_summary.json"
    if summary_path.exists():
        return json.loads(summary_path.read_text(encoding="utf-8"))
    completed = (
        progress.get("completed_records", {"F2-P1": 0, "F3-P1": 0})
        if progress
        else {"F2-P1": 0, "F3-P1": 0}
    )
    summary = {
        "schema_version": 1,
        "run_status": "incomplete_resource_guard",
        "guard_reason": reason,
        "seed": seed,
        "approved_commit": activation["approved_commit"],
        "attempt_id": activation["attempt_id"],
        "resume_source": activation["source_attempt_id"],
        "completed_records": completed,
        "metrics_reported": False,
        "resume_requires_fresh_authorization": True,
        "automatic_retry": False,
        "contains_corpus_text": False,
    }
    _write_json_atomic(summary_path, summary)
    return summary


def supervise(
    *,
    command: list[str],
    attempt_root: Path,
    seed: int,
    activation: dict,
    now=time.monotonic,
    sleep=time.sleep,
    memory_reader=cgroup_memory,
    popen=subprocess.Popen,
) -> dict:
    started = now()
    last_progress = started
    last_count: int | None = None
    latest_progress: dict | None = None
    process = popen(command)
    guard_reason = None
    while process.poll() is None:
        observed = _progress_count(attempt_root / "progress.json")
        if observed is not None:
            count, latest_progress = observed
            if count != last_count:
                last_count = count
                last_progress = now()
        memory = memory_reader()
        if memory is not None and memory[0] / memory[1] >= MEMORY_HIGH_WATER_FRACTION:
            guard_reason = "memory_high_water"
        elif now() - last_progress >= NO_PROGRESS_TIMEOUT_SECONDS:
            guard_reason = "no_progress_timeout"
        elif now() - started >= WORKER_WALLCLOCK_SECONDS:
            guard_reason = "worker_wallclock"
        if guard_reason:
            _stop_worker(process)
            summary = _write_guard_summary(
                attempt_root=attempt_root,
                seed=seed,
                activation=activation,
                reason=guard_reason,
                progress=latest_progress,
            )
            return {
                "run_status": summary["run_status"],
                "guard_reason": guard_reason,
                "seed": seed,
                "completed_records": summary["completed_records"],
                "metrics_printed": False,
                "contains_corpus_text": False,
            }
        sleep(POLL_SECONDS)
    exit_code = process.wait()
    if exit_code != 0:
        summary = _write_guard_summary(
            attempt_root=attempt_root,
            seed=seed,
            activation=activation,
            reason="worker_nonzero_exit",
            progress=latest_progress,
        )
        return {
            "run_status": summary["run_status"],
            "guard_reason": "worker_nonzero_exit",
            "seed": seed,
            "completed_records": summary["completed_records"],
            "metrics_printed": False,
            "contains_corpus_text": False,
        }
    return {
        "run_status": "complete",
        "seed": seed,
        "metrics_printed": False,
        "contains_corpus_text": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--training-root", required=True, type=Path)
    parser.add_argument("--test-input-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--canary-root", required=True, type=Path)
    parser.add_argument("--source-attempt-id", default=SOURCE_ATTEMPT_ID)
    parser.add_argument("--source-commit", default=SOURCE_EVALUATION_COMMIT)
    parser.add_argument("--approved-commit", required=True)
    parser.add_argument("--approval-reference", required=True)
    parser.add_argument("--confirmation", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    activation = validate_repair_activation(
        stage="continuation",
        seed=args.seed,
        approved_commit=args.approved_commit,
        actual_commit=actual_commit(),
        approval_reference=args.approval_reference,
        confirmation=args.confirmation,
    )
    activation["source_attempt_id"] = args.source_attempt_id
    activation["source_commit"] = args.source_commit
    training_root = _require_private_absolute_path(args.training_root, "training root")
    test_root = _require_private_absolute_path(args.test_input_root, "test input root")
    output_root = _require_private_absolute_path(args.output_root, "output root")
    canary_root = _require_private_absolute_path(args.canary_root, "canary root")
    validate_canary_summary(canary_root, args.approved_commit)
    resume_root = (
        output_root
        / f"seed-{args.seed}"
        / "attempts"
        / args.source_attempt_id
    )
    attempt_root = (
        output_root
        / f"seed-{args.seed}"
        / "attempts"
        / activation["attempt_id"]
    )
    command = [
        sys.executable,
        "-m",
        "scripts.run_f2_f3_nautilus_multiseed_eval",
        "--seed",
        str(args.seed),
        "--training-root",
        str(training_root),
        "--test-input-root",
        str(test_root),
        "--output-root",
        str(output_root),
        "--resume-root",
        str(resume_root),
        "--kernel-start-epoch-seconds",
        str(time.time()),
        "--approved-commit",
        args.approved_commit,
        "--approval-reference",
        args.approval_reference,
        "--confirmation",
        CONTINUATION_CONFIRMATION,
        "--repair-continuation",
        "--resume-source-attempt-id",
        args.source_attempt_id,
        "--resume-source-commit",
        args.source_commit,
        "--batch-size",
        str(REPAIR_BATCH_SIZE),
    ]
    result = supervise(
        command=command,
        attempt_root=attempt_root,
        seed=args.seed,
        activation=activation,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["run_status"] != "complete":
        raise SystemExit(75)


if __name__ == "__main__":
    main()
