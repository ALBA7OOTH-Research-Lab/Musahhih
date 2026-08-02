#!/usr/bin/env python3
"""Run one issue #194 batch-stable replacement from record zero."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from scripts.f1_eval_utils import load_and_validate_nahw_records
from scripts.f2_f3_eval_rtx3090_utils import rtx3090_preflight
from scripts.f2_f3_fixed_checkpoint_repair_utils import (
    BATCH_SIZE,
    GPU_NAME,
    OUTPUT_ROOT,
    SAFE_STOP_ELAPSED_SECONDS,
    FixedCheckpointRepairError,
    validate_activation,
)
from scripts.f2_f3_fixed_checkpoint_utils import validate_unselected_training_pair
from scripts.f2_f3_multiseed_eval_utils import TEST_FILENAME
from scripts.run_f2_f3_final_eval import AdapterGenerator, _release_generator
from scripts.run_f2_f3_nautilus_multiseed_eval import (
    _public_adapter_meta,
    _require_private_absolute_path,
    execute,
    validate_test_staging,
)
from scripts.run_f2_f3_nautilus_pair import actual_commit, runtime_summary


def synthetic_batch_stability_gate(
    adapter: Path, *, required_gpu: str, generator_factory=AdapterGenerator,
) -> dict:
    """Require two identical runs of the exact frozen batch-16 path."""

    prompts = [
        "Synthetic non-corpus stability check. Return TOKEN. Context: "
        + "synthetic token " * (80 + (index % 16) * 8)
        for index in range(BATCH_SIZE)
    ]
    generator = generator_factory(adapter, required_gpu=required_gpu)
    try:
        generator.load()
        first = generator.generate_batch(prompts)
        second = generator.generate_batch(prompts)
        if len(first) != BATCH_SIZE or first != second:
            raise FixedCheckpointRepairError(
                "repeated batch-16 synthetic stability failed"
            )
        return {
            "status": "passed",
            "synthetic_records": BATCH_SIZE,
            "batch_size": BATCH_SIZE,
            "repeated_batch_equal": True,
            "single_batch_equivalence_required": False,
            "output_sha256": hashlib.sha256(
                json.dumps(first, ensure_ascii=False).encode("utf-8")
            ).hexdigest(),
            "contains_corpus_text": False,
        }
    finally:
        _release_generator(generator)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--training-root", required=True, type=Path)
    parser.add_argument("--test-input-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--kernel-start-epoch-seconds", required=True, type=float)
    parser.add_argument("--approved-commit", required=True)
    parser.add_argument("--approval-reference", required=True)
    parser.add_argument("--confirmation", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    activation = validate_activation(
        seed=args.seed,
        approved_commit=args.approved_commit,
        actual_commit=actual_commit(),
        approval_reference=args.approval_reference,
        confirmation=args.confirmation,
    )
    if args.output_root.as_posix() != OUTPUT_ROOT:
        raise FixedCheckpointRepairError("repair output root mismatch")

    os.environ["UNSLOTH_COMPILE_DISABLE"] = "1"
    import torch

    gpu = rtx3090_preflight(torch)
    runtime_summary(torch, gpu)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False

    training_root = _require_private_absolute_path(args.training_root, "training root")
    output_root = _require_private_absolute_path(args.output_root, "output root")
    validated = validate_unselected_training_pair(
        training_root / f"seed-{args.seed}", args.seed
    )
    first_arm = next(iter(validated))
    activation["pretest_gate"] = synthetic_batch_stability_gate(
        validated[first_arm]["adapter_path"], required_gpu=GPU_NAME
    )

    test_root = _require_private_absolute_path(args.test_input_root, "test input root")
    validate_test_staging(test_root)
    records = load_and_validate_nahw_records(test_root / TEST_FILENAME)
    public = _public_adapter_meta(validated)
    summary = execute(
        activation=activation,
        records=records,
        adapter_meta={
            arm: {**public[arm], "adapter_path": validated[arm]["adapter_path"]}
            for arm in public
        },
        output_root=output_root,
        resume_root=None,
        kernel_start_epoch_seconds=args.kernel_start_epoch_seconds,
        batch_size=BATCH_SIZE,
        required_gpu=GPU_NAME,
        safe_stop_elapsed_seconds=SAFE_STOP_ELAPSED_SECONDS,
    )
    print(json.dumps({
        "run_status": summary["run_status"],
        "seed": args.seed,
        "metrics_printed": False,
        "training_executed": False,
        "contains_corpus_text": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
