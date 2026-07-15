import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.validate_error_registry import (
    DEFAULT_REGISTRY,
    RegistryValidationError,
    load_registry,
    validate_registry,
)


class ErrorRegistryValidationTests(unittest.TestCase):
    def setUp(self):
        self.registry = load_registry(DEFAULT_REGISTRY)

    def test_reviewed_registry_is_valid_and_has_no_enabled_operators(self):
        summary = validate_registry(self.registry)
        self.assertEqual(summary["category_count"], 26)
        self.assertEqual(summary["parent_class_count"], 7)
        self.assertEqual(summary["enabled_operator_count"], 0)

    def test_rejects_source_taxonomy_drift(self):
        mutations = []

        wrong_description = copy.deepcopy(self.registry)
        wrong_description["categories"][0]["published_description"] = "invented"
        mutations.append(wrong_description)

        wrong_class = copy.deepcopy(self.registry)
        wrong_class["categories"][0]["parent_class"] = "Syntax"
        mutations.append(wrong_class)

        wrong_citation = copy.deepcopy(self.registry)
        wrong_citation["source"]["url"] = "https://example.invalid"
        mutations.append(wrong_citation)

        for payload in mutations:
            with self.subTest(payload=payload):
                with self.assertRaises(RegistryValidationError):
                    validate_registry(payload)

    def test_rejects_excluded_duplicate_and_unknown_tags(self):
        for code in ("OO", "ZZ"):
            payload = copy.deepcopy(self.registry)
            payload["categories"][0]["source_code"] = code
            payload["categories"][0]["id"] = f"areta:{code}"
            with self.subTest(code=code):
                with self.assertRaises(RegistryValidationError):
                    validate_registry(payload)

        duplicate = copy.deepcopy(self.registry)
        duplicate["categories"][1] = copy.deepcopy(duplicate["categories"][0])
        with self.assertRaisesRegex(RegistryValidationError, "duplicate"):
            validate_registry(duplicate)

    def test_rejects_unsourced_arabic_label(self):
        payload = copy.deepcopy(self.registry)
        payload["categories"][0]["arabic_label"] = "unsourced label"
        with self.assertRaisesRegex(RegistryValidationError, "Arabic label"):
            validate_registry(payload)

    def test_rejects_any_operator_activation_or_specification(self):
        mutations = []
        enabled = copy.deepcopy(self.registry)
        enabled["categories"][0]["synthetic_operator"]["status"] = "enabled"
        mutations.append(enabled)

        specified = copy.deepcopy(self.registry)
        specified["categories"][0]["synthetic_operator"]["rule_id"] = "rule-1"
        mutations.append(specified)

        approved = copy.deepcopy(self.registry)
        approved["categories"][0]["synthetic_operator"]["approval"] = "PR-unknown"
        mutations.append(approved)

        for payload in mutations:
            with self.subTest(payload=payload):
                with self.assertRaises(RegistryValidationError):
                    validate_registry(payload)

    def test_cli_accepts_registry_and_rejects_invalid_copy(self):
        accepted = subprocess.run(
            [sys.executable, "scripts/validate_error_registry.py"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertIn('"enabled_operator_count": 0', accepted.stdout)

        invalid = copy.deepcopy(self.registry)
        invalid["categories"][0]["synthetic_operator"]["status"] = "enabled"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalid.json"
            path.write_text(json.dumps(invalid), encoding="utf-8")
            rejected = subprocess.run(
                [sys.executable, "scripts/validate_error_registry.py", str(path)],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("synthetic operator enabled", rejected.stderr)


if __name__ == "__main__":
    unittest.main()
