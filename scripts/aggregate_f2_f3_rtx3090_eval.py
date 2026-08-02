#!/usr/bin/env python3
"""Validate and aggregate the five completed issue #183 evaluations."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from scripts.f1_eval_utils import (
    BOOTSTRAP_SAMPLES,
    EXPECTED_TEST_RECORDS,
    EXPECTED_TEST_SHA256,
    paired_comparison,
    sha256_file,
)
from scripts.f2_f3_multiseed_eval_utils import aggregate_seed_summaries
from scripts.f2_f3_nautilus_utils import SEEDS, atomic_write_json
from scripts.f2_f3_eval_rtx3090_utils import BATCH_SIZE, GPU_NAME
from scripts.f2_f3_rtx3090_aggregate_utils import (
    EVALUATION_COMMIT,
    EVALUATION_ROOT,
    OUTPUT_ROOT,
    SOURCE_ATTEMPT_ID,
    validate_activation,
)
from scripts.run_f2_f3_nautilus_pair import actual_commit


ARMS = ("F2-P1", "F3-P1")


def _read_json(path: Path, label: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"cannot read {label}") from error
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} must be a JSON object")
    return value


def _read_prediction_contract(path: Path, *, seed: int, arm: str) -> dict:
    rows = []
    try:
        with path.open("r", encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    value = json.loads(line)
                    if not isinstance(value, dict):
                        raise RuntimeError("prediction row must be an object")
                    rows.append(value)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"cannot parse seed {seed} {arm} predictions") from error
    if len(rows) != EXPECTED_TEST_RECORDS:
        raise RuntimeError(f"seed {seed} {arm} prediction count mismatch")
    record_ids = [row.get("record_id") for row in rows]
    if (
        any(not isinstance(value, str) or not value for value in record_ids)
        or len(set(record_ids)) != EXPECTED_TEST_RECORDS
        or any(type(row.get("exact_match")) is not bool for row in rows)
    ):
        raise RuntimeError(f"seed {seed} {arm} prediction schema mismatch")
    order_sha256 = hashlib.sha256(
        json.dumps(record_ids, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    return {
        "rows": rows,
        "records": len(rows),
        "correct": sum(row["exact_match"] for row in rows),
        "predictions_sha256": sha256_file(path),
        "record_order_sha256": order_sha256,
    }


def validate_private_seed_result(root: Path, *, seed: int) -> dict:
    attempt = root / f"seed-{seed}" / "attempts" / SOURCE_ATTEMPT_ID
    summary_path = attempt / "public_summary.json"
    summary = _read_json(summary_path, f"seed {seed} summary")
    if (
        summary.get("seed") != seed
        or summary.get("attempt_id") != SOURCE_ATTEMPT_ID
        or summary.get("approved_commit") != EVALUATION_COMMIT
        or summary.get("run_status") != "complete"
        or summary.get("records") != EXPECTED_TEST_RECORDS
        or summary.get("test_sha256") != EXPECTED_TEST_SHA256
        or summary.get("batch_size") != BATCH_SIZE
        or summary.get("inference_gpu_required") != GPU_NAME
        or summary.get("pretest_gate", {}).get("status") != "passed"
        or summary.get("automatic_retry") is not False
        or summary.get("training_executed") is not False
        or summary.get("qalb_test_used") is not False
        or summary.get("contains_corpus_text") is not False
    ):
        raise RuntimeError(f"seed {seed} summary identity mismatch")

    contracts = {}
    for arm in ARMS:
        path = attempt / f"{arm.lower()}_predictions.jsonl"
        if not path.is_file():
            raise RuntimeError(f"seed {seed} {arm} predictions are missing")
        contract = _read_prediction_contract(path, seed=seed, arm=arm)
        metrics = summary.get("arms", {}).get(arm, {})
        if (
            metrics.get("records") != contract["records"]
            or metrics.get("correct") != contract["correct"]
            or metrics.get("accuracy") != contract["correct"] / EXPECTED_TEST_RECORDS
            or metrics.get("predictions_sha256") != contract["predictions_sha256"]
        ):
            raise RuntimeError(f"seed {seed} {arm} metric/hash mismatch")
        contracts[arm] = contract

    if (
        contracts["F2-P1"]["record_order_sha256"]
        != contracts["F3-P1"]["record_order_sha256"]
    ):
        raise RuntimeError(f"seed {seed} paired record order mismatch")
    recomputed = paired_comparison(
        contracts["F2-P1"]["rows"],
        contracts["F3-P1"]["rows"],
        bootstrap_samples=BOOTSTRAP_SAMPLES,
        seed=seed,
    )
    comparison = summary.get("comparison", {})
    expected = {
        "f3_minus_f2": recomputed["accuracy_difference_adapter_minus_baseline"],
        "f2_wrong_f3_right": recomputed["baseline_wrong_adapter_right"],
        "f2_right_f3_wrong": recomputed["baseline_right_adapter_wrong"],
        "mcnemar_two_sided_exact_p_value": recomputed[
            "mcnemar_two_sided_exact_p_value"
        ],
        "paired_bootstrap_95_percentile_ci": recomputed[
            "paired_bootstrap_95_percentile_ci"
        ],
        "bootstrap_samples": BOOTSTRAP_SAMPLES,
        "bootstrap_seed": seed,
    }
    if any(comparison.get(key) != value for key, value in expected.items()):
        raise RuntimeError(f"seed {seed} paired statistic mismatch")
    return {
        "summary": summary,
        "summary_sha256": sha256_file(summary_path),
        "record_order_sha256": contracts["F2-P1"]["record_order_sha256"],
        "prediction_sha256": {
            arm: contracts[arm]["predictions_sha256"] for arm in ARMS
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation-root", type=Path, default=Path(EVALUATION_ROOT))
    parser.add_argument("--output-root", type=Path, default=Path(OUTPUT_ROOT))
    parser.add_argument("--approved-commit", required=True)
    parser.add_argument("--approval-reference", required=True)
    parser.add_argument("--confirmation", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    activation = validate_activation(
        approved_commit=args.approved_commit,
        actual_commit=actual_commit(),
        approval_reference=args.approval_reference,
        confirmation=args.confirmation,
    )
    if args.evaluation_root.as_posix() != EVALUATION_ROOT:
        raise RuntimeError("evaluation root mismatch")
    if args.output_root.as_posix() != OUTPUT_ROOT:
        raise RuntimeError("aggregate output root mismatch")
    validated = [
        validate_private_seed_result(args.evaluation_root, seed=seed)
        for seed in SEEDS
    ]
    order_hashes = {value["record_order_sha256"] for value in validated}
    if len(order_hashes) != 1:
        raise RuntimeError("record order differs across seeds")
    aggregate = aggregate_seed_summaries(
        [value["summary"] for value in validated]
    )
    result = {
        "schema_version": 1,
        "status": "complete",
        "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "approved_commit": activation["approved_commit"],
        "approval_reference": activation["approval_reference"],
        "attempt_id": activation["attempt_id"],
        "source_attempt_id": SOURCE_ATTEMPT_ID,
        "evaluation_commit": EVALUATION_COMMIT,
        "aggregate": aggregate,
        "source_summary_sha256": {
            str(seed): value["summary_sha256"]
            for seed, value in zip(SEEDS, validated, strict=True)
        },
        "source_prediction_sha256": {
            str(seed): value["prediction_sha256"]
            for seed, value in zip(SEEDS, validated, strict=True)
        },
        "common_record_order_sha256": next(iter(order_hashes)),
        "private_prediction_hashes_validated": True,
        "private_prediction_rows_per_arm_seed": EXPECTED_TEST_RECORDS,
        "private_prediction_files_validated": len(SEEDS) * len(ARMS),
        "record_alignment_validated": True,
        "per_seed_statistics_recomputed": True,
        "gpu_used": False,
        "inference_executed": False,
        "training_executed": False,
        "contains_corpus_text": False,
    }
    output = args.output_root / "aggregate" / f"attempt-{activation['attempt_id']}.json"
    atomic_write_json(output, result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
