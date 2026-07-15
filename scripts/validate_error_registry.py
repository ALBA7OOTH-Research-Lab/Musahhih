#!/usr/bin/env python3
"""Validate the public, corpus-free Arabic error category registry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "data" / "registry" / "arabic_error_categories.json"

EXPECTED_CATEGORIES = {
    "OA": ("Orthography", "Confusion in Alif, Ya and Alif-Maqsura"),
    "OC": ("Orthography", "Wrong order of word characters"),
    "OD": ("Orthography", "Additional character(s)"),
    "OG": ("Orthography", "Lengthening short vowels"),
    "OH": ("Orthography", "Hamza errors"),
    "OM": ("Orthography", "Missing character(s)"),
    "ON": ("Orthography", "Confusion between Nun and Tanwin"),
    "OR": ("Orthography", "Replacement in word character(s)"),
    "OS": ("Orthography", "Shortening long vowels"),
    "OT": ("Orthography", "Confusion in Ha, Ta and Ta-Marbuta"),
    "OW": ("Orthography", "Confusion in Alif Fariqa"),
    "MI": ("Morphology", "Word inflection"),
    "MT": ("Morphology", "Verb tense"),
    "XC": ("Syntax", "Case"),
    "XF": ("Syntax", "Definiteness"),
    "XG": ("Syntax", "Gender"),
    "XM": ("Syntax", "Missing word"),
    "XN": ("Syntax", "Number"),
    "XT": ("Syntax", "Unnecessary word"),
    "SF": ("Semantics", "Conjunction error"),
    "SW": ("Semantics", "Word selection error"),
    "PC": ("Punctuation", "Punctuation confusion"),
    "PM": ("Punctuation", "Missing punctuation"),
    "PT": ("Punctuation", "Unnecessary punctuation"),
    "MG": ("Merge", "Words are merged"),
    "SP": ("Split", "Words are split"),
}
EXPECTED_CLASSES = {
    "Orthography",
    "Morphology",
    "Syntax",
    "Semantics",
    "Punctuation",
    "Merge",
    "Split",
}
EXCLUDED_TAGS = {"OO", "MO", "XO", "SO", "PO"}
CATEGORY_KEYS = {
    "id",
    "source_code",
    "parent_class",
    "published_description",
    "arabic_label",
    "source_locator",
    "label_role",
    "areta_supported",
    "synthetic_operator",
}
OPERATOR_KEYS = {"status", "rule_id", "specification", "approval"}


class RegistryValidationError(ValueError):
    """Raised when registry metadata drifts from the reviewed source audit."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RegistryValidationError(message)


def load_registry(path: Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as stream:
        payload = json.load(stream)
    _require(isinstance(payload, dict), "registry root must be a JSON object")
    return payload


def validate_registry(payload: dict) -> dict:
    """Return a corpus-free summary if the registry satisfies every guardrail."""

    _require(payload.get("schema_version") == 1, "schema_version must equal 1")
    _require(
        payload.get("registry_id") == "musahhih-areta-candidates-v1",
        "unexpected registry_id",
    )
    _require(payload.get("status") == "candidate_only", "registry is not candidate-only")

    source = payload.get("source")
    _require(isinstance(source, dict), "source metadata must be an object")
    _require(source.get("name") == "ARETA", "source name must be ARETA")
    _require(
        source.get("url") == "https://aclanthology.org/2021.conll-1.47/",
        "source URL must cite the peer-reviewed ARETA paper",
    )
    _require(source.get("locator") == "Table 1", "source locator must be Table 1")

    declared_classes = payload.get("expected_parent_classes")
    _require(isinstance(declared_classes, list), "expected_parent_classes must be a list")
    _require(set(declared_classes) == EXPECTED_CLASSES, "parent-class inventory drifted")
    _require(len(declared_classes) == len(EXPECTED_CLASSES), "parent classes contain duplicates")

    excluded = payload.get("excluded_source_tags")
    _require(isinstance(excluded, list), "excluded_source_tags must be a list")
    _require(set(excluded) == EXCLUDED_TAGS, "excluded source tags drifted")
    _require(len(excluded) == len(EXCLUDED_TAGS), "excluded source tags contain duplicates")

    categories = payload.get("categories")
    _require(isinstance(categories, list), "categories must be a list")
    _require(len(categories) == len(EXPECTED_CATEGORIES), "registry must contain exactly 26 categories")

    seen_ids: set[str] = set()
    seen_codes: set[str] = set()
    for index, category in enumerate(categories):
        _require(isinstance(category, dict), f"category {index} must be an object")
        _require(set(category) == CATEGORY_KEYS, f"category {index} has invalid fields")
        code = category.get("source_code")
        _require(isinstance(code, str), f"category {index} source_code must be a string")
        _require(code not in EXCLUDED_TAGS, f"excluded source tag {code} is active")
        _require(code in EXPECTED_CATEGORIES, f"unknown source code {code}")
        _require(code not in seen_codes, f"duplicate source code {code}")
        seen_codes.add(code)

        category_id = category.get("id")
        _require(category_id == f"areta:{code}", f"invalid stable ID for {code}")
        _require(category_id not in seen_ids, f"duplicate category ID {category_id}")
        seen_ids.add(category_id)

        expected_class, expected_description = EXPECTED_CATEGORIES[code]
        _require(category.get("parent_class") == expected_class, f"parent class drifted for {code}")
        _require(
            category.get("published_description") == expected_description,
            f"published description drifted for {code}",
        )
        _require(category.get("arabic_label") is None, f"unsourced Arabic label added for {code}")
        _require(category.get("source_locator") == "Table 1", f"source locator missing for {code}")
        _require(category.get("label_role") == "candidate_diagnostic", f"label role drifted for {code}")
        _require(category.get("areta_supported") is True, f"ARETA support flag invalid for {code}")

        operator = category.get("synthetic_operator")
        _require(isinstance(operator, dict), f"synthetic operator for {code} must be an object")
        _require(set(operator) == OPERATOR_KEYS, f"synthetic operator fields invalid for {code}")
        _require(operator.get("status") == "disabled", f"synthetic operator enabled for {code}")
        for field in ("rule_id", "specification", "approval"):
            _require(operator.get(field) is None, f"synthetic operator {field} set for {code}")

    _require(seen_codes == set(EXPECTED_CATEGORIES), "category inventory is incomplete")
    return {
        "registry_id": payload["registry_id"],
        "status": payload["status"],
        "category_count": len(categories),
        "parent_class_count": len(EXPECTED_CLASSES),
        "enabled_operator_count": 0,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_REGISTRY)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        summary = validate_registry(load_registry(args.path))
    except (OSError, json.JSONDecodeError, RegistryValidationError) as error:
        raise SystemExit(f"ERROR: {error}") from error
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
