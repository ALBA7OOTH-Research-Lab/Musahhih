#!/usr/bin/env python3
"""Validate and aggregate five completed issue #171 private evaluations."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from scripts.f1_eval_utils import EXPECTED_TEST_RECORDS, sha256_file
from scripts.f2_f3_multiseed_eval_utils import (
    AGGREGATE_CONFIRMATION,
    aggregate_seed_summaries,
    validate_activation,
)
from scripts.f2_f3_nautilus_utils import SEEDS, atomic_write_json
from scripts.run_f2_f3_nautilus_pair import actual_commit


def _read_summary(path: Path, seed: int) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"cannot read seed {seed} summary") from error
    if not isinstance(value, dict):
        raise RuntimeError(f"seed {seed} summary must be an object")
    return value


def validate_private_seed_result(
    root: Path,
    *,
    seed: int,
    source_attempt_id: str,
    evaluation_commit: str,
) -> dict:
    attempt = root / f"seed-{seed}" / "attempts" / source_attempt_id
    summary = _read_summary(attempt / "public_summary.json", seed)
    if (
        summary.get("seed") != seed
        or summary.get("attempt_id") != source_attempt_id
        or summary.get("approved_commit") != evaluation_commit
        or summary.get("run_status") != "complete"
        or summary.get("contains_corpus_text") is not False
    ):
        raise RuntimeError(f"seed {seed} summary identity mismatch")
    for arm in ("F2-P1", "F3-P1"):
        path = attempt / f"{arm.lower()}_predictions.jsonl"
        metrics = summary.get("arms", {}).get(arm, {})
        if (
            not path.is_file()
            or sha256_file(path) != metrics.get("predictions_sha256")
            or sum(1 for line in path.open("rb") if line.strip())
            != EXPECTED_TEST_RECORDS
        ):
            raise RuntimeError(f"seed {seed} {arm} private prediction mismatch")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation-root", required=True, type=Path)
    parser.add_argument("--source-attempt-id", required=True)
    parser.add_argument("--evaluation-commit", required=True)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--approved-commit", required=True)
    parser.add_argument("--approval-reference", required=True)
    parser.add_argument("--confirmation", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    activation = validate_activation(
        stage="aggregate-evaluation",
        seed=None,
        approved_commit=args.approved_commit,
        actual_commit=actual_commit(),
        approval_reference=args.approval_reference,
        confirmation=args.confirmation,
    )
    summaries = [
        validate_private_seed_result(
            args.evaluation_root,
            seed=seed,
            source_attempt_id=args.source_attempt_id,
            evaluation_commit=args.evaluation_commit,
        )
        for seed in SEEDS
    ]
    aggregate = aggregate_seed_summaries(summaries)
    result = {
        "schema_version": 1,
        "status": "complete",
        "created_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat(),
        "approved_commit": activation["approved_commit"],
        "approval_reference": activation["approval_reference"],
        "attempt_id": activation["attempt_id"],
        "source_attempt_id": args.source_attempt_id,
        "evaluation_commit": args.evaluation_commit,
        "aggregate": aggregate,
        "private_predictions_hash_validated": True,
        "private_prediction_rows_per_arm_seed": EXPECTED_TEST_RECORDS,
        "contains_corpus_text": False,
    }
    output = (
        args.output_root / "aggregate" / f"attempt-{activation['attempt_id']}.json"
    )
    atomic_write_json(output, result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
