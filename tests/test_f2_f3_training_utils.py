import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.f2_f3_training_utils import (
    F2F3TrainingGateError,
    FULL_TRAINING_CONFIRMATION,
    GPU_SMOKE_CONFIRMATION,
    P100_CORE_STACK,
    P100_HEAVY_STACK,
    locate_private_input,
    p100_stack_report,
    require_execution_approval,
    require_full_training_confirmation,
    require_smoke_confirmation,
    run_id,
    validate_private_records,
    validate_p100_core_stack,
)


def conversation(index, source, split="train"):
    return {
        "record_id": f"{source}-{index}",
        "prompt": [{"role": "user", "content": "PRIVATE INPUT"}],
        "completion": [{"role": "assistant", "content": "PRIVATE OUTPUT"}],
        "source": source,
        "split": split,
    }


class F2F3TrainingUtilsTests(unittest.TestCase):
    APPROVAL = (
        "https://github.com/ALBA7OOTH-Research-Lab/Musahhih/"
        "issues/69#issuecomment-1"
    )

    def write_rows(self, rows):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "records.jsonl"
        path.write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
        )
        return path

    def test_private_input_locator_supports_current_nested_kaggle_mount(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            kaggle_root = root / "kaggle" / "input"
            nested = (
                kaggle_root
                / "datasets"
                / "univverssal"
                / "musahhih-f2-f3-private-records"
            )
            nested.mkdir(parents=True)
            expected = nested / "f2_train_records.jsonl"
            expected.touch()

            located = locate_private_input(
                expected.name,
                kaggle_root,
                root / "data" / "processed" / "f2_f3_training_records",
            )

            self.assertEqual(located, expected)

    def test_private_input_locator_falls_back_locally_and_rejects_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            kaggle_root = root / "kaggle" / "input"
            local_root = root / "data" / "processed" / "f2_f3_training_records"
            local_root.mkdir(parents=True)
            expected = local_root / "common_dev_records.jsonl"
            expected.touch()
            self.assertEqual(
                locate_private_input(expected.name, kaggle_root, local_root),
                expected,
            )

            first = kaggle_root / "datasets" / "owner" / "one"
            second = kaggle_root / "datasets" / "owner" / "two"
            first.mkdir(parents=True)
            second.mkdir(parents=True)
            (first / expected.name).touch()
            (second / expected.name).touch()
            with self.assertRaisesRegex(
                F2F3TrainingGateError, "Expected exactly one private"
            ):
                locate_private_input(expected.name, kaggle_root, local_root)

    def test_private_f3_validation_reports_only_aggregate_provenance(self):
        rows = [
            conversation(1, "QALB-2014-L1"),
            conversation(2, "Tibyan-corpus"),
        ]
        path = self.write_rows(rows)
        import hashlib

        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        with (
            patch("scripts.f2_f3_training_utils.TRAIN_RECORDS", 2),
            patch.dict(
                "scripts.f2_f3_training_utils.EXPECTED_RECORD_SHA256",
                {"F3-P1": digest},
            ),
        ):
            summary = validate_private_records(path, "F3-P1")
        self.assertEqual(
            summary["source_counts"],
            {"QALB-2014-L1": 1, "Tibyan-corpus": 1},
        )
        self.assertNotIn("PRIVATE", json.dumps(summary))

    def test_p100_stack_report_accepts_exact_or_cuda_tagged_versions(self):
        self.assertEqual(
            P100_CORE_STACK,
            {
                "torch": "2.6.0",
                "torchvision": "0.21.0",
                "xformers": "0.0.29.post3",
                "torchao": "0.16.0",
                "numpy": "2.0.2",
            },
        )
        installed = dict(P100_CORE_STACK)
        installed["torch"] = "2.6.0+cu124"
        installed["torchvision"] = "0.21.0+cu124"

        summary = p100_stack_report(installed)

        self.assertTrue(summary["compatible"])
        self.assertEqual(summary["installed"], installed)

    def test_p100_stack_report_supports_heavy_preinstall_decision(self):
        installed = dict(P100_CORE_STACK)
        installed["xformers"] = "0.0.34"

        report = p100_stack_report(installed, P100_HEAVY_STACK)

        self.assertTrue(report["compatible"])
        self.assertNotIn("xformers", report["installed"])

    def test_p100_core_stack_fails_closed_after_setup_on_mismatch(self):
        installed = dict(P100_CORE_STACK)
        installed.pop("xformers")
        installed["torch"] = "2.7.0"

        with self.assertRaisesRegex(
            F2F3TrainingGateError, "core stack mismatch after setup"
        ):
            validate_p100_core_stack(installed)

    def test_smoke_requires_exact_confirmation(self):
        with self.assertRaisesRegex(F2F3TrainingGateError, "confirmation"):
            require_smoke_confirmation("yes", "a" * 40, "a" * 40, self.APPROVAL)
        with self.assertRaisesRegex(F2F3TrainingGateError, "commit"):
            require_smoke_confirmation(
                GPU_SMOKE_CONFIRMATION, "a" * 40, "b" * 40, self.APPROVAL
            )
        require_smoke_confirmation(
            GPU_SMOKE_CONFIRMATION, "a" * 40, "a" * 40, self.APPROVAL
        )

    def test_execution_approval_accepts_any_musahhih_issue_comment(self):
        commit = "a" * 40
        require_execution_approval(
            commit,
            commit,
            "https://github.com/ALBA7OOTH-Research-Lab/Musahhih/"
            "issues/85#issuecomment-123456",
        )

    def test_execution_approval_rejects_non_comment_and_lookalike_urls(self):
        commit = "a" * 40
        repository = "https://github.com/ALBA7OOTH-Research-Lab/Musahhih"
        invalid_references = (
            f"{repository}/issues/85",
            f"{repository}/pull/85#issuecomment-1",
            "https://github.com/another/Musahhih/issues/85#issuecomment-1",
            f"{repository}/issues/0#issuecomment-1",
            f"{repository}/issues/85#issuecomment-0",
            f"{repository}/issues/85#issuecomment-1?x=1",
        )
        for reference in invalid_references:
            with self.subTest(reference=reference):
                with self.assertRaisesRegex(
                    F2F3TrainingGateError, "issue-comment URL"
                ):
                    require_execution_approval(commit, commit, reference)

    def test_full_training_requires_matching_arm_commit_and_issue_approval(self):
        arm = "F2-P1"
        commit = "a" * 40
        smoke = {"passed": True, "arm": arm, "workflow_commit": commit}
        require_full_training_confirmation(
            arm,
            FULL_TRAINING_CONFIRMATION[arm],
            smoke,
            commit,
            commit,
            "https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/69#issuecomment-1",
        )
        with self.assertRaisesRegex(F2F3TrainingGateError, "commit"):
            require_full_training_confirmation(
                arm,
                FULL_TRAINING_CONFIRMATION[arm],
                smoke,
                commit,
                "b" * 40,
                "https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/69#issuecomment-1",
            )

    def test_run_ids_are_arm_and_stage_specific(self):
        self.assertNotEqual(run_id("F2-P1", "smoke"), run_id("F3-P1", "smoke"))
        self.assertNotEqual(
            run_id("F2-P1", "smoke"), run_id("F2-P1", "training")
        )


if __name__ == "__main__":
    unittest.main()
