import json
from pathlib import Path
import tempfile
import unittest

from scripts.prepare_b2_final_kaggle_kernel import (
    KernelPreparationError,
    build_metadata,
    build_wrapper,
    write_kernel_package,
)


class PrepareB2FinalKaggleKernelTests(unittest.TestCase):
    COMMIT = "a" * 40
    APPROVAL = (
        "https://github.com/ALBA7OOTH-Research-Lab/Musahhih/"
        "issues/141#issuecomment-123456"
    )
    DATASET = "thgh15/musahhih-b1-final-private-8710263-r01"

    def test_wrapper_freezes_b2_and_accesses_only_input_after_preflight(self):
        wrapper = build_wrapper(
            approved_commit=self.COMMIT,
            approval_reference=self.APPROVAL,
            dataset_source=self.DATASET,
        )
        self.assertIn(f'APPROVED_COMMIT = "{self.COMMIT}"', wrapper)
        self.assertIn('"B2-P1"', wrapper)
        self.assertIn(
            'EXPECTED_INPUT_SHA256 = "acb3cfd204b35d5415532fbd32a4a523'
            '1b553fae329ab8f48e8454609e10279b"',
            wrapper,
        )
        self.assertIn('"RUN_B1_B2_NAHW_FINAL_TIMEOUT_SAFE"', wrapper)
        self.assertNotIn("--bundle", wrapper)
        self.assertNotIn("EXPECTED_BUNDLE", wrapper)
        self.assertNotIn("--temperature", wrapper)
        self.assertIn(
            'Path("/kaggle/input").rglob("nahw_gec_test.jsonl")',
            wrapper,
        )
        self.assertIn("if len(input_candidates) != 1:", wrapper)
        self.assertNotIn(
            '/ "musahhih-b1-final-private-8710263-r01"',
            wrapper,
        )
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
            kernel_id="thgh15/musahhih-b2-final-deadbee-r01",
            dataset_source=self.DATASET,
        )
        self.assertTrue(metadata["is_private"])
        self.assertTrue(metadata["enable_gpu"])
        self.assertEqual(metadata["machine_shape"], "NvidiaTeslaP100")
        self.assertEqual(metadata["dataset_sources"], [self.DATASET])
        self.assertEqual(metadata["model_sources"], [])

    def test_rejects_invalid_activation_values(self):
        with self.assertRaises(KernelPreparationError):
            build_wrapper(
                approved_commit="abc",
                approval_reference=self.APPROVAL,
                dataset_source=self.DATASET,
            )
        with self.assertRaises(KernelPreparationError):
            build_wrapper(
                approved_commit=self.COMMIT,
                approval_reference="https://example.com",
                dataset_source=self.DATASET,
            )
        with self.assertRaises(KernelPreparationError):
            build_wrapper(
                approved_commit=self.COMMIT,
                approval_reference=self.APPROVAL,
                dataset_source="bad",
            )
        with self.assertRaises(KernelPreparationError):
            build_metadata(kernel_id="bad", dataset_source=self.DATASET)

    def test_writes_once_and_generated_wrapper_compiles(self):
        wrapper = build_wrapper(
            approved_commit=self.COMMIT,
            approval_reference=self.APPROVAL,
            dataset_source=self.DATASET,
        )
        metadata = build_metadata(
            kernel_id="thgh15/musahhih-b2-final-deadbee-r01",
            dataset_source=self.DATASET,
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
