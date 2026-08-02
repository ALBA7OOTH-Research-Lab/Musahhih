#!/usr/bin/env python3
"""Run the issue #177 synthetic five-worker batch-16 A100 canary."""

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
    WORKER_COUNT,
    validate_concurrency_activation,
)
from scripts.f2_f3_multiseed_eval_utils import validate_training_pair
from scripts.f2_f3_eval_mps_utils import validate_mps_activation
from scripts.f2_f3_nautilus_utils import a100_preflight
from scripts.run_f2_f3_final_eval import AdapterGenerator, _fsync_stream, _write_json_atomic
from scripts.run_f2_f3_nautilus_multiseed_eval import _require_private_absolute_path
from scripts.run_f2_f3_nautilus_pair import actual_commit, runtime_summary
from scripts.supervise_f2_f3_nautilus_eval_repair import cgroup_memory


CANARY_SEED = 3407
CANARY_ARM = "F2-P1"
SOAK_BATCHES = 24
MINIMUM_SAMPLES = 10
MINIMUM_MEAN_GPU_UTILIZATION = 40.0
MAXIMUM_HOST_MEMORY_FRACTION = 0.80
MAXIMUM_GPU_MEMORY_FRACTION = 0.85
READY_TIMEOUT_SECONDS = 1_800
SOAK_TIMEOUT_SECONDS = 3_600


class ConcurrencyCanaryError(RuntimeError):
    """Raised when concurrent batch-16 execution is not safe to continue."""


def _mps_topology() -> dict:
    if not os.environ.get("CUDA_MPS_PIPE_DIRECTORY"):
        raise ConcurrencyCanaryError("CUDA MPS pipe directory is not configured")
    server_result = subprocess.run(
        ["nvidia-cuda-mps-control"],
        input="get_server_list\n",
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )
    servers = [
        int(line.strip())
        for line in server_result.stdout.splitlines()
        if line.strip().isdigit()
    ]
    if len(servers) != 1:
        raise ConcurrencyCanaryError("expected exactly one CUDA MPS server")
    client_result = subprocess.run(
        ["nvidia-cuda-mps-control"],
        input=f"get_client_list {servers[0]}\n",
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )
    clients = [
        int(line.strip())
        for line in client_result.stdout.splitlines()
        if line.strip().isdigit()
    ]
    if len(set(clients)) != WORKER_COUNT:
        raise ConcurrencyCanaryError("all five workers must attach to CUDA MPS")
    return {
        "mps_server_count": 1,
        "mps_client_count": len(set(clients)),
        "mps_active_thread_percentage": int(
            os.environ.get("CUDA_MPS_ACTIVE_THREAD_PERCENTAGE", "0")
        ),
    }


def synthetic_prompts() -> list[str]:
    base = "synthetic validation token "
    return [
        (
            "This is synthetic non-corpus load testing. Return only TOKEN. Context: "
            + base * (80 + (index % 16) * 8)
        )
        for index in range(CONCURRENT_BATCH_SIZE)
    ]


