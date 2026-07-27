import contextlib
import importlib.metadata
import io
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import check_b1_b2_kaggle_runtime


class B1B2KaggleRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.versions = {
            name: f"{name}-version"
            for name in check_b1_b2_kaggle_runtime.PACKAGE_NAMES
        }

    def version_getter(self, name):
        value = self.versions.get(name)
        if value is None:
            raise importlib.metadata.PackageNotFoundError(name)
        return value

    @staticmethod
    def fake_torch(*, available=True, count=1, name="Tesla P100-PCIE-16GB"):
        return SimpleNamespace(
            version=SimpleNamespace(cuda="12.8"),
            cuda=SimpleNamespace(
                is_available=lambda: available,
                device_count=lambda: count,
                get_device_name=lambda index: name,
            ),
        )

    def test_ready_report_is_aggregate_only(self):
        report = check_b1_b2_kaggle_runtime.runtime_report(
            self.fake_torch(),
            version_getter=self.version_getter,
        )
        self.assertTrue(report["probe_complete"])
        self.assertTrue(report["ready"])
        self.assertEqual(report["failures"], [])
        self.assertEqual(report["device_name"], "Tesla P100-PCIE-16GB")
        self.assertFalse(report["network_access_attempted"])
        self.assertFalse(report["private_input_accessed"])
        self.assertFalse(report["model_loaded"])
        rendered = json.dumps(report)
        for forbidden in ("prompt", "passage", "correction", "response"):
            self.assertNotIn(forbidden, rendered)

    def test_report_fails_closed_for_gpu_and_missing_packages(self):
        self.versions["unsloth"] = None
        report = check_b1_b2_kaggle_runtime.runtime_report(
            self.fake_torch(name="Tesla T4"),
            version_getter=self.version_getter,
        )
        self.assertFalse(report["ready"])
        self.assertEqual(
            report["failures"],
            ["gpu_is_not_p100", "required_inference_packages_missing"],
        )
        self.assertEqual(report["missing_required_packages"], ["unsloth"])

    def test_cli_treats_not_ready_as_a_completed_probe(self):
        output = io.StringIO()
        with (
            patch(
                "scripts.check_b1_b2_kaggle_runtime.runtime_report",
                return_value={
                    "stage": "b1_b2_kaggle_runtime_probe",
                    "probe_complete": True,
                    "ready": False,
                },
            ),
            contextlib.redirect_stdout(output),
        ):
            check_b1_b2_kaggle_runtime.main()
        payload = json.loads(output.getvalue())
        self.assertTrue(payload["probe_complete"])
        self.assertFalse(payload["ready"])

    def test_probe_source_has_no_network_or_research_access(self):
        source = Path(check_b1_b2_kaggle_runtime.__file__).read_text(
            encoding="utf-8"
        )
        for forbidden in (
            "subprocess",
            "requests",
            "urllib",
            "socket",
            "pip install",
            "git clone",
            "from_pretrained",
            "nahw",
            "qalb",
        ):
            self.assertNotIn(forbidden, source.lower())


if __name__ == "__main__":
    unittest.main()
