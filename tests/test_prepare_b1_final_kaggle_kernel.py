import json
from pathlib import Path
import tempfile
import unittest

from scripts.prepare_b1_final_kaggle_kernel import (
    KernelPreparationError,
    build_metadata,
    build_wrapper,
    write_kernel_package,
)


class PrepareB1FinalKaggleKernelTests(unittest.TestCase):
    COMMIT = "a" * 40
    APPROVAL = (
        "https://github.com/ALBA7OOTH-Research-Lab/Musahhih/"
        "issues/137#issuecomment-123456"
    )

    def test_wrapper_freezes_identity_and_orders_private_access_after_preflight(self):
        wrapper = build_wrapper(
            approved_commit=self.COMMIT,
            approval_reference=self.APPROVAL,
        )
        self.assertIn(f'APPROVED_COMMIT = "{self.COMMIT}"', wrapper)
        self.assertIn(
            'EXPECTED_INPUT_SHA256 = "acb3cfd204b35d5415532fbd32a4a523'
            '1b553fae329ab8f48e8454609e10279b"',
            wrapper,
        )
        self.assertIn(
            'EXPECTED_BUNDLE_SHA256 = "760674f0d6cc85c48b2be18d175b87e'
            '2025cd3d01fde31a6e25afaa08f9fc11a"',
            wrapper,
        )
        self.assertIn('"RUN_B1_B2_NAHW_FINAL_TIMEOUT_SAFE"', wrapper)
        self.assertNotIn("--temperature", wrapper)
        self.assertLess(
            wrapper.index("scripts.check_b1_b2_restored_p100"),
            wrapper.index('Path("/kaggle/input")'),
        )
        self.assertLess(
            wrapper.index('Path("/kaggle/input")'),
            wrapper.index("scripts.run_prompt_baseline"),
        )
        self.assertTrue(
            wrapper.startswith(
                "import time\n\nKERNEL_START_EPOCH_SECONDS = time.time()\n"
            )
        )

    def test_metadata_is_private_p100_with_one_data_source(self):
        metadata = build_metadata(
            kernel_id="thgh15/musahhih-b1-final-deadbee-r04",
            dataset_source="thgh15/musahhih-b1-final-private-8710263-r01",
        )
        self.assertTrue(metadata["is_private"])
        self.assertTrue(metadata["enable_gpu"])
        self.assertEqual(metadata["machine_shape"], "NvidiaTeslaP100")
        self.assertEqual(len(metadata["dataset_sources"]), 1)
        self.assertEqual(metadata["model_sources"], [])

    def test_rejects_invalid_commit_reference_and_slugs(self):
        with self.assertRaises(KernelPreparationError):
            build_wrapper(
                approved_commit="abc",
                approval_reference=self.APPROVAL,
            )
        with self.assertRaises(KernelPreparationError):
            build_wrapper(
                approved_commit=self.COMMIT,
                approval_reference="https://example.com",
            )
        with self.assertRaises(KernelPreparationError):
            build_metadata(kernel_id="bad", dataset_source="owner/source")
        with self.assertRaises(KernelPreparationError):
            build_metadata(kernel_id="owner/kernel", dataset_source="bad")

    def test_writes_once_without_execution(self):
        wrapper = build_wrapper(
            approved_commit=self.COMMIT,
            approval_reference=self.APPROVAL,
        )
        metadata = build_metadata(
            kernel_id="thgh15/musahhih-b1-final-deadbee-r04",
            dataset_source="thgh15/musahhih-b1-final-private-8710263-r01",
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "kernel"
            wrapper_path, metadata_path = write_kernel_package(
                output_dir=output,
                wrapper=wrapper,
                metadata=metadata,
            )
            compile(wrapper_path.read_text(encoding="utf-8"), str(wrapper_path), "exec")
            self.assertEqual(
                json.loads(metadata_path.read_text(encoding="utf-8")),
                metadata,
            )
            with self.assertRaises(KernelPreparationError):
                write_kernel_package(
                    output_dir=output,
                    wrapper=wrapper,
                    metadata=metadata,
                )


if __name__ == "__main__":
    unittest.main()
