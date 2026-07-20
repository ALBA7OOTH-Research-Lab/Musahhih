import json
from pathlib import Path
import tempfile
import unittest

from scripts.prepare_f2_dev_smoke_execution_config import (
    CONFIG_FILENAME,
    CONFIRMATION,
    F2DevSmokeConfigError,
    build_execution_config,
    write_execution_config,
)


class PrepareF2DevSmokeExecutionConfigTests(unittest.TestCase):
    COMMIT = "a" * 40
    APPROVAL = (
        "https://github.com/ALBA7OOTH-Research-Lab/Musahhih/"
        "issues/82#issuecomment-123456"
    )

    def test_builds_only_frozen_f2_development_smoke(self):
        config = build_execution_config(
            approved_workflow_commit=self.COMMIT,
            approval_reference=self.APPROVAL,
            confirmation=CONFIRMATION,
        )
        self.assertEqual(
            config,
            {
                "stage": "private-dev-smoke",
                "approved_workflow_commit": self.COMMIT,
                "approval_reference": self.APPROVAL,
                "confirmation": CONFIRMATION,
            },
        )

    def test_rejects_invalid_commit_reference_and_confirmation(self):
        valid = {
            "approved_workflow_commit": self.COMMIT,
            "approval_reference": self.APPROVAL,
            "confirmation": CONFIRMATION,
        }
        for update in (
            {"approved_workflow_commit": "abc"},
            {"approval_reference": "https://example.com"},
            {"confirmation": "yes"},
        ):
            with self.subTest(update=update):
                with self.assertRaises(F2DevSmokeConfigError):
                    build_execution_config(**(valid | update))

    def test_writes_utf8_json_once_under_exact_filename(self):
        config = build_execution_config(
            approved_workflow_commit=self.COMMIT,
            approval_reference=self.APPROVAL,
            confirmation=CONFIRMATION,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / CONFIG_FILENAME
            write_execution_config(config, path)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), config)
            with self.assertRaises(F2DevSmokeConfigError):
                write_execution_config(config, path)
            with self.assertRaises(F2DevSmokeConfigError):
                write_execution_config(config, Path(directory) / "wrong.json")


if __name__ == "__main__":
    unittest.main()
