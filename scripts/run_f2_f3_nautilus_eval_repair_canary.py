#!/usr/bin/env python3
"""Run one non-test A100 batching/utilization canary after an issue #175 GO."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import threading
import time

from scripts.f2_f3_eval_repair_utils import (
    CANARY_CONFIRMATION,
    validate_repair_activation,
)
from scripts.f2_f3_multiseed_eval_utils import validate_training_pair
from scripts.f2_f3_nautilus_utils import a100_preflight
from scripts.run_f2_f3_final_eval import (
    AdapterGenerator,
    _fsync_stream,
    _write_json_atomic,
)
from scripts.run_f2_f3_nautilus_multiseed_eval import (
    REPAIR_BATCH_SIZE,
    _require_private_absolute_path,
)
from scripts.run_f2_f3_nautilus_pair import actual_commit, runtime_summary
from scripts.supervise_f2_f3_nautilus_eval_repair import cgroup_memory


CANARY_SEED = 3407
CANARY_ARM = "F2-P1"
SOAK_BATCHES = 16
MINIMUM_GPU_SAMPLES = 10
MINIMUM_MEAN_GPU_UTILIZATION = 40.0
MAXIMUM_MEMORY_FRACTION = 0.80


class RepairCanaryError(RuntimeError):
    """Raised when the repaired runtime is not safe to continue."""

    def __init__(self, message: str, *, evidence: dict | None = None) -> None:
        super().__init__(message)
        self.evidence = evidence or {}


def synthetic_prompts() -> list[str]:
    base = "synthetic validation token "
    return [
        (
            "This is synthetic non-corpus load testing. Return only TOKEN. Context: "
            + base * (80 + (index % 16) * 8)
        )
        for index in range(REPAIR_BATCH_SIZE)
    ]


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
        raise RepairCanaryError("GPU utilization sampler returned invalid data")
    return values[0]


def _sample_resources(stop: threading.Event, samples: dict[str, list]) -> None:
    while not stop.wait(1):
        try:
            samples["gpu"].append(_gpu_utilization())
        except (OSError, ValueError, subprocess.SubprocessError, RepairCanaryError):
            samples["sampler_failures"].append(1)
        memory = cgroup_memory()
        if memory is not None:
            samples["memory"].append(memory)


def run_canary(
    generator: AdapterGenerator, *, durability_probe_path: Path | None = None
) -> dict:
    prompts = synthetic_prompts()
    single = [generator(prompt) for prompt in prompts]
    batched = generator.generate_batch(prompts)
    if single != batched:
        raise RepairCanaryError("single-versus-batch synthetic outputs differ")
    samples: dict[str, list] = {"gpu": [], "memory": [], "sampler_failures": []}
    stop = threading.Event()
    sampler = threading.Thread(
        target=_sample_resources, args=(stop, samples), daemon=True
    )
    sampler.start()
    started = time.monotonic()
    durability_rows = 0
    durability_stream = None
    try:
        if durability_probe_path is not None:
            durability_stream = durability_probe_path.open(
                "x", encoding="utf-8", newline="\n"
            )
        for _ in range(SOAK_BATCHES):
            outputs = generator.generate_batch(prompts)
            if len(outputs) != REPAIR_BATCH_SIZE:
                raise RepairCanaryError("synthetic soak output count mismatch")
            if durability_stream is not None:
                for output in outputs:
                    durability_stream.write(
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
                    _fsync_stream(durability_stream)
                    durability_rows += 1
    finally:
        try:
            if durability_stream is not None:
                durability_stream.close()
        finally:
            stop.set()
            sampler.join(timeout=10)
    evidence = {
        "single_batch_equivalent": True,
        "batch_size": REPAIR_BATCH_SIZE,
        "soak_batches": SOAK_BATCHES,
        "synthetic_generations": REPAIR_BATCH_SIZE * SOAK_BATCHES,
        "durability_probe_rows": durability_rows,
        "per_row_fsync": durability_probe_path is not None,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "gpu_samples": len(samples["gpu"]),
        "gpu_sampler_failures": len(samples["sampler_failures"]),
        "contains_corpus_text": False,
    }
    if samples["sampler_failures"] or len(samples["gpu"]) < MINIMUM_GPU_SAMPLES:
        raise RepairCanaryError(
            "GPU utilization sampling was incomplete", evidence=evidence
        )
    mean_gpu = statistics.mean(samples["gpu"])
    memory_fractions = [current / maximum for current, maximum in samples["memory"]]
    if not memory_fractions:
        raise RepairCanaryError(
            "cgroup memory sampling was unavailable", evidence=evidence
        )
    peak_memory = max(memory_fractions)
    evidence.update(
        {
            "mean_gpu_utilization_percent": round(mean_gpu, 3),
            "peak_memory_fraction": round(peak_memory, 6),
        }
    )
    if mean_gpu < MINIMUM_MEAN_GPU_UTILIZATION:
        raise RepairCanaryError(
            "mean GPU utilization did not clear 40 percent", evidence=evidence
        )
    if peak_memory >= MAXIMUM_MEMORY_FRACTION:
        raise RepairCanaryError(
            "canary memory reached the 80 percent guard", evidence=evidence
        )
    return evidence


def _error_digest(error: BaseException) -> str:
    return hashlib.sha256(str(error).encode("utf-8", errors="replace")).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--approved-commit", required=True)
    parser.add_argument("--approval-reference", required=True)
    parser.add_argument("--confirmation", required=True)
    return parser.parse_args()


def run_and_persist_canary(
    *,
    adapter_path: Path,
    common: dict,
    summary_path: Path,
    generator_factory=AdapterGenerator,
) -> dict:
    """Persist a corpus-free summary on both pass and failure paths."""

    try:
        generator = generator_factory(adapter_path, required_gpu="A100")
        result = run_canary(
            generator,
            durability_probe_path=summary_path.parent / "durability_probe.jsonl",
        )
    except BaseException as error:
        summary = {
            **common,
            "status": "failed",
            "error_type": type(error).__name__,
            "error_message_sha256": _error_digest(error),
            **(error.evidence if isinstance(error, RepairCanaryError) else {}),
        }
        _write_json_atomic(summary_path, summary)
        print(json.dumps(summary, indent=2, sort_keys=True))
        raise
    summary = {**common, "status": "complete", **result}
    _write_json_atomic(summary_path, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def main() -> None:
    args = parse_args()
    activation = validate_repair_activation(
        stage="utilization-canary",
        seed=None,
        approved_commit=args.approved_commit,
        actual_commit=actual_commit(),
        approval_reference=args.approval_reference,
        confirmation=args.confirmation,
    )
    import torch

    gpu = a100_preflight(torch)
    runtime_summary(torch, gpu)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    training_root = _require_private_absolute_path(args.training_root, "training root")
    output_root = _require_private_absolute_path(args.output_root, "output root")
    selected = validate_training_pair(
        training_root / f"seed-{CANARY_SEED}", CANARY_SEED
    )[CANARY_ARM]
    attempt_root = output_root / f"attempt-{activation['attempt_id']}"
    attempt_root.mkdir(parents=True, exist_ok=False)
    common = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "approved_commit": activation["approved_commit"],
        "approval_reference": activation["approval_reference"],
        "attempt_id": activation["attempt_id"],
        "seed": CANARY_SEED,
        "arm": CANARY_ARM,
        "adapter_model_sha256": selected["adapter_model_sha256"],
        "batch_size": REPAIR_BATCH_SIZE,
        "soak_batches": SOAK_BATCHES,
        "synthetic_generations": REPAIR_BATCH_SIZE * SOAK_BATCHES,
        "nahw_passage_used": False,
        "qalb_test_used": False,
        "private_prediction_used": False,
        "metric_computed": False,
        "training_executed": False,
        "automatic_retry": False,
        "contains_corpus_text": False,
    }
    run_and_persist_canary(
        adapter_path=selected["adapter_path"],
        common=common,
        summary_path=attempt_root / "public_summary.json",
    )


if __name__ == "__main__":
    main()
