import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts.prepare_f2_f3_safety_kaggle_dataset import (
    CONFIRMATION,
    DatasetPreparationError,
    ROOT,
    require_preparation_authorization,
    validate_output_dir,
    write_dataset_bundle,
)
from scripts.prepare_f2_f3_safety_kaggle_kernel import (
    KernelPreparationError,
    build_metadata,
)


class F2F3SafetyDatasetTests(unittest.TestCase):
    def test_disabled_cli_does_not_access_private_artifacts(self):
        command = [
            sys.executable,
            "-m",
            "scripts.prepare_f2_f3_safety_kaggle_dataset",
            "--dataset-id",
            "owner/private-artifacts",
            "--output-dir",
            "missing-output",
            "--overcorrection-input",
            "missing-over",
            "--capability-input",
            "missing-capability",
            "--f2-adapter",
            "missing-f2",
            "--f3-adapter",
            "missing-f3",
            "--b0-overcorrection-predictions",
            "missing-b0-over",
            "--f1-overcorrection-predictions",
            "missing-f1-over",
            "--b0-capability-predictions",
            "missing-b0-cap",
            "--f1-capability-predictions",
            "missing-f1-cap",
        ]
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "disabled")
        self.assertFalse(payload["private_artifact_accessed"])
        self.assertFalse(payload["bundle_created"])
        self.assertFalse(payload["upload_executed"])

    def test_preparation_authorization_is_issue_200_and_commit_exact(self):
        completed = subprocess.CompletedProcess(
            args=["git"], returncode=0, stdout="a" * 40 + "\n", stderr=""
        )
        reference = (
            "https://github.com/ALBA7OOTH-Research-Lab/"
            "Musahhih/issues/200#issuecomment-123"
        )
        with patch(
            "scripts.prepare_f2_f3_safety_kaggle_dataset.subprocess.run",
            return_value=completed,
        ):
            require_preparation_authorization(
                CONFIRMATION,
                "a" * 40,
                reference,
            )
        with self.assertRaisesRegex(DatasetPreparationError, "confirmation"):
            require_preparation_authorization("wrong", "a" * 40, reference)

    def test_bundle_is_minimal_private_write_once_and_not_uploaded(self):
        outputs = ROOT / "outputs"
        outputs.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=outputs) as directory:
            root = Path(directory)
            source_a = root / "source-a"
            source_b = root / "source-b"
            source_a.write_bytes(b"private-a")
            source_b.write_bytes(b"private-b")
            target = root / "bundle"
            manifest = write_dataset_bundle(
                output_dir=target,
                dataset_id="owner/private-artifacts",
                sources={
                    "inputs/a.bin": source_a,
                    "adapter/b.bin": source_b,
                },
            )
            self.assertEqual(len(manifest["files"]), 2)
            self.assertTrue(manifest["private_upload_required"])
            self.assertFalse(manifest["upload_executed"])
            metadata = json.loads(
                (target / "dataset-metadata.json").read_text(encoding="utf-8")
            )
            self.assertEqual(metadata["id"], "owner/private-artifacts")
            with self.assertRaisesRegex(DatasetPreparationError, "overwrite"):
                write_dataset_bundle(
                    output_dir=target,
                    dataset_id="owner/private-artifacts",
                    sources={"inputs/a.bin": source_a},
                )

    def test_bundle_output_is_confined_to_ignored_outputs(self):
        with self.assertRaisesRegex(DatasetPreparationError, "ignored outputs"):
            validate_output_dir(ROOT / "results" / "private-bundle")

    def test_kernel_metadata_accepts_one_combined_private_dataset(self):
        metadata = build_metadata(
            kernel_id="thgh15/f2-f3-safety-r01",
            artifact_dataset_sources=["thgh15/f2-f3-private-artifacts"],
        )
        self.assertEqual(
            metadata["dataset_sources"],
            ["thgh15/f2-f3-private-artifacts"],
        )
        self.assertEqual(metadata["kernel_sources"], [])
        with self.assertRaisesRegex(KernelPreparationError, "mutually exclusive"):
            build_metadata(
                kernel_id="thgh15/f2-f3-safety-r01",
                artifact_dataset_sources=["thgh15/f2-f3-private-artifacts"],
                safety_dataset_source="owner/legacy-inputs",
                f1_safety_kernel_source="owner/f1",
                f2_kernel_source="owner/f2",
                f3_kernel_source="owner/f3",
            )

    def test_dataset_preparer_contains_no_upload_or_execution_path(self):
        source = (
            ROOT / "scripts" / "prepare_f2_f3_safety_kaggle_dataset.py"
        ).read_text(encoding="utf-8")
        for forbidden in (
            "kaggle datasets create",
            "FastModel.from_pretrained",
            "model.generate",
            "SFTTrainer",
            "nahw_gec_test.jsonl",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
