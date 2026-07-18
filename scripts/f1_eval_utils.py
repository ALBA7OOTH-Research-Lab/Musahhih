#!/usr/bin/env python3
"""Fail-closed validation and paired statistics for F1-P1 final evaluation."""

from __future__ import annotations

from collections.abc import Sequence
import hashlib
import json
import math
from pathlib import Path
import random
import subprocess

from scripts.baseline_prompts import render_b0_prompt


RUN_ID = "F1-P1__gemma3-4b-it__nahw-passage__s3407__r01"
CONFIRMATION = "RUN_F1_P1_NAHW_FINAL_511"
BASE_MODEL_ID = "unsloth/gemma-3-4b-it-unsloth-bnb-4bit"
BASE_MODEL_REVISION = "316726ca0bd24aa323bfaf86e8a379ee1176d1fe"
EXPECTED_ADAPTER_CONFIG_SHA256 = (
    "db19ef8bf4852698103dde20cd50b4429ca102ac96980f7939ecc4cff2049c4d"
)
EXPECTED_SELECTION_SHA256 = (
    "898c19d5dcead1f6c8f0ed27b6e8c5c6b9ebaec2f1b2a9909e58d8c9758ee123"
)
EXPECTED_TEST_SHA256 = (
    "acb3cfd204b35d5415532fbd32a4a5231b553fae329ab8f48e8454609e10279b"
)
EXPECTED_BASELINE_PREDICTIONS_SHA256 = (
    "6997b6fe5959f5502511ebdd1885d05a89ebaefeb27eefb73520842598f36ebc"
)
EXPECTED_TEST_RECORDS = 511
SEED = 3407
MAX_NEW_TOKENS = 32
BOOTSTRAP_SAMPLES = 10_000
TARGET_MODULES = {
    "q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"
}


