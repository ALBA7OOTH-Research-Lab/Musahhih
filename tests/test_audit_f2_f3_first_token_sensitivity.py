import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.audit_f2_f3_first_token_sensitivity import (
    SensitivityAuditError,
    audit_pair,
    write_new_json,
)


def write_rows(path: Path, rows: list[dict]) -> str:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def row(record_id: str, parsed: str, gold: str) -> dict:
    warnings = ["multiple_words"] if len(parsed.split()) > 1 else []
    return {
        "record_id": record_id,
        "gold_correction": gold,
        "parsed_correction": parsed,
        "exact_match": parsed == gold,
        "parsing_warnings": warnings,
    }


class FirstTokenSensitivityTests(unittest.TestCase):
    def _fixture(self, root: Path):
        f2_rows = [
            row("r1", "correct", "correct"),
            row("r2", "target explanation", "target"),
            row("r3", "wrong explanation", "target"),
        ]
        f3_rows = [
            row("r1", "correct", "correct"),
            row("r2", "target", "target"),
            row("r3", "target explanation", "target"),
        ]
        f2_path = root / "f2.jsonl"
        f3_path = root / "f3.jsonl"
        f2_hash = write_rows(f2_path, f2_rows)
        f3_hash = write_rows(f3_path, f3_rows)
        expected = {
            "F2-P1": {"sha256": f2_hash, "correct": 1, "multiple_words": 2},
            "F3-P1": {"sha256": f3_hash, "correct": 2, "multiple_words": 1},
        }
        return f2_path, f3_path, expected

    def test_symmetric_counterfactual_reports_only_aggregates(self):
        with tempfile.TemporaryDirectory() as directory:
            f2_path, f3_path, expected = self._fixture(Path(directory))
            result = audit_pair(f2_path, f3_path, expected=expected, expected_rows=3)
        self.assertEqual(result["arms"]["F2-P1"]["rescued_by_first_token"], 1)
        self.assertEqual(result["arms"]["F2-P1"]["counterfactual_correct"], 2)
        self.assertEqual(result["arms"]["F3-P1"]["rescued_by_first_token"], 1)
        self.assertEqual(result["arms"]["F3-P1"]["counterfactual_correct"], 3)
        serialized = json.dumps(result)
        for private_value in ("r1", "r2", "r3", "target", "explanation"):
            self.assertNotIn(private_value, serialized)

    def test_hash_mismatch_fails_before_analysis(self):
        with tempfile.TemporaryDirectory() as directory:
            f2_path, f3_path, expected = self._fixture(Path(directory))
            expected["F2-P1"]["sha256"] = "0" * 64
            with self.assertRaisesRegex(SensitivityAuditError, "SHA-256 mismatch"):
                audit_pair(f2_path, f3_path, expected=expected, expected_rows=3)

    def test_alignment_mismatch_is_rejected_without_identifier(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            f2_path, f3_path, expected = self._fixture(root)
            f3_rows = [
                row("r1", "correct", "correct"),
                row("different-private-id", "target", "target"),
                row("r3", "target explanation", "target"),
            ]
            expected["F3-P1"]["sha256"] = write_rows(f3_path, f3_rows)
            with self.assertRaises(SensitivityAuditError) as caught:
                audit_pair(f2_path, f3_path, expected=expected, expected_rows=3)
        self.assertNotIn("different-private-id", str(caught.exception))

    def test_warning_contract_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            f2_path, f3_path, expected = self._fixture(root)
            rows = [
                row("r1", "correct", "correct"),
                row("r2", "target explanation", "target"),
                row("r3", "wrong explanation", "target"),
            ]
            rows[1]["parsing_warnings"] = []
            expected["F2-P1"]["sha256"] = write_rows(f2_path, rows)
            with self.assertRaisesRegex(SensitivityAuditError, "warning mismatch"):
                audit_pair(f2_path, f3_path, expected=expected, expected_rows=3)

    def test_output_is_write_once(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "summary.json"
            write_new_json(output, {"contains_corpus_text": False})
            with self.assertRaises(FileExistsError):
                write_new_json(output, {"contains_corpus_text": False})


if __name__ == "__main__":
    unittest.main()
