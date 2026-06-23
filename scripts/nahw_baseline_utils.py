#!/usr/bin/env python3
"""Conservative parsing and accounting helpers for the Nahw baseline.

These helpers deliberately avoid Unicode or Arabic spelling normalization.
"""

from __future__ import annotations

from collections.abc import Sequence


_PAIRED_WRAPPERS = (
    ("**", "**"),
    ("__", "__"),
    ("`", "`"),
    ('"', '"'),
    ("'", "'"),
    ("«", "»"),
    ("“", "”"),
)

_EXPLANATION_MARKERS = (
    "الكلمة المصححة:",
    "التصحيح:",
    "الإجابة:",
    "الجواب:",
)


def parse_model_response(raw_response: str) -> tuple[str, list[str]]:
    """Remove only harmless outer formatting and flag suspicious output.

    The function never uses the gold answer and never normalizes Arabic letters,
    diacritics, internal punctuation, or Unicode composition.
    """

    warnings: list[str] = []
    original = raw_response
    nonempty_lines = [line.strip() for line in raw_response.splitlines() if line.strip()]
    parsed = "\n".join(nonempty_lines).strip()

    changed = parsed != original
    wrapper_removed = True
    while parsed and wrapper_removed:
        wrapper_removed = False
        for opening, closing in _PAIRED_WRAPPERS:
            minimum_length = len(opening) + len(closing)
            if len(parsed) >= minimum_length and parsed.startswith(opening) and parsed.endswith(closing):
                parsed = parsed[len(opening) : len(parsed) - len(closing)].strip()
                changed = True
                wrapper_removed = True
                break

    if changed and parsed:
        warnings.append("outer_formatting_removed")
    if not parsed:
        warnings.append("empty_output")
        return parsed, warnings
    if len(nonempty_lines) > 1:
        warnings.append("multiple_lines")
    if len(parsed.split()) > 1:
        warnings.append("multiple_words")
    if any(marker in parsed for marker in _EXPLANATION_MARKERS):
        warnings.append("explanation_like")
    if len(parsed) > 64:
        warnings.append("unusually_long")
    return parsed, warnings


def summarize_predictions(rows: Sequence[dict]) -> dict:
    """Return transparent aggregate counts for already-scored predictions."""

    total = len(rows)
    correct = sum(bool(row["exact_match"]) for row in rows)
    empty = sum(not row["parsed_correction"] for row in rows)
    suspicious = sum(
        bool(set(row["parsing_warnings"]) - {"outer_formatting_removed"})
        for row in rows
    )
    multi_token = sum(
        "multiple_words" in row["parsing_warnings"] for row in rows
    )
    return {
        "number_of_records": total,
        "number_correct": correct,
        "exact_match_accuracy": correct / total if total else 0.0,
        "invalid_or_empty_count": empty,
        "parsing_failure_count": empty,
        "suspicious_output_count": suspicious,
        "multi_token_count": multi_token,
    }
