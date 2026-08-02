#!/usr/bin/env python3
"""Frozen identities and aggregate statistics for issue #171 evaluation."""

from __future__ import annotations

import json
from pathlib import Path
import re
from statistics import mean, stdev
from typing import Sequence

from scripts.f1_eval_utils import EXPECTED_TEST_RECORDS, EXPECTED_TEST_SHA256
from scripts.f2_f3_nautilus_utils import (
    SEEDS,
    arm_order,
    approval_attempt_id,
    validate_seed,
)
from scripts.run_f2_f3_nautilus_pair import validate_completed_arm


TRAINING_COMMIT = "108888dcf0ad34c49157b47e2561c406c5463bf8"
TEST_FILENAME = "nahw_gec_test.jsonl"
TEST_STAGING_CONFIRMATION = "STAGE_F2_F3_MULTI_SEED_NAHW_TEST"
EVALUATION_CONFIRMATION = "RUN_F2_F3_NAUTILUS_MULTI_SEED_EVALUATION"
AGGREGATE_CONFIRMATION = "AGGREGATE_F2_F3_MULTI_SEED_RESULTS"
STAGES = ("test-staging", "paired-evaluation", "aggregate-evaluation")
COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
APPROVAL_PATTERN = re.compile(
    r"https://github\.com/ALBA7OOTH-Research-Lab/Musahhih/"
    r"issues/171#issuecomment-[1-9][0-9]*"
)


class MultiSeedEvaluationError(ValueError):
    """Raised before a frozen issue #171 contract can be violated."""


def validate_activation(
    *,
    stage: str,
    seed: int | None,
    approved_commit: str,
    actual_commit: str,
    approval_reference: str,
    confirmation: str,
) -> dict:
    if stage not in STAGES:
        raise MultiSeedEvaluationError(f"stage must be one of {STAGES}")
    if (
        not COMMIT_PATTERN.fullmatch(approved_commit)
        or actual_commit != approved_commit
    ):
        raise MultiSeedEvaluationError("approved repository commit mismatch")
    if not APPROVAL_PATTERN.fullmatch(approval_reference):
        raise MultiSeedEvaluationError("approval must be an issue #171 comment URL")
    expected = {
        "test-staging": TEST_STAGING_CONFIRMATION,
        "paired-evaluation": EVALUATION_CONFIRMATION,
        "aggregate-evaluation": AGGREGATE_CONFIRMATION,
    }[stage]
    if confirmation != expected:
        raise MultiSeedEvaluationError("stage confirmation mismatch")
    if stage == "paired-evaluation":
        if seed is None:
            raise MultiSeedEvaluationError("paired evaluation requires one seed")
        validate_seed(seed)
        order = list(arm_order(seed))
    else:
        if seed is not None:
            raise MultiSeedEvaluationError(f"{stage} must not select a seed")
        order = None
    return {
        "stage": stage,
        "seed": seed,
        "arm_order": order,
        "approved_commit": approved_commit,
        "approval_reference": approval_reference,
        "attempt_id": approval_attempt_id(approval_reference),
        "contains_corpus_text": False,
    }


