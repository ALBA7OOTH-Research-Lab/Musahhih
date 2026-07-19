#!/usr/bin/env python3
"""Fail-closed validation and paired statistics for F1 safety diagnostics."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
import hashlib
import json
import math
from pathlib import Path
import random
import subprocess

from scripts.baseline_prompts import render_b0_prompt
from scripts.f1_eval_utils import EvaluationSafetyError, exact_mcnemar_p_value


CONFIRMATION = "RUN_MATCHED_F1_SAFETY_DIAGNOSTICS"
EXPECTED_OVERCORRECTION_SHA256 = (
    "fa0c3f7a5321ae0a97528aaaf8df0ac29fce0039d3fad9b1e3cf83de71ac2036"
)
EXPECTED_CAPABILITY_SHA256 = (
    "ff6d250150016a4a9d18248bd7af632d67c14a978c87ccb3e50cb2d28d4e9f9a"
)
EXPECTED_OVERCORRECTION_RECORDS = 154
EXPECTED_CAPABILITY_RECORDS = 1_000
EXPECTED_CAPABILITY_TASKS = 40
CAPABILITY_PER_TASK = 25
SEED = 3407
BOOTSTRAP_SAMPLES = 10_000


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_jsonl(path: Path, expected_sha256: str, label: str) -> list[dict]:
    path = Path(path).expanduser().resolve()
    if sha256_file(path) != expected_sha256:
        raise EvaluationSafetyError(f"{label} SHA-256 mismatch")
    rows: list[dict] = []
    try:
        with path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise EvaluationSafetyError(
                        f"{label} line {line_number} must be a JSON object"
                    )
                rows.append(row)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EvaluationSafetyError(f"unable to read valid UTF-8 {label}") from error
    return rows


def load_overcorrection_records(
    path: Path,
    *,
    expected_sha256: str = EXPECTED_OVERCORRECTION_SHA256,
    expected_records: int = EXPECTED_OVERCORRECTION_RECORDS,
) -> list[dict]:
    """Load the exact private QALB-development correct-input records."""

    rows = _load_jsonl(path, expected_sha256, "overcorrection input")
    if len(rows) != expected_records:
        raise EvaluationSafetyError("overcorrection record count mismatch")
    required = {
        "record_id", "source", "split", "passage", "selected_token_position",
        "selected_token", "gold_unchanged_token", "prompt",
    }
    seen: set[str] = set()
    for row in rows:
        if not required.issubset(row):
            raise EvaluationSafetyError("incomplete overcorrection record")
        record_id = row["record_id"]
        if not isinstance(record_id, str) or record_id in seen:
            raise EvaluationSafetyError("invalid or duplicate overcorrection record ID")
        if row["source"] != "QALB-2015-L2-Dev" or row["split"] != "dev":
            raise EvaluationSafetyError("overcorrection source/split mismatch")
        text_fields = ("passage", "selected_token", "gold_unchanged_token", "prompt")
        if not all(isinstance(row[field], str) for field in text_fields):
            raise EvaluationSafetyError("overcorrection text fields must be strings")
        tokens = row["passage"].split()
        position = row["selected_token_position"]
        if not isinstance(position, int) or isinstance(position, bool):
            raise EvaluationSafetyError("invalid overcorrection token position")
        if not 0 <= position < len(tokens) or tokens[position] != row["selected_token"]:
            raise EvaluationSafetyError("overcorrection token does not match passage")
        if row["selected_token"] != row["gold_unchanged_token"]:
            raise EvaluationSafetyError("overcorrection target is not unchanged")
        if row["prompt"] != render_b0_prompt(row["passage"], row["selected_token"]):
            raise EvaluationSafetyError("overcorrection prompt differs from frozen B0")
        seen.add(record_id)
    return rows


def load_capability_records(
    path: Path,
    *,
    expected_sha256: str = EXPECTED_CAPABILITY_SHA256,
    expected_records: int = EXPECTED_CAPABILITY_RECORDS,
) -> list[dict]:
    """Load the exact balanced ArabicMMLU selection and verify its contract."""

    rows = _load_jsonl(path, expected_sha256, "capability input")
    if len(rows) != expected_records:
        raise EvaluationSafetyError("capability record count mismatch")
    required = {
        "record_id", "task", "source_id", "source", "split", "prompt",
        "choices", "gold_choice",
    }
    seen: set[str] = set()
    task_counts: Counter[str] = Counter()
    alphabet = ["A", "B", "C", "D", "E"]
    for row in rows:
        if not required.issubset(row):
            raise EvaluationSafetyError("incomplete capability record")
        record_id = row["record_id"]
        if not isinstance(record_id, str) or record_id in seen:
            raise EvaluationSafetyError("invalid or duplicate capability record ID")
        if row["source"] != "MBZUAI/ArabicMMLU" or row["split"] != "test":
            raise EvaluationSafetyError("capability source/split mismatch")
        if not all(isinstance(row[field], str) for field in (
            "task", "source_id", "prompt", "gold_choice"
        )):
            raise EvaluationSafetyError("capability text fields must be strings")
        choices = row["choices"]
        if not isinstance(choices, list) or choices not in tuple(
            alphabet[:size] for size in range(2, 6)
        ):
            raise EvaluationSafetyError("capability choices must be an ordered A-B to A-E prefix")
        if row["gold_choice"] not in choices:
            raise EvaluationSafetyError("capability gold choice is unavailable")
        if not row["prompt"].startswith("This is a ") or not row["prompt"].endswith(
            "\n\nAnswer:"
        ):
            raise EvaluationSafetyError("capability prompt shape mismatch")
        seen.add(record_id)
        task_counts[row["task"]] += 1
    if len(task_counts) != EXPECTED_CAPABILITY_TASKS or set(task_counts.values()) != {
        CAPABILITY_PER_TASK
    }:
        raise EvaluationSafetyError("capability task balance mismatch")
    return rows


def require_execution_authorization(
    confirmation: str | None,
    approved_commit: str | None,
    approval_reference: str | None,
    *,
    repository: Path,
) -> None:
    if confirmation != CONFIRMATION:
        raise EvaluationSafetyError("exact safety-diagnostic confirmation is required")
    if not approved_commit or len(approved_commit) != 40 or any(
        character not in "0123456789abcdef" for character in approved_commit.lower()
    ):
        raise EvaluationSafetyError("approved protocol commit must be a 40-character SHA")
    if not approval_reference or not approval_reference.startswith("https://github.com/"):
        raise EvaluationSafetyError("GitHub approval reference is required")
    try:
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", approved_commit, "HEAD"],
            cwd=repository,
            check=False,
            capture_output=True,
        )
    except OSError as error:
        raise EvaluationSafetyError("unable to verify approved protocol commit") from error
    if result.returncode != 0:
        raise EvaluationSafetyError("approved protocol commit is not an ancestor of HEAD")


def _linear_percentile(sorted_values: Sequence[float], probability: float) -> float:
    if not sorted_values:
        raise ValueError("percentile requires at least one value")
    position = (len(sorted_values) - 1) * probability
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return float(sorted_values[low])
    weight = position - low
    return float(sorted_values[low] * (1.0 - weight) + sorted_values[high] * weight)


def stratified_paired_bootstrap_interval(
    differences_by_stratum: dict[str, Sequence[int]],
    *,
    samples: int = BOOTSTRAP_SAMPLES,
    seed: int = SEED,
) -> tuple[float, float]:
    if not differences_by_stratum or samples <= 0:
        raise ValueError("stratified bootstrap requires strata and positive samples")
    ordered = [(name, tuple(values)) for name, values in sorted(differences_by_stratum.items())]
    if any(not values for _, values in ordered):
        raise ValueError("stratified bootstrap cannot contain an empty stratum")
    total = sum(len(values) for _, values in ordered)
    rng = random.Random(seed)
    estimates = []
    for _ in range(samples):
        sampled_sum = 0
        for _, values in ordered:
            sampled_sum += sum(values[rng.randrange(len(values))] for _ in values)
        estimates.append(sampled_sum / total)
    estimates.sort()
    return _linear_percentile(estimates, 0.025), _linear_percentile(estimates, 0.975)


def paired_binary_comparison(
    baseline_rows: Sequence[dict],
    adapter_rows: Sequence[dict],
    *,
    outcome_field: str,
    stratum_field: str | None = None,
    bootstrap_samples: int = BOOTSTRAP_SAMPLES,
    seed: int = SEED,
) -> dict:
    """Compare aligned boolean outcomes with the pre-registered paired analysis."""

    def indexed(rows: Sequence[dict], label: str) -> dict[str, tuple[bool, str | None]]:
        output: dict[str, tuple[bool, str | None]] = {}
        for row in rows:
            record_id = row.get("record_id")
            if not isinstance(record_id, str) or record_id in output:
                raise EvaluationSafetyError(f"invalid or duplicate {label} record ID")
            outcome = row.get(outcome_field)
            if not isinstance(outcome, bool):
                raise EvaluationSafetyError(f"{label} {outcome_field} must be boolean")
            stratum = row.get(stratum_field) if stratum_field else None
            if stratum_field and not isinstance(stratum, str):
                raise EvaluationSafetyError(f"{label} stratum must be a string")
            output[record_id] = (outcome, stratum)
        return output

    baseline = indexed(baseline_rows, "baseline")
    adapter = indexed(adapter_rows, "adapter")
    if baseline.keys() != adapter.keys() or not baseline:
        raise EvaluationSafetyError("baseline and adapter record IDs do not match")
    differences_by_stratum: dict[str, list[int]] = {}
    n01 = n10 = baseline_correct = adapter_correct = 0
    for record_id in sorted(baseline):
        baseline_value, baseline_stratum = baseline[record_id]
        adapter_value, adapter_stratum = adapter[record_id]
        if baseline_stratum != adapter_stratum:
            raise EvaluationSafetyError("baseline and adapter strata do not match")
        difference = int(adapter_value) - int(baseline_value)
        differences_by_stratum.setdefault(baseline_stratum or "all", []).append(difference)
        baseline_correct += int(baseline_value)
        adapter_correct += int(adapter_value)
        n01 += difference == 1
        n10 += difference == -1
    lower, upper = stratified_paired_bootstrap_interval(
        differences_by_stratum, samples=bootstrap_samples, seed=seed
    )
    total = len(baseline)
    return {
        "number_of_paired_records": total,
        "baseline_correct": baseline_correct,
        "baseline_accuracy": baseline_correct / total,
        "adapter_correct": adapter_correct,
        "adapter_accuracy": adapter_correct / total,
        "accuracy_difference_adapter_minus_baseline": (
            adapter_correct - baseline_correct
        ) / total,
        "baseline_wrong_adapter_right": n01,
        "baseline_right_adapter_wrong": n10,
        "mcnemar_two_sided_exact_p_value": exact_mcnemar_p_value(n01, n10),
        "stratified_paired_bootstrap_95_percentile_ci": [lower, upper],
        "bootstrap_samples": bootstrap_samples,
        "bootstrap_seed": seed,
        "bootstrap_strata": len(differences_by_stratum),
    }


def select_highest_logit(choices: Sequence[str], scores: dict[str, float]) -> str:
    """Return the highest-scoring choice, breaking exact ties by display order."""

    if not choices or len(set(choices)) != len(choices):
        raise EvaluationSafetyError("choices must be nonempty and unique")
    if set(scores) != set(choices):
        raise EvaluationSafetyError("candidate scores do not match available choices")
    if any(
        isinstance(scores[choice], bool)
        or not isinstance(scores[choice], (int, float))
        or not math.isfinite(scores[choice])
        for choice in choices
    ):
        raise EvaluationSafetyError("candidate scores must be finite numbers")
    return max(choices, key=lambda choice: scores[choice])