def _digest(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _gpu_sample() -> tuple[int, int, int]:
    completed = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=utilization.gpu,memory.used,memory.total",
            "--format=csv,noheader,nounits",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if len(lines) != 1:
        raise ConcurrencyCanaryError("expected exactly one GPU telemetry row")
    values = tuple(int(part.strip()) for part in lines[0].split(","))
    if len(values) != 3 or not 0 <= values[0] <= 100 or values[2] <= 0:
        raise ConcurrencyCanaryError("invalid GPU telemetry")
    return values


def _worker(args: argparse.Namespace) -> None:
    adapter = _require_private_absolute_path(args.adapter, "adapter")
    worker_root = _require_private_absolute_path(args.worker_root, "worker root")
    worker_root.mkdir(parents=True, exist_ok=False)
    summary_path = worker_root / "summary.json"
    try:
        import torch

        gpu = a100_preflight(torch)
        runtime = runtime_summary(torch, gpu)
        if gpu["total_memory_bytes"] < 75 * 1024**3:
            raise ConcurrencyCanaryError("concurrency canary requires an 80 GB A100")
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        generator = AdapterGenerator(adapter, required_gpu="A100")
        generator.load()
        _write_json_atomic(
            worker_root / "ready.json",
            {
                "worker": args.worker,
                "status": "ready",
                "runtime": runtime,
                "contains_corpus_text": False,
            },
        )
        deadline = time.monotonic() + READY_TIMEOUT_SECONDS
        while not args.start_marker.is_file():
            if time.monotonic() >= deadline:
                raise ConcurrencyCanaryError("worker start-marker timeout")
            time.sleep(0.25)
        prompts = synthetic_prompts()
        reference = generator.generate_batch(prompts)
        if len(reference) != CONCURRENT_BATCH_SIZE:
            raise ConcurrencyCanaryError("reference output count mismatch")
        reference_digest = _digest(reference)
        durability_rows = 0
        with (worker_root / "durability.jsonl").open(
            "x", encoding="utf-8", newline="\n"
        ) as stream:
            for _ in range(SOAK_BATCHES):
                outputs = generator.generate_batch(prompts)
                if outputs != reference:
                    raise ConcurrencyCanaryError("batch-16 output changed during soak")
                for output in outputs:
                    stream.write(
                        json.dumps(
                            {
                                "synthetic": True,
                                "output_sha256": hashlib.sha256(
                                    output.encode("utf-8", errors="replace")
                                ).hexdigest(),
                                "padding": "x" * 2048,
                            },
                            sort_keys=True,
                        )
                        + "\n"
                    )
                    _fsync_stream(stream)
                    durability_rows += 1
        _write_json_atomic(
            summary_path,
            {
                "worker": args.worker,
                "status": "complete",
                "batch_size": CONCURRENT_BATCH_SIZE,
                "soak_batches": SOAK_BATCHES,
                "reference_output_sha256": reference_digest,
                "durability_rows": durability_rows,
                "per_row_fsync": True,
                "mps_pipe_configured": bool(
                    os.environ.get("CUDA_MPS_PIPE_DIRECTORY")
                ),
                "mps_active_thread_percentage": int(
                    os.environ.get("CUDA_MPS_ACTIVE_THREAD_PERCENTAGE", "0")
                ),
                "runtime": generator.runtime,
                "contains_corpus_text": False,
            },
        )
    except BaseException as error:
        _write_json_atomic(
            summary_path,
            {
                "worker": args.worker,
                "status": "failed",
                "error_type": type(error).__name__,
                "error_message_sha256": hashlib.sha256(
                    str(error).encode("utf-8", errors="replace")
                ).hexdigest(),
                "contains_corpus_text": False,
            },
        )
        raise


def validate_worker_summaries(
    summaries: list[dict], *, mps_required: bool = False
) -> dict:
    expected_rows = CONCURRENT_BATCH_SIZE * SOAK_BATCHES
    if len(summaries) != WORKER_COUNT:
        raise ConcurrencyCanaryError("worker summary count mismatch")
    digests = set()
    for index, summary in enumerate(summaries):
        if (
            summary.get("worker") != index
            or summary.get("status") != "complete"
            or summary.get("batch_size") != CONCURRENT_BATCH_SIZE
            or summary.get("soak_batches") != SOAK_BATCHES
            or summary.get("durability_rows") != expected_rows
            or summary.get("per_row_fsync") is not True
            or summary.get("contains_corpus_text") is not False
            or (
                mps_required
                and (
                    summary.get("mps_pipe_configured") is not True
                    or summary.get("mps_active_thread_percentage") != 20
                )
            )
        ):
            raise ConcurrencyCanaryError("worker summary contract mismatch")
        digest = summary.get("reference_output_sha256")
        if not isinstance(digest, str) or len(digest) != 64:
            raise ConcurrencyCanaryError("worker reference digest is invalid")
        digests.add(digest)
    if len(digests) != 1:
        raise ConcurrencyCanaryError("concurrent batch-16 worker outputs differ")
    return {
        "worker_count": WORKER_COUNT,
        "batch_size": CONCURRENT_BATCH_SIZE,
        "soak_batches_per_worker": SOAK_BATCHES,
        "synthetic_generations": expected_rows * WORKER_COUNT,
        "durability_probe_rows": expected_rows * WORKER_COUNT,
        "per_row_fsync": True,
        "concurrent_worker_outputs_equivalent": True,
        "reference_output_sha256": next(iter(digests)),
    }


def _terminate(processes: list[subprocess.Popen]) -> None:
    for process in processes:
        if process.poll() is None:
            process.terminate()
    for process in processes:
        if process.poll() is None:
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=30)


