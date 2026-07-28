import contextlib
import io
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import check_b1_b2_private_input
from scripts.run_prompt_baseline import RunSafetyError


class B1B2PrivateInputTests(unittest.TestCase):
    def test_validate_emits_only_aggregate_contract_evidence(self):
        records = [
            SimpleNamespace(record_id="r1"),
            SimpleNamespace(record_id="r2"),
        ]
        with (
            patch(
                "scripts.check_b1_b2_private_input.validate_private_path",
                side_effect=lambda path, **kwargs: path,
            ),
            patch(
                "scripts.check_b1_b2_private_input.sha256_file",
                return_value=check_b1_b2_private_input.FINAL_INPUT_SHA256,
            ),
            patch(
                "scripts.check_b1_b2_private_input.load_prompt_records",
                return_value=records,
            ),
        ):
            report = check_b1_b2_private_input.validate(Path("private.jsonl"))

        self.assertEqual(report["record_count"], 2)
        self.assertTrue(report["unique_record_ids"])
        self.assertNotIn("passage", report)
        self.assertNotIn("prompt", report)

    def test_validate_rejects_nonfrozen_hash_before_schema_load(self):
        with (
            patch(
                "scripts.check_b1_b2_private_input.validate_private_path",
                side_effect=lambda path, **kwargs: path,
            ),
            patch(
                "scripts.check_b1_b2_private_input.sha256_file",
                return_value="0" * 64,
            ),
            patch(
                "scripts.check_b1_b2_private_input.load_prompt_records"
            ) as loader,
        ):
            with self.assertRaisesRegex(RunSafetyError, "SHA-256"):
                check_b1_b2_private_input.validate(Path("private.jsonl"))
        loader.assert_not_called()

    def test_cli_prints_json_only(self):
        output = io.StringIO()
        report = {
            "input_sha256": "a" * 64,
            "passed": True,
            "record_count": 511,
            "stage": "b1_b2_private_input_contract",
            "unique_record_ids": True,
        }
        with (
            patch(
                "scripts.check_b1_b2_private_input.validate",
                return_value=report,
            ),
            patch(
                "scripts.check_b1_b2_private_input.argparse.ArgumentParser.parse_args",
                return_value=SimpleNamespace(input=Path("private.jsonl")),
            ),
            contextlib.redirect_stdout(output),
        ):
            check_b1_b2_private_input.main()

        self.assertEqual(json.loads(output.getvalue()), report)


if __name__ == "__main__":
    unittest.main()