class EvaluationSafetyError(ValueError):
    """Raised when any pre-registered evaluation gate fails."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path, label: str) -> dict:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EvaluationSafetyError(f"unable to read valid UTF-8 {label}") from error
    if not isinstance(value, dict):
        raise EvaluationSafetyError(f"{label} must be a JSON object")
    return value


def validate_adapter_checkpoint(
    adapter_path: Path,
    *,
    expected_adapter_sha256: str = EXPECTED_ADAPTER_CONFIG_SHA256,
    expected_selection_sha256: str = EXPECTED_SELECTION_SHA256,
) -> dict:
    """Verify the selected private checkpoint without reading adapter weights."""

    adapter_path = Path(adapter_path).expanduser().resolve()
    if adapter_path.name != "checkpoint-250" or not adapter_path.is_dir():
        raise EvaluationSafetyError("adapter must be the checkpoint-250 directory")
    config_path = adapter_path / "adapter_config.json"
    selection_path = adapter_path.parent / "checkpoint_selection.json"
    if sha256_file(config_path) != expected_adapter_sha256:
        raise EvaluationSafetyError("adapter_config.json SHA-256 mismatch")
    if sha256_file(selection_path) != expected_selection_sha256:
        raise EvaluationSafetyError("checkpoint_selection.json SHA-256 mismatch")
    config = _load_json(config_path, "adapter config")
    selection = _load_json(selection_path, "checkpoint selection")
    expected_config = {
        "base_model_name_or_path": BASE_MODEL_ID,
        "peft_type": "LORA",
        "r": 16,
        "lora_alpha": 32,
        "lora_dropout": 0.0,
        "bias": "none",
        "inference_mode": True,
    }
    for field, expected in expected_config.items():
        if config.get(field) != expected:
            raise EvaluationSafetyError(f"adapter config mismatch: {field}")
    if set(config.get("target_modules", [])) != TARGET_MODULES:
        raise EvaluationSafetyError("adapter target_modules mismatch")
    auto_mapping = config.get("auto_mapping")
    if not isinstance(auto_mapping, dict) or auto_mapping.get("base_model_class") != (
        "Gemma3ForConditionalGeneration"
    ):
        raise EvaluationSafetyError("adapter base model class mismatch")
    if selection.get("selected_checkpoint") != "checkpoint-250":
        raise EvaluationSafetyError("checkpoint selection does not select checkpoint-250")
    return {
        "adapter_path": str(adapter_path),
        "adapter_config_sha256": expected_adapter_sha256,
        "checkpoint_selection_sha256": expected_selection_sha256,
    }


def load_and_validate_nahw_records(
    path: Path,
    *,
    expected_sha256: str = EXPECTED_TEST_SHA256,
    expected_records: int = EXPECTED_TEST_RECORDS,
) -> list[dict]:
    """Load the frozen prepared test file and validate its full contract."""

    path = Path(path).expanduser().resolve()
    if sha256_file(path) != expected_sha256:
        raise EvaluationSafetyError("Nahw evaluation file SHA-256 mismatch")
    records: list[dict] = []
    seen: set[str] = set()
    required = {
        "id", "passage_id", "prompt", "passage", "error", "gold_correction",
        "split", "source",
    }
    try:
        with path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                if not isinstance(row, dict) or not required.issubset(row):
                    raise EvaluationSafetyError(
                        f"invalid or incomplete Nahw record at line {line_number}"
                    )
                text_fields = required - {"passage_id"}
                if not all(isinstance(row[field], str) for field in text_fields):
                    raise EvaluationSafetyError(
                        f"Nahw text fields must be strings at line {line_number}"
                    )
                if not isinstance(row["passage_id"], (str, int)) or isinstance(
                    row["passage_id"], bool
                ):
                    raise EvaluationSafetyError(
                        f"Nahw passage_id has invalid type at line {line_number}"
                    )
                if row["id"] in seen:
                    raise EvaluationSafetyError("duplicate Nahw record ID")
                if row["split"] != "test" or row["source"] != "Nahw-Passage":
                    raise EvaluationSafetyError("Nahw source/split marker mismatch")
                if row["prompt"] != render_b0_prompt(row["passage"], row["error"]):
                    raise EvaluationSafetyError("stored Nahw prompt differs from frozen B0")
                seen.add(row["id"])
                records.append(row)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EvaluationSafetyError("unable to read valid UTF-8 Nahw JSONL") from error
    if len(records) != expected_records:
        raise EvaluationSafetyError(
            f"Nahw record count mismatch: expected {expected_records}, got {len(records)}"
        )
    return records


def load_validated_baseline_predictions(
    path: Path,
    *,
    expected_sha256: str = EXPECTED_BASELINE_PREDICTIONS_SHA256,
    expected_records: int = EXPECTED_TEST_RECORDS,
) -> list[dict]:
    """Load only the exact accepted B0 record-level prediction artifact."""

    path = Path(path).expanduser().resolve()
    if sha256_file(path) != expected_sha256:
        raise EvaluationSafetyError("accepted B0 predictions SHA-256 mismatch")
    try:
        with path.open("r", encoding="utf-8") as stream:
            rows = [json.loads(line) for line in stream if line.strip()]
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EvaluationSafetyError("unable to read valid UTF-8 B0 predictions") from error
    if len(rows) != expected_records:
        raise EvaluationSafetyError("accepted B0 prediction count mismatch")
    return rows


def require_execution_authorization(
    confirmation: str | None,
    approved_commit: str | None,
    approval_reference: str | None,
    *,
    repository: Path,
) -> None:
    if confirmation != CONFIRMATION:
        raise EvaluationSafetyError("exact final-evaluation confirmation is required")
    if not approved_commit or len(approved_commit) != 40 or any(
        char not in "0123456789abcdef" for char in approved_commit.lower()
    ):
        raise EvaluationSafetyError("approved protocol commit must be a 40-character SHA")
    if not approval_reference or not approval_reference.startswith("https://github.com/"):
        raise EvaluationSafetyError("GitHub independent-approval reference is required")
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


def exact_mcnemar_p_value(n01: int, n10: int) -> float:
    if n01 < 0 or n10 < 0:
        raise ValueError("discordant counts cannot be negative")
    n = n01 + n10
    if n == 0:
        return 1.0
    k = min(n01, n10)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2**n)
    return min(1.0, 2.0 * tail)


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


def paired_bootstrap_interval(
    differences: Sequence[int],
    *,
    samples: int = BOOTSTRAP_SAMPLES,
    seed: int = SEED,
) -> tuple[float, float]:
    if not differences or samples <= 0:
        raise ValueError("paired bootstrap requires records and positive samples")
    rng = random.Random(seed)
    size = len(differences)
    estimates = sorted(
        sum(differences[rng.randrange(size)] for _ in range(size)) / size
        for _ in range(samples)
    )
    return _linear_percentile(estimates, 0.025), _linear_percentile(estimates, 0.975)


def paired_comparison(
    baseline_rows: Sequence[dict],
    adapter_rows: Sequence[dict],
    *,
    bootstrap_samples: int = BOOTSTRAP_SAMPLES,
    seed: int = SEED,
) -> dict:
    def indexed(rows: Sequence[dict], label: str) -> dict[str, bool]:
        output: dict[str, bool] = {}
        for row in rows:
            record_id = row.get("record_id", row.get("id"))
            if not isinstance(record_id, str) or record_id in output:
                raise EvaluationSafetyError(f"invalid or duplicate {label} record ID")
            if not isinstance(row.get("exact_match"), bool):
                raise EvaluationSafetyError(f"{label} exact_match must be boolean")
            output[record_id] = row["exact_match"]
        return output

    baseline = indexed(baseline_rows, "baseline")
    adapter = indexed(adapter_rows, "adapter")
    if baseline.keys() != adapter.keys():
        raise EvaluationSafetyError("baseline and adapter record IDs do not match")
    if not baseline:
        raise EvaluationSafetyError("paired comparison contains no records")
    ordered_ids = sorted(baseline)
    differences = [int(adapter[rid]) - int(baseline[rid]) for rid in ordered_ids]
    n01 = sum(value == 1 for value in differences)
    n10 = sum(value == -1 for value in differences)
    baseline_correct = sum(baseline.values())
    adapter_correct = sum(adapter.values())
    lower, upper = paired_bootstrap_interval(
        differences, samples=bootstrap_samples, seed=seed
    )
    total = len(ordered_ids)
    return {
        "number_of_paired_records": total,
        "baseline_correct": baseline_correct,
        "baseline_accuracy": baseline_correct / total,
        "adapter_correct": adapter_correct,
        "adapter_accuracy": adapter_correct / total,
        "accuracy_difference_adapter_minus_baseline": sum(differences) / total,
        "baseline_wrong_adapter_right": n01,
        "baseline_right_adapter_wrong": n10,
        "mcnemar_two_sided_exact_p_value": exact_mcnemar_p_value(n01, n10),
        "paired_bootstrap_95_percentile_ci": [lower, upper],
        "bootstrap_samples": bootstrap_samples,
        "bootstrap_seed": seed,
    }
