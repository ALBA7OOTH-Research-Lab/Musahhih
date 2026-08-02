#!/usr/bin/env python3
"""Supervise the five issue #177 batch-16 continuation workers together."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time

from scripts.f2_f3_eval_concurrency_utils import (
    CONCURRENT_BATCH_SIZE,
    CONTINUATION_CONFIRMATION,
    SOURCE_ATTEMPT_ID,
    SOURCE_EVALUATION_COMMIT,
    SOURCE_PROGRESS_COUNTS,
    WORKER_COUNT,
    validate_concurrency_activation,
)
from scripts.f2_f3_nautilus_utils import SEEDS
from scripts.run_f2_f3_final_eval import _write_json_atomic
from scripts.run_f2_f3_nautilus_multiseed_eval import _require_private_absolute_path
from scripts.run_f2_f3_nautilus_pair import actual_commit
from scripts.supervise_f2_f3_nautilus_eval_repair import (
    _progress_count,
    _stop_worker,
    _write_guard_summary,
    cgroup_memory,
)


NO_PROGRESS_TIMEOUT_SECONDS = 900
WALLCLOCK_SECONDS = 21_600
MEMORY_HIGH_WATER_FRACTION = 0.85
POLL_SECONDS = 5


class ConcurrencySupervisorError(RuntimeError):
    """Raised when the five-worker continuation cannot safely proceed."""


def validate_concurrency_canary(root: Path, approved_commit: str) -> dict:
    try:
        summary = json.loads(
            (Path(root) / "public_summary.json").read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ConcurrencySupervisorError("invalid concurrency canary summary") from error
    if (
        summary.get("status") != "complete"
        or summary.get("approved_commit") != approved_commit
        or summary.get("worker_count") != WORKER_COUNT
        or summary.get("batch_size") != CONCURRENT_BATCH_SIZE
        or summary.get("concurrent_worker_outputs_equivalent") is not True
        or summary.get("per_row_fsync") is not True
        or not isinstance(summary.get("mean_gpu_utilization_percent"), (int, float))
        or summary["mean_gpu_utilization_percent"] < 40
        or not isinstance(summary.get("peak_gpu_memory_fraction"), (int, float))
        or summary["peak_gpu_memory_fraction"] >= 0.85
        or not isinstance(summary.get("peak_host_memory_fraction"), (int, float))
        or summary["peak_host_memory_fraction"] >= 0.80
        or summary.get("nahw_passage_used") is not False
        or summary.get("metric_computed") is not False
        or summary.get("contains_corpus_text") is not False
    ):
        raise ConcurrencySupervisorError("concurrency canary contract mismatch")
    return summary


def _gpu_utilization() -> int:
    completed = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=utilization.gpu",
            "--format=csv,noheader,nounits",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )
    values = [int(value.strip()) for value in completed.stdout.splitlines() if value.strip()]
    if len(values) != 1 or not 0 <= values[0] <= 100:
        raise ConcurrencySupervisorError("invalid GPU utilization sample")
    return values[0]


def _worker_command(
    *,
    seed: int,
    training_root: Path,
    test_root: Path,
    output_root: Path,
    approved_commit: str,
    approval_reference: str,
) -> list[str]:
    return [
        sys.executable,
        "-m",
        "scripts.run_f2_f3_nautilus_multiseed_eval",
        "--seed",
        str(seed),
        "--training-root",
        str(training_root),
        "--test-input-root",
        str(test_root),
        "--output-root",
        str(output_root),
        "--resume-root",
        str(output_root / f"seed-{seed}" / "attempts" / SOURCE_ATTEMPT_ID),
        "--kernel-start-epoch-seconds",
        str(time.time()),
        "--approved-commit",
        approved_commit,
        "--approval-reference",
        approval_reference,
        "--confirmation",
        CONTINUATION_CONFIRMATION,
        "--concurrent-continuation",
        "--resume-source-attempt-id",
        SOURCE_ATTEMPT_ID,
        "--resume-source-commit",
        SOURCE_EVALUATION_COMMIT,
        "--batch-size",
        str(CONCURRENT_BATCH_SIZE),
    ]


def _terminate_all(processes: dict[int, subprocess.Popen]) -> None:
    for process in processes.values():
        if process.poll() is None:
            _stop_worker(process)


def supervise_all(
    *,
    commands: dict[int, list[str]],
    attempt_roots: dict[int, Path],
    activations: dict[int, dict],
    coordinator_root: Path,
    popen_factory=subprocess.Popen,
    memory_reader=cgroup_memory,
    gpu_reader=_gpu_utilization,
    now=time.monotonic,
    sleep=time.sleep,
) -> dict:
    coordinator_root.mkdir(parents=True, exist_ok=False)
    processes: dict[int, subprocess.Popen] = {}
    logs = {}
    started = now()
    last_progress = {seed: started for seed in SEEDS}
    last_counts: dict[int, int | None] = {seed: None for seed in SEEDS}
    latest_progress: dict[int, dict | None] = {seed: None for seed in SEEDS}
    gpu_samples: list[int] = []
    gpu_sampler_failures = 0
    guard_reason: str | None = None
    guard_seed: int | None = None
    try:
        for seed in SEEDS:
            log = (coordinator_root / f"seed-{seed}.log").open(
                "x", encoding="utf-8", newline="\n"
            )
            logs[seed] = log
            processes[seed] = popen_factory(
                commands[seed],
                stdout=log,
                stderr=subprocess.STDOUT,
                env=os.environ.copy(),
            )
        while True:
            running = False
            for seed, process in processes.items():
                code = process.poll()
                if code is None:
                    running = True
                elif code != 0:
                    guard_reason = "worker_nonzero_exit"
                    guard_seed = seed
                    break
                observed = _progress_count(attempt_roots[seed] / "progress.json")
                if observed is not None:
                    count, progress = observed
                    latest_progress[seed] = progress
                    if count != last_counts[seed]:
                        last_counts[seed] = count
                        last_progress[seed] = now()
                if code is None and now() - last_progress[seed] >= NO_PROGRESS_TIMEOUT_SECONDS:
                    guard_reason = "no_progress_timeout"
                    guard_seed = seed
                    break
            if guard_reason:
                break
            if not running:
                break
            memory = memory_reader()
            if memory is not None and memory[0] / memory[1] >= MEMORY_HIGH_WATER_FRACTION:
                guard_reason = "memory_high_water"
                break
            if now() - started >= WALLCLOCK_SECONDS:
                guard_reason = "coordinator_wallclock"
                break
            try:
                gpu_samples.append(gpu_reader())
            except (OSError, ValueError, subprocess.SubprocessError, ConcurrencySupervisorError):
                gpu_sampler_failures += 1
            sleep(POLL_SECONDS)
        if guard_reason:
            _terminate_all(processes)
            for seed in SEEDS:
                if not (attempt_roots[seed] / "public_summary.json").is_file():
                    _write_guard_summary(
                        attempt_root=attempt_roots[seed],
                        seed=seed,
                        activation=activations[seed],
                        reason=guard_reason,
                        progress=latest_progress[seed],
                    )
            status = "incomplete_resource_guard"
        else:
            for seed, process in processes.items():
                if process.wait() != 0:
                    raise ConcurrencySupervisorError(f"seed {seed} exited nonzero")
                summary = json.loads(
                    (attempt_roots[seed] / "public_summary.json").read_text(
                        encoding="utf-8"
                    )
                )
                if summary.get("run_status") != "complete":
                    raise ConcurrencySupervisorError("worker completion summary mismatch")
            status = "complete"
        summary = {
            "schema_version": 1,
            "status": status,
            "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "worker_count": WORKER_COUNT,
            "seeds": list(SEEDS),
            "source_attempt_id": SOURCE_ATTEMPT_ID,
            "source_progress_counts": SOURCE_PROGRESS_COUNTS,
            "guard_reason": guard_reason,
            "guard_seed": guard_seed,
            "gpu_samples": len(gpu_samples),
            "gpu_sampler_failures": gpu_sampler_failures,
            "mean_gpu_utilization_percent": (
                round(statistics.mean(gpu_samples), 3) if gpu_samples else None
            ),
            "elapsed_seconds": round(now() - started, 3),
            "metrics_printed": False,
            "automatic_retry": False,
            "contains_corpus_text": False,
        }
        _write_json_atomic(coordinator_root / "public_summary.json", summary)
        return summary
    except BaseException as error:
        _terminate_all(processes)
        failure = {
            "schema_version": 1,
            "status": "failed",
            "error_type": type(error).__name__,
            "error_message_sha256": hashlib.sha256(
                str(error).encode("utf-8", errors="replace")
            ).hexdigest(),
            "metrics_printed": False,
            "automatic_retry": False,
            "contains_corpus_text": False,
        }
        _write_json_atomic(coordinator_root / "public_summary.json", failure)
        raise
    finally:
        for log in logs.values():
            log.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-root", required=True, type=Path)
    parser.add_argument("--test-input-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--coordinator-root", required=True, type=Path)
    parser.add_argument("--canary-root", required=True, type=Path)
    parser.add_argument("--approved-commit", required=True)
    parser.add_argument("--approval-reference", required=True)
    parser.add_argument("--confirmation", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    commit = actual_commit()
    activations = {
        seed: validate_concurrency_activation(
            stage="continuation",
            seed=seed,
            approved_commit=args.approved_commit,
            actual_commit=commit,
            approval_reference=args.approval_reference,
            confirmation=args.confirmation,
        )
        for seed in SEEDS
    }
    for activation in activations.values():
        activation["source_attempt_id"] = SOURCE_ATTEMPT_ID
    training_root = _require_private_absolute_path(args.training_root, "training root")
    test_root = _require_private_absolute_path(args.test_input_root, "test input root")
    output_root = _require_private_absolute_path(args.output_root, "output root")
    coordinator_base = _require_private_absolute_path(
        args.coordinator_root, "coordinator root"
    )
    canary_root = _require_private_absolute_path(args.canary_root, "canary root")
    validate_concurrency_canary(canary_root, args.approved_commit)
    attempt = next(iter(activations.values()))["attempt_id"]
    coordinator_root = coordinator_base / f"attempt-{attempt}"
    attempt_roots = {
        seed: output_root / f"seed-{seed}" / "attempts" / attempt for seed in SEEDS
    }
    commands = {
        seed: _worker_command(
            seed=seed,
            training_root=training_root,
            test_root=test_root,
            output_root=output_root,
            approved_commit=args.approved_commit,
            approval_reference=args.approval_reference,
        )
        for seed in SEEDS
    }
    result = supervise_all(
        commands=commands,
        attempt_roots=attempt_roots,
        activations=activations,
        coordinator_root=coordinator_root,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "complete":
        raise SystemExit(75)


if __name__ == "__main__":
    main()
