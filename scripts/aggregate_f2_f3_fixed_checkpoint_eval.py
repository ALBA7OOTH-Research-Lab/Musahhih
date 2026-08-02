#!/usr/bin/env python3
"""Validate private sources and aggregate fixed checkpoint policies."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from statistics import mean, stdev

from scripts.aggregate_f2_f3_rtx3090_eval import validate_private_seed_result
from scripts.f1_eval_utils import (
    BOOTSTRAP_SAMPLES,
    EXPECTED_TEST_RECORDS,
    EXPECTED_TEST_SHA256,
    paired_comparison,
    sha256_file,
)
from scripts.f2_f3_eval_rtx3090_utils import BATCH_SIZE, GPU_NAME
from scripts.f2_f3_fixed_checkpoint_aggregate_utils import (
    OUTPUT_ROOT,
    SELECTED_ATTEMPT_ID,
    SELECTED_COMMIT,
    SELECTED_ROOT,
    TRAINING_ROOT,
    UNSELECTED_ATTEMPTS,
    UNSELECTED_COMMITS,
    UNSELECTED_ROOTS,
    validate_activation,
)
from scripts.f2_f3_fixed_checkpoint_utils import validate_unselected_training_pair
from scripts.f2_f3_multiseed_eval_utils import TRAINING_COMMIT, validate_training_pair
from scripts.f2_f3_nautilus_utils import SEEDS, atomic_write_json
from scripts.run_f2_f3_nautilus_pair import actual_commit


ARMS = ("F2-P1", "F3-P1")
CHECKPOINTS = ("checkpoint-125", "checkpoint-250")
POLICIES = (
    ("fixed_epoch_1", "Fixed epoch 1", "checkpoint-125"),
    ("fixed_epoch_2", "Fixed epoch 2", "checkpoint-250"),
    ("dev_selected", "Dev-selected", None),
)


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
    return {
        "rows": rows,
        "records": len(rows),
        "correct": sum(row["exact_match"] for row in rows),
        "predictions_sha256": sha256_file(path),
        "record_order_sha256": hashlib.sha256(
            json.dumps(record_ids, ensure_ascii=False, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest(),
    }


def _public_adapter_meta(meta: dict) -> dict:
    return {key: value for key, value in meta.items() if key != "adapter_path"}


def _validate_adapter_meta(summary: dict, expected: dict[str, dict], *, seed: int) -> None:
    adapters = summary.get("adapters")
    if not isinstance(adapters, dict):
        raise RuntimeError(f"seed {seed} adapter metadata missing")
    for arm in ARMS:
        if adapters.get(arm) != _public_adapter_meta(expected[arm]):
            raise RuntimeError(f"seed {seed} {arm} adapter identity mismatch")


def validate_unselected_private_seed_result(
    root: Path,
    *,
    seed: int,
    attempt_id: str,
    evaluation_commit: str,
    expected_adapters: dict[str, dict],
) -> dict:
    attempt = root / f"seed-{seed}" / "attempts" / attempt_id
    summary_path = attempt / "public_summary.json"
    summary = _read_json(summary_path, f"seed {seed} unselected summary")
    if (
        summary.get("seed") != seed
        or summary.get("attempt_id") != attempt_id
        or summary.get("approved_commit") != evaluation_commit
        or summary.get("training_commit") != TRAINING_COMMIT
        or summary.get("run_status") != "complete"
        or summary.get("records") != EXPECTED_TEST_RECORDS
        or summary.get("test_sha256") != EXPECTED_TEST_SHA256
        or summary.get("batch_size") != BATCH_SIZE
        or summary.get("inference_gpu_required") != GPU_NAME
        or summary.get("pretest_gate", {}).get("status") != "passed"
        or summary.get("automatic_retry") is not False
        or summary.get("training_executed") is not False
        or summary.get("qalb_test_used") is not False
        or summary.get("prompt_or_parser_changed") is not False
        or summary.get("development_values_exposed") is not False
        or summary.get("contains_corpus_text") is not False
    ):
        raise RuntimeError(f"seed {seed} unselected summary identity mismatch")
    _validate_adapter_meta(summary, expected_adapters, seed=seed)

    contracts = {}
    for arm in ARMS:
        path = attempt / f"{arm.lower()}_predictions.jsonl"
        if not path.is_file():
            raise RuntimeError(f"seed {seed} {arm} unselected predictions missing")
        contract = _read_prediction_contract(path, seed=seed, arm=arm)
        metrics = summary.get("arms", {}).get(arm, {})
        if (
            metrics.get("records") != contract["records"]
            or metrics.get("correct") != contract["correct"]
            or metrics.get("accuracy") != contract["correct"] / EXPECTED_TEST_RECORDS
            or metrics.get("predictions_sha256") != contract["predictions_sha256"]
        ):
            raise RuntimeError(f"seed {seed} {arm} unselected metric/hash mismatch")
        contracts[arm] = contract
    if contracts["F2-P1"]["record_order_sha256"] != contracts["F3-P1"][
        "record_order_sha256"
    ]:
        raise RuntimeError(f"seed {seed} unselected paired order mismatch")
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
        raise RuntimeError(f"seed {seed} unselected paired statistic mismatch")
    return {
        "summary": summary,
        "summary_sha256": sha256_file(summary_path),
        "record_order_sha256": contracts["F2-P1"]["record_order_sha256"],
        "prediction_sha256": {
            arm: contracts[arm]["predictions_sha256"] for arm in ARMS
        },
    }


def _checkpoint(meta: dict) -> str:
    value = meta.get("checkpoint", meta.get("selected_checkpoint"))
    if value not in CHECKPOINTS:
        raise RuntimeError("checkpoint identity is invalid")
    return value


def _policy_cell(source: dict, *, arm: str, source_kind: str) -> dict:
    summary = source["summary"]
    metrics = summary["arms"][arm]
    return {
        "checkpoint": _checkpoint(summary["adapters"][arm]),
        "correct": metrics["correct"],
        "accuracy": metrics["accuracy"],
        "source_kind": source_kind,
        "source_attempt_id": summary["attempt_id"],
        "predictions_sha256": source["prediction_sha256"][arm],
    }


def build_policy_aggregate(validated: list[dict]) -> dict:
    by_seed = {value["seed"]: value for value in validated}
    if tuple(sorted(by_seed)) != SEEDS or len(by_seed) != len(validated):
        raise RuntimeError("all five unique seeds are required")
    per_seed = []
    policy_values = {key: {arm: [] for arm in ARMS} for key, _, _ in POLICIES}
    differences = {key: [] for key, _, _ in POLICIES}
    for seed in SEEDS:
        source_pair = by_seed[seed]
        policies = {}
        for key, label, target in POLICIES:
            arms = {}
            for arm in ARMS:
                if key == "dev_selected":
                    source_kind = "selected"
                else:
                    matches = [
                        kind
                        for kind in ("selected", "unselected")
                        if _checkpoint(source_pair[kind]["summary"]["adapters"][arm])
                        == target
                    ]
                    if len(matches) != 1:
                        raise RuntimeError(
                            f"seed {seed} {arm} does not cover checkpoint {target} once"
                        )
                    source_kind = matches[0]
                arms[arm] = _policy_cell(
                    source_pair[source_kind], arm=arm, source_kind=source_kind
                )
                policy_values[key][arm].append(arms[arm]["accuracy"])
            difference = arms["F3-P1"]["accuracy"] - arms["F2-P1"]["accuracy"]
            differences[key].append(difference)
            policies[key] = {
                "label": label,
                "arms": arms,
                "f3_minus_f2": difference,
            }
        per_seed.append({"seed": seed, "policies": policies})

    across_seed = {}
    compact_table = []
    for key, label, _ in POLICIES:
        f2 = policy_values[key]["F2-P1"]
        f3 = policy_values[key]["F3-P1"]
        diff = differences[key]
        across_seed[key] = {
            "label": label,
            "F2-P1": {"mean_accuracy": mean(f2), "sample_sd": stdev(f2)},
            "F3-P1": {"mean_accuracy": mean(f3), "sample_sd": stdev(f3)},
            "F3-P1_minus_F2-P1": {
                "mean": mean(diff),
                "sample_sd": stdev(diff),
                "minimum": min(diff),
                "maximum": max(diff),
            },
        }
        compact_table.append({
            "checkpoint_policy": label,
            "f2_mean_accuracy": mean(f2),
            "f3_mean_accuracy": mean(f3),
            "f3_minus_f2_mean": mean(diff),
        })
    return {
        "seeds": list(SEEDS),
        "per_seed": per_seed,
        "across_seed": across_seed,
        "compact_table": compact_table,
        "standard_deviation_definition": "sample SD with denominator n-1",
        "post_hoc_sensitivity_evidence": True,
        "original_seed_3407_result_remains_primary": True,
        "contains_corpus_text": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selected-root", type=Path, default=Path(SELECTED_ROOT))
    parser.add_argument("--issue-192-root", type=Path, default=Path("/private/evaluations/issue-192"))
    parser.add_argument("--issue-194-root", type=Path, default=Path("/private/evaluations/issue-194"))
    parser.add_argument("--training-root", type=Path, default=Path(TRAINING_ROOT))
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
    if (
        args.selected_root.as_posix() != SELECTED_ROOT
        or args.issue_192_root.as_posix() != "/private/evaluations/issue-192"
        or args.issue_194_root.as_posix() != "/private/evaluations/issue-194"
        or args.training_root.as_posix() != TRAINING_ROOT
        or args.output_root.as_posix() != OUTPUT_ROOT
    ):
        raise RuntimeError("private source/output root mismatch")

    unselected_roots = {
        "/private/evaluations/issue-192": args.issue_192_root,
        "/private/evaluations/issue-194": args.issue_194_root,
    }
    validated = []
    for seed in SEEDS:
        selected_adapters = validate_training_pair(args.training_root / f"seed-{seed}", seed)
        unselected_adapters = validate_unselected_training_pair(
            args.training_root / f"seed-{seed}", seed
        )
        selected = validate_private_seed_result(args.selected_root, seed=seed)
        _validate_adapter_meta(selected["summary"], selected_adapters, seed=seed)
        if (
            selected["summary"].get("attempt_id") != SELECTED_ATTEMPT_ID
            or selected["summary"].get("approved_commit") != SELECTED_COMMIT
        ):
            raise RuntimeError(f"seed {seed} selected source identity mismatch")
        unselected = validate_unselected_private_seed_result(
            unselected_roots[UNSELECTED_ROOTS[seed]],
            seed=seed,
            attempt_id=UNSELECTED_ATTEMPTS[seed],
            evaluation_commit=UNSELECTED_COMMITS[seed],
            expected_adapters=unselected_adapters,
        )
        if selected["record_order_sha256"] != unselected["record_order_sha256"]:
            raise RuntimeError(f"seed {seed} selected/unselected order mismatch")
        validated.append({"seed": seed, "selected": selected, "unselected": unselected})

    order_hashes = {
        item[kind]["record_order_sha256"]
        for item in validated
        for kind in ("selected", "unselected")
    }
    if len(order_hashes) != 1:
        raise RuntimeError("record order differs across seeds or checkpoint sources")
    aggregate = build_policy_aggregate(validated)
    result = {
        "schema_version": 1,
        "status": "complete",
        "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "approved_commit": activation["approved_commit"],
        "approval_reference": activation["approval_reference"],
        "attempt_id": activation["attempt_id"],
        "source_attempts": {
            "selected_issue_183": SELECTED_ATTEMPT_ID,
            "unselected_issue_192": "5157509573",
            "unselected_issue_194": "5158062318",
        },
        "aggregate": aggregate,
        "source_summary_sha256": {
            str(item["seed"]): {
                kind: item[kind]["summary_sha256"]
                for kind in ("selected", "unselected")
            }
            for item in validated
        },
        "source_prediction_sha256": {
            str(item["seed"]): {
                kind: item[kind]["prediction_sha256"]
                for kind in ("selected", "unselected")
            }
            for item in validated
        },
        "common_record_order_sha256": next(iter(order_hashes)),
        "training_checkpoint_identities_validated": True,
        "private_prediction_files_validated": len(SEEDS) * len(ARMS) * 2,
        "private_prediction_rows_per_file": EXPECTED_TEST_RECORDS,
        "record_alignment_validated": True,
        "source_statistics_recomputed": True,
        "gpu_used": False,
        "inference_executed": False,
        "training_executed": False,
        "development_values_exposed": False,
        "contains_corpus_text": False,
    }
    output = args.output_root / "aggregate" / f"attempt-{activation['attempt_id']}.json"
    atomic_write_json(output, result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
