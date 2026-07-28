import contextlib
import io
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import check_b1_b2_gpu_preflight


class B1B2GpuPreflightTests(unittest.TestCase):
    def test_cli_emits_only_aggregate_runtime_metadata(self):
        output = io.StringIO()
        with (
            patch(
                "scripts.check_b1_b2_gpu_preflight.require_single_p100_runtime",
                return_value={
                    "cuda_available": True,
                    "cuda_device_count": 1,
                    "cuda_operation_passed": True,
                    "device_name": "Tesla P100-PCIE-16GB",
                    "require_p100": True,
                },
            ),
            patch(
                "scripts.check_b1_b2_gpu_preflight.require_proven_p100_stack",
                return_value={
                    "compatible": True,
                    "cuda_runtime": "12.4",
                    "installed": {},
                    "mismatches": {},
                    "report_only_versions": {},
                    "required": {},
                },
            ),
            patch("scripts.check_b1_b2_gpu_preflight.importlib.import_module"),
            patch.dict(
                sys.modules,
                {"torch": SimpleNamespace()},
            ),
            contextlib.redirect_stdout(output),
        ):
            check_b1_b2_gpu_preflight.main()
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["stage"], "b1_b2_gpu_preflight")
        self.assertTrue(payload["passed"])
        self.assertTrue(payload["cuda_operation_passed"])
        self.assertTrue(payload["inference_imports_passed"])
        self.assertTrue(payload["proven_stack"]["compatible"])
        self.assertNotIn("record_id", payload)
        self.assertNotIn("prompt", payload)

    def test_preflight_source_does_not_depend_on_nvidia_smi(self):
        source = Path(check_b1_b2_gpu_preflight.__file__).read_text(
            encoding="utf-8"
        )
        self.assertNotIn("nvidia-smi", source)
        self.assertNotIn("subprocess", source)


if __name__ == "__main__":
    unittest.main()