def _parent(args: argparse.Namespace) -> None:
    if args.mps_canary:
        activation = validate_mps_activation(
            approved_commit=args.approved_commit,
            actual_commit=actual_commit(),
            approval_reference=args.approval_reference,
            confirmation=args.confirmation,
        )
    else:
        activation = validate_concurrency_activation(
            stage="concurrency-canary",
            seed=None,
            approved_commit=args.approved_commit,
            actual_commit=actual_commit(),
            approval_reference=args.approval_reference,
            confirmation=args.confirmation,
        )
    training_root = _require_private_absolute_path(args.training_root, "training root")
    output_root = _require_private_absolute_path(args.output_root, "output root")
    selected = validate_training_pair(
        training_root / f"seed-{CANARY_SEED}", CANARY_SEED
    )[CANARY_ARM]
    attempt_root = output_root / f"attempt-{activation['attempt_id']}"
    attempt_root.mkdir(parents=True, exist_ok=False)
    start_marker = attempt_root / "start"
    processes: list[subprocess.Popen] = []
    logs = []
    samples: list[tuple[int, int, int]] = []
    host_samples: list[tuple[int, int]] = []
    sampler_failures = 0
    mps_evidence: dict = {}
    started = time.monotonic()
    common = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "approved_commit": activation["approved_commit"],
        "approval_reference": activation["approval_reference"],
        "attempt_id": activation["attempt_id"],
        "worker_count": WORKER_COUNT,
        "batch_size": CONCURRENT_BATCH_SIZE,
        "mps_required": args.mps_canary,
        "nahw_passage_used": False,
        "qalb_test_used": False,
        "private_prediction_used": False,
        "metric_computed": False,
        "training_executed": False,
        "automatic_retry": False,
        "contains_corpus_text": False,
    }
    try:
        for worker in range(WORKER_COUNT):
            root = attempt_root / f"worker-{worker}"
            log = (attempt_root / f"worker-{worker}.log").open(
                "x", encoding="utf-8", newline="\n"
            )
            logs.append(log)
            processes.append(
                subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "scripts.run_f2_f3_nautilus_eval_concurrency_canary",
                        "--worker",
                        str(worker),
                        "--adapter",
                        str(selected["adapter_path"]),
                        "--worker-root",
                        str(root),
                        "--start-marker",
                        str(start_marker),
                    ],
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    env=os.environ.copy(),
                )
            )
        ready_deadline = time.monotonic() + READY_TIMEOUT_SECONDS
        while True:
            if any(process.poll() is not None for process in processes):
                raise ConcurrencyCanaryError("worker failed before synchronized start")
            if all(
                (attempt_root / f"worker-{worker}" / "ready.json").is_file()
                for worker in range(WORKER_COUNT)
            ):
                break
            if time.monotonic() >= ready_deadline:
                raise ConcurrencyCanaryError("workers did not become ready in time")
            time.sleep(1)
        if args.mps_canary:
            mps_evidence = _mps_topology()
            if mps_evidence["mps_active_thread_percentage"] != 20:
                raise ConcurrencyCanaryError(
                    "CUDA MPS active thread percentage must equal 20"
                )
        start_marker.write_text("start\n", encoding="ascii")
        soak_deadline = time.monotonic() + SOAK_TIMEOUT_SECONDS
        while any(process.poll() is None for process in processes):
            if time.monotonic() >= soak_deadline:
                raise ConcurrencyCanaryError("concurrent soak timeout")
            try:
                samples.append(_gpu_sample())
            except (OSError, ValueError, subprocess.SubprocessError, ConcurrencyCanaryError):
                sampler_failures += 1
            memory = cgroup_memory()
            if memory is not None:
                host_samples.append(memory)
            time.sleep(1)
        exit_codes = [process.wait() for process in processes]
        if any(code != 0 for code in exit_codes):
            raise ConcurrencyCanaryError("one or more canary workers failed")
        summaries = [
            json.loads(
                (attempt_root / f"worker-{worker}" / "summary.json").read_text(
                    encoding="utf-8"
                )
            )
            for worker in range(WORKER_COUNT)
        ]
        evidence = validate_worker_summaries(
            summaries, mps_required=args.mps_canary
        )
        if sampler_failures or len(samples) < MINIMUM_SAMPLES:
            raise ConcurrencyCanaryError("GPU telemetry sampling was incomplete")
        if not host_samples:
            raise ConcurrencyCanaryError("host-memory telemetry was unavailable")
        mean_gpu = statistics.mean(sample[0] for sample in samples)
        peak_gpu_memory = max(sample[1] / sample[2] for sample in samples)
        peak_host_memory = max(current / maximum for current, maximum in host_samples)
        evidence.update(
            {
                "gpu_samples": len(samples),
                "gpu_sampler_failures": sampler_failures,
                "mean_gpu_utilization_percent": round(mean_gpu, 3),
                "peak_gpu_memory_fraction": round(peak_gpu_memory, 6),
                "peak_host_memory_fraction": round(peak_host_memory, 6),
                "elapsed_seconds": round(time.monotonic() - started, 3),
            }
        )
        if mean_gpu < MINIMUM_MEAN_GPU_UTILIZATION:
            raise ConcurrencyCanaryError("mean GPU utilization did not clear 40 percent")
        if peak_gpu_memory >= MAXIMUM_GPU_MEMORY_FRACTION:
            raise ConcurrencyCanaryError("GPU memory reached the 85 percent guard")
        if peak_host_memory >= MAXIMUM_HOST_MEMORY_FRACTION:
            raise ConcurrencyCanaryError("host memory reached the 80 percent guard")
        summary = {**common, "status": "complete", **mps_evidence, **evidence}
        _write_json_atomic(attempt_root / "public_summary.json", summary)
        print(json.dumps(summary, indent=2, sort_keys=True))
    except BaseException as error:
        _terminate(processes)
        summary = {
            **common,
            "status": "failed",
            "error_type": type(error).__name__,
            "error_message_sha256": hashlib.sha256(
                str(error).encode("utf-8", errors="replace")
            ).hexdigest(),
            "gpu_samples": len(samples),
            "gpu_sampler_failures": sampler_failures,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            **mps_evidence,
        }
        if samples:
            summary["mean_gpu_utilization_percent"] = round(
                statistics.mean(sample[0] for sample in samples), 3
            )
            summary["peak_gpu_memory_fraction"] = round(
                max(sample[1] / sample[2] for sample in samples), 6
            )
        if host_samples:
            summary["peak_host_memory_fraction"] = round(
                max(current / maximum for current, maximum in host_samples), 6
            )
        _write_json_atomic(attempt_root / "public_summary.json", summary)
        print(json.dumps(summary, indent=2, sort_keys=True))
        raise
    finally:
        for log in logs:
            log.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", type=int)
    parser.add_argument("--adapter", type=Path)
    parser.add_argument("--worker-root", type=Path)
    parser.add_argument("--start-marker", type=Path)
    parser.add_argument("--training-root", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--approved-commit")
    parser.add_argument("--approval-reference")
    parser.add_argument("--confirmation")
    parser.add_argument("--mps-canary", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.worker is not None:
        if not 0 <= args.worker < WORKER_COUNT:
            raise ConcurrencyCanaryError("invalid worker index")
        if args.adapter is None or args.worker_root is None or args.start_marker is None:
            raise ConcurrencyCanaryError("worker paths are required")
        _worker(args)
    else:
        required = (
            args.training_root,
            args.output_root,
            args.approved_commit,
            args.approval_reference,
            args.confirmation,
        )
        if any(value is None for value in required):
            raise ConcurrencyCanaryError("parent activation arguments are required")
        _parent(args)


if __name__ == "__main__":
    main()
