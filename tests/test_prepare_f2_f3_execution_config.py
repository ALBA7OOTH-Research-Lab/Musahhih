import json
from pathlib import Path
import tempfile
import unittest

from scripts.f2_f3_training_utils import F2F3TrainingGateError
from scripts.prepare_f2_f3_execution_config import (
    CONFIG_FILENAME,
    ExecutionConfigError,
    build_execution_config,
    write_execution_config,
)


class PrepareF2F3ExecutionConfigTests(unittest.TestCase):
    COMMIT = "a" * 40
    APPROVAL = (
        "https://github.com/ALBA7OOTH-Research-Lab/Musahhih/"
        "issues/69#issuecomment-123456"
    )

    def test_builds_deliberate_gpu_smoke_config(self):
        config = build_execution_config(
            arm="F2-P1",
            stage="gpu-smoke",
            approved_workflow_commit=self.COMMIT,
            approval_reference=self.APPROVAL,
            confirmation="RUN_F2_F3_LONGEST_RECORD_SMOKE",
        )
        self.assertEqual(config["stage"], "gpu-smoke")
        self.assertEqual(config["prior_smoke_summary_path"], "")
        self.assertEqual(
            set(config),
            {
                "arm",
                "stage",
                "approved_workflow_commit",
                "approval_reference",
                "confirmation",
                "prior_smoke_summary_path",
            },
        )

    def test_builds_arm_specific_full_training_config(self):
        config = build_execution_config(
            arm="F3-P1",
            stage="full-training",
            approved_workflow_commit=self.COMMIT,
            approval_reference=self.APPROVAL,
            confirmation="RUN_F3_P1_TWO_EPOCH_TRAINING",
            prior_smoke_summary_path="/kaggle/input/private-smoke/summary.json",
        )
        self.assertEqual(config["stage"], "full-training")

    def test_accepts_a_dedicated_f3_issue_comment(self):
        approval = (
            "https://github.com/ALBA7OOTH-Research-Lab/Musahhih/"
            "issues/85#issuecomment-987654"
        )
        config = build_execution_config(
            arm="F3-P1",
            stage="gpu-smoke",
            approved_workflow_commit=self.COMMIT,
            approval_reference=approval,
            confirmation="RUN_F2_F3_LONGEST_RECORD_SMOKE",
        )
        self.assertEqual(config["approval_reference"], approval)

    def test_rejects_invalid_arm_stage_commit_reference_and_confirmation(self):
        valid = {
            "arm": "F2-P1",
            "stage": "gpu-smoke",
            "approved_workflow_commit": self.COMMIT,
            "approval_reference": self.APPROVAL,
            "confirmation": "RUN_F2_F3_LONGEST_RECORD_SMOKE",
        }
        cases = (
            ({"arm": "F4-P1"}, F2F3TrainingGateError),
            ({"stage": "training"}, ExecutionConfigError),
            ({"approved_workflow_commit": "abc"}, ExecutionConfigError),
            ({"approval_reference": "https://example.com"}, ExecutionConfigError),
            (
                {
                    "approval_reference": (
                        "https://github.com/ALBA7OOTH-Research-Lab/Musahhih/"
                        "issues/85#not-a-comment"
                    )
                },
                ExecutionConfigError,
            ),
            ({"confirmation": "yes"}, ExecutionConfigError),
        )
        for update, error_type in cases:
            with self.subTest(update=update):
                with self.assertRaises(error_type):
                    build_execution_config(**(valid | update))

    def test_stage_specific_prior_smoke_rules_fail_closed(self):
        with self.assertRaises(ExecutionConfigError):
            build_execution_config(
                arm="F2-P1",
                stage="gpu-smoke",
                approved_workflow_commit=self.COMMIT,
                approval_reference=self.APPROVAL,
                confirmation="RUN_F2_F3_LONGEST_RECORD_SMOKE",
                prior_smoke_summary_path="summary.json",
            )
        with self.assertRaises(ExecutionConfigError):
            build_execution_config(
                arm="F2-P1",
                stage="full-training",
                approved_workflow_commit=self.COMMIT,
                approval_reference=self.APPROVAL,
                confirmation="RUN_F2_P1_TWO_EPOCH_TRAINING",
            )

    def test_writes_utf8_json_once_under_exact_filename(self):
        config = build_execution_config(
            arm="F2-P1",
            stage="gpu-smoke",
            approved_workflow_commit=self.COMMIT,
            approval_reference=self.APPROVAL,
            confirmation="RUN_F2_F3_LONGEST_RECORD_SMOKE",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / CONFIG_FILENAME
            write_execution_config(config, path)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), config)
            with self.assertRaises(ExecutionConfigError):
                write_execution_config(config, path)
            with self.assertRaises(ExecutionConfigError):
                write_execution_config(config, Path(directory) / "wrong.json")


if __name__ == "__main__":
    unittest.main()
