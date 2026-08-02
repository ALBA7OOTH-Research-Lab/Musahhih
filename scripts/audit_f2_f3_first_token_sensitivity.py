#!/usr/bin/env python3
"""Audit a post-hoc first-token sensitivity without releasing private text."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


EXPECTED_ROWS = 511
EXPECTED = {
    "F2-P1": {
        "sha256": "ca4a6eb2f5e40a60be14f59cdc7365a0f327b41ab0b8f46c8a08c43cfb442753",
        "correct": 105,
        "multiple_words": 20,
    },
    "F3-P1": {
        "sha256": "ccb296e0f091bf28ebe4d7c8b9ed454934f4dade0b5793dcf1b3a5706379c35c",
        "correct": 162,
        "multiple_words": 2,
    },
}
REQUIRED_FIELDS = {
    "record_id",
    "gold_correction",
    "parsed_correction",
    "exact_match",
    "parsing_warnings",
}


class SensitivityAuditError(RuntimeError):
    """Raised when a private artifact fails a corpus-free contract check."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_rows(
    path: Path,
    *,
    arm: str,
    expected: dict[str, Any],
    expected_rows: int,
) -> list[dict]:
    if not path.is_file():
        raise SensitivityAuditError(f"{arm}: prediction artifact is missing")
    actual_hash = sha256_file(path)
    if actual_hash != expected["sha256"]:
        raise SensitivityAuditError(f"{arm}: prediction SHA-256 mismatch")

    rows: list[dict] = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise SensitivityAuditError(
                    f"{arm}: invalid JSON at row {line_number}"
                ) from error
            if not isinstance(row, dict) or not REQUIRED_FIELDS <= row.keys():
                raise SensitivityAuditError(
                    f"{arm}: invalid private row schema at row {line_number}"
                )
            if not isinstance(row["record_id"], str) or not row["record_id"]:
                raise SensitivityAuditError(
                    f"{arm}: invalid record identity at row {line_number}"
                )
            if not isinstance(row["gold_correction"], str):
                raise SensitivityAuditError(
                    f"{arm}: invalid gold field at row {line_number}"
                )
            if not isinstance(row["parsed_correction"], str):
                raise SensitivityAuditError(
                    f"{arm}: invalid parsed field at row {line_number}"
                )
            if not isinstance(row["exact_match"], bool):
                raise SensitivityAuditError(
                    f"{arm}: invalid exact-match field at row {line_number}"
                )
            warnings = row["parsing_warnings"]
            if not isinstance(warnings, list) or not all(
                isinstance(warning, str) for warning in warnings
            ):
                raise SensitivityAuditError(
                    f"{arm}: invalid warning field at row {line_number}"
                )
            if row["exact_match"] != (
                row["parsed_correction"] == row["gold_correction"]
            ):
                raise SensitivityAuditError(
                    f"{arm}: stored score mismatch at row {line_number}"
                )
            is_multi = len(row["parsed_correction"].split()) > 1
            if ("multiple_words" in warnings) != is_multi:
                raise SensitivityAuditError(
                    f"{arm}: multiple-word warning mismatch at row {line_number}"
                )
            rows.append(row)

    if len(rows) != expected_rows:
        raise SensitivityAuditError(f"{arm}: expected {expected_rows} rows")
    if len({row["record_id"] for row in rows}) != expected_rows:
        raise SensitivityAuditError(f"{arm}: record identities are not unique")
    correct = sum(row["exact_match"] for row in rows)
    if correct != expected["correct"]:
        raise SensitivityAuditError(f"{arm}: original correct-count mismatch")
    multiple_words = sum(
        "multiple_words" in row["parsing_warnings"] for row in rows
    )
    if multiple_words != expected["multiple_words"]:
        raise SensitivityAuditError(f"{arm}: multiple-word count mismatch")
    return rows