def _read_json(path: Path, label: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise MultiSeedEvaluationError(f"cannot read {label}") from error
    if not isinstance(value, dict):
        raise MultiSeedEvaluationError(f"{label} must be a JSON object")
    return value


def validate_training_pair(seed_root: Path, seed: int) -> dict[str, dict]:
    """Validate both frozen selected checkpoints without exposing dev losses."""

    validate_seed(seed)
    seed_root = Path(seed_root)
    expected_order = arm_order(seed)
    pair = _read_json(seed_root / "99_pair_complete.json", "pair completion")
    if (
        pair.get("seed") != seed
        or pair.get("arm_order") != list(expected_order)
        or pair.get("completed_arms") != list(expected_order)
        or pair.get("workflow_commit") != TRAINING_COMMIT
        or pair.get("contains_corpus_text") is not False
        or pair.get("nahw_passage_used") is not False
        or pair.get("qalb_test_used") is not False
    ):
        raise MultiSeedEvaluationError("pair completion contract mismatch")

    result: dict[str, dict] = {}
    for position, arm in enumerate(expected_order, 1):
        try:
            selection = validate_completed_arm(
                seed_root=seed_root,
                position=position,
                arm=arm,
                seed=seed,
                workflow_commit=TRAINING_COMMIT,
            )
        except RuntimeError as error:
            raise MultiSeedEvaluationError(
                f"{arm} completed-checkpoint validation failed"
            ) from error
        if selection is None:
            raise MultiSeedEvaluationError(f"{arm} completion is missing")
        selected = selection.get("selected_checkpoint")
        if selected not in ("checkpoint-125", "checkpoint-250"):
            raise MultiSeedEvaluationError(f"{arm} selected checkpoint is invalid")
        identities = selection.get("checkpoints", [])
        identity = next(
            (item for item in identities if item.get("checkpoint") == selected), None
        )
        if not isinstance(identity, dict):
            raise MultiSeedEvaluationError(f"{arm} selected identity is missing")
        result[arm] = {
            "arm": arm,
            "seed": seed,
            "selected_checkpoint": selected,
            "adapter_path": seed_root / arm.lower() / selected,
            "adapter_model_bytes": identity["adapter_model_bytes"],
            "adapter_model_sha256": identity["adapter_model_sha256"],
            "adapter_config_sha256": identity["adapter_config_sha256"],
            "training_commit": TRAINING_COMMIT,
            "adapter_merged": False,
            "contains_corpus_text": False,
        }
    return result


def aggregate_seed_summaries(summaries: Sequence[dict]) -> dict:
    """Aggregate the prospectively frozen five paired-seed outcomes."""

    by_seed: dict[int, dict] = {}
    for summary in summaries:
        seed = summary.get("seed")
        if seed in by_seed or seed not in SEEDS:
            raise MultiSeedEvaluationError("invalid or duplicate seed summary")
        if (
            summary.get("run_status") != "complete"
            or summary.get("records") != EXPECTED_TEST_RECORDS
            or summary.get("test_sha256") != EXPECTED_TEST_SHA256
            or summary.get("contains_corpus_text") is not False
        ):
            raise MultiSeedEvaluationError("seed summary contract mismatch")
        arms = summary.get("arms")
        comparison = summary.get("comparison")
        if not isinstance(arms, dict) or not isinstance(comparison, dict):
            raise MultiSeedEvaluationError("seed result fields are missing")
        for arm in ("F2-P1", "F3-P1"):
            metrics = arms.get(arm)
            if (
                not isinstance(metrics, dict)
                or not isinstance(metrics.get("correct"), int)
                or metrics["correct"] < 0
                or metrics["correct"] > EXPECTED_TEST_RECORDS
                or metrics.get("records") != EXPECTED_TEST_RECORDS
            ):
                raise MultiSeedEvaluationError(f"invalid {arm} metrics")
            expected_accuracy = metrics["correct"] / EXPECTED_TEST_RECORDS
            if metrics.get("accuracy") != expected_accuracy:
                raise MultiSeedEvaluationError(f"invalid {arm} accuracy")
        expected_difference = (
            arms["F3-P1"]["accuracy"] - arms["F2-P1"]["accuracy"]
        )
        if comparison.get("f3_minus_f2") != expected_difference:
            raise MultiSeedEvaluationError("paired difference mismatch")
        by_seed[seed] = summary

    if tuple(sorted(by_seed)) != SEEDS:
        raise MultiSeedEvaluationError("all five frozen seed summaries are required")

    f2 = [by_seed[seed]["arms"]["F2-P1"]["accuracy"] for seed in SEEDS]
    f3 = [by_seed[seed]["arms"]["F3-P1"]["accuracy"] for seed in SEEDS]
    differences = [
        by_seed[seed]["comparison"]["f3_minus_f2"] for seed in SEEDS
    ]
    return {
        "seeds": list(SEEDS),
        "per_seed": [
            {
                "seed": seed,
                "f2_accuracy": by_seed[seed]["arms"]["F2-P1"]["accuracy"],
                "f3_accuracy": by_seed[seed]["arms"]["F3-P1"]["accuracy"],
                "f3_minus_f2": by_seed[seed]["comparison"]["f3_minus_f2"],
            }
            for seed in SEEDS
        ],
        "F2-P1": {"mean_accuracy": mean(f2), "sample_sd": stdev(f2)},
        "F3-P1": {"mean_accuracy": mean(f3), "sample_sd": stdev(f3)},
        "F3-P1_minus_F2-P1": {
            "mean": mean(differences),
            "sample_sd": stdev(differences),
            "minimum": min(differences),
            "maximum": max(differences),
        },
        "standard_deviation_definition": "sample SD with denominator n-1",
        "post_hoc_robustness_evidence": True,
        "original_seed_3407_result_remains_primary": True,
        "contains_corpus_text": False,
    }


__all__ = [
    "AGGREGATE_CONFIRMATION",
    "APPROVAL_PATTERN",
    "EVALUATION_CONFIRMATION",
    "MultiSeedEvaluationError",
    "STAGES",
    "TEST_FILENAME",
    "TEST_STAGING_CONFIRMATION",
    "TRAINING_COMMIT",
    "aggregate_seed_summaries",
    "validate_activation",
    "validate_training_pair",
]