def _audit_arm(rows: list[dict], *, expected_hash: str) -> dict[str, Any]:
    original_correct = sum(row["exact_match"] for row in rows)
    flagged = 0
    rescued = 0
    harmed = 0
    counterfactual_correct = 0
    for row in rows:
        original = row["exact_match"]
        counterfactual = original
        if "multiple_words" in row["parsing_warnings"]:
            flagged += 1
            tokens = row["parsed_correction"].split()
            if len(tokens) < 2:
                raise SensitivityAuditError(
                    "counterfactual encountered an invalid flagged output"
                )
            counterfactual = tokens[0] == row["gold_correction"]
            rescued += int(counterfactual and not original)
            harmed += int(original and not counterfactual)
        counterfactual_correct += int(counterfactual)

    total = len(rows)
    return {
        "prediction_sha256": expected_hash,
        "number_of_records": total,
        "original_correct": original_correct,
        "original_accuracy": original_correct / total,
        "multiple_word_outputs": flagged,
        "rescued_by_first_token": rescued,
        "harmed_by_first_token": harmed,
        "counterfactual_correct": counterfactual_correct,
        "counterfactual_accuracy": counterfactual_correct / total,
        "counterfactual_change_percentage_points": (
            (counterfactual_correct - original_correct) / total * 100
        ),
    }


def audit_pair(
    f2_path: Path,
    f3_path: Path,
    *,
    expected: dict[str, dict[str, Any]] = EXPECTED,
    expected_rows: int = EXPECTED_ROWS,
) -> dict[str, Any]:
    """Return corpus-free aggregates for the frozen symmetric counterfactual."""

    f2_rows = _load_rows(
        f2_path,
        arm="F2-P1",
        expected=expected["F2-P1"],
        expected_rows=expected_rows,
    )
    f3_rows = _load_rows(
        f3_path,
        arm="F3-P1",
        expected=expected["F3-P1"],
        expected_rows=expected_rows,
    )
    if [row["record_id"] for row in f2_rows] != [
        row["record_id"] for row in f3_rows
    ]:
        raise SensitivityAuditError("F2-P1/F3-P1 ordered alignment mismatch")

    arms = {
        "F2-P1": _audit_arm(
            f2_rows, expected_hash=expected["F2-P1"]["sha256"]
        ),
        "F3-P1": _audit_arm(
            f3_rows, expected_hash=expected["F3-P1"]["sha256"]
        ),
    }
    original_difference = (
        arms["F3-P1"]["original_accuracy"] - arms["F2-P1"]["original_accuracy"]
    )
    counterfactual_difference = (
        arms["F3-P1"]["counterfactual_accuracy"]
        - arms["F2-P1"]["counterfactual_accuracy"]
    )
    return {
        "schema_version": 1,
        "protocol_id": "F2-F3-FIRST-TOKEN-SENSITIVITY",
        "analysis_status": "complete",
        "analysis_class": "post_hoc_sensitivity",
        "counterfactual": {
            "scope": "only_outputs_already_flagged_multiple_words",
            "operation": "first_whitespace_token_of_existing_parsed_correction",
            "applied_symmetrically": True,
            "primary_parser_changed": False,
            "primary_metric_changed": False,
        },
        "arms": arms,
        "comparison": {
            "original_f3_minus_f2_percentage_points": original_difference * 100,
            "counterfactual_f3_minus_f2_percentage_points": (
                counterfactual_difference * 100
            ),
        },
        "audit": {
            "hashes_verified": True,
            "row_counts_verified": True,
            "unique_record_ids_verified": True,
            "ordered_alignment_verified": True,
            "stored_scores_verified": True,
            "warning_contract_verified": True,
            "contains_corpus_text": False,
        },
        "safeguards": {
            "training_executed": False,
            "model_loaded": False,
            "inference_executed": False,
            "gpu_used": False,
            "predictions_modified": False,
            "prompt_changed": False,
            "parser_changed": False,
            "checkpoint_changed": False,
            "record_level_output_published": False,
        },
    }


def write_new_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--f2-predictions", type=Path, required=True)
    parser.add_argument("--f3-predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = audit_pair(args.f2_predictions, args.f3_predictions)
    write_new_json(args.output, result)
    print("First-token sensitivity audit complete; corpus-text-free summary written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
