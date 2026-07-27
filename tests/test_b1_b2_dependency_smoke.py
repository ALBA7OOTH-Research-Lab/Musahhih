import importlib.metadata
import json
import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts import check_b1_b2_dependency_smoke


class B1B2DependencySmokeTests(unittest.TestCase):
    def setUp(self):
        self.versions = {
            "torch": "2.10.0+cu128",
            "torchvision": "0.25.0+cu128",
            "numpy": "2.0.2",
            "unsloth": "2026.7.2",
            "unsloth_zoo": "2026.7.2",
            "bitsandbytes": "0.49.2",
            "transformers": "4.56.2",
            "trl": "0.23.0",
            "xformers": "0.0.34",
            "accelerate": "1.13.0",
            "peft": "0.19.1",
        }
        self.torch = SimpleNamespace(
            version=SimpleNamespace(cuda="12.8"),
            cuda=SimpleNamespace(
                is_available=lambda: True,
                device_count=lambda: 1,
                get_device_name=lambda index: "Tesla P100-PCIE-16GB",
            ),
        )

    def version_getter(self, name):
        value = self.versions.get(name)
        if value is None:
            raise importlib.metadata.PackageNotFoundError(name)
        return value

    @staticmethod
    def import_module(name):
        if name == "unsloth":
            return SimpleNamespace(FastModel=object())
        return SimpleNamespace()

    def test_success_preserves_base_and_uses_only_pypi(self):
        commands = []
        observed_constraints = []

        def run_command(command, **kwargs):
            commands.append(command)
            if "install" in command:
                constraint_index = command.index("--constraint") + 1
                observed_constraints.extend(
                    Path(command[constraint_index])
                    .read_text(encoding="utf-8")
                    .splitlines()
                )
            return subprocess.CompletedProcess(command, 0, "ok", "")

        report = check_b1_b2_dependency_smoke.run_dependency_smoke(
            torch_module=self.torch,
            version_getter=self.version_getter,
            import_module=self.import_module,
            run_command=run_command,
        )
        self.assertTrue(report["probe_complete"])
        self.assertTrue(report["ready"])
        self.assertEqual(report["failures"], [])
        self.assertEqual(report["base_before"], report["base_after"])
        install = commands[0]
        self.assertIn("https://pypi.org/simple", install)
        self.assertNotIn("download.pytorch.org", " ".join(install))
        self.assertIn("unsloth[cu128-torch2100]==2026.7.2", install)
        self.assertEqual(
            tuple(observed_constraints),
            check_b1_b2_dependency_smoke.CONSTRAINTS,
        )
        self.assertEqual(commands[1][-2:], ["pip", "check"])

    def test_base_mismatch_stops_before_install(self):
        self.versions["torch"] = "2.11.0+cu128"
        calls = []
        report = check_b1_b2_dependency_smoke.run_dependency_smoke(
            torch_module=self.torch,
            version_getter=self.version_getter,
            run_command=lambda *args, **kwargs: calls.append(args),
        )
        self.assertFalse(report["ready"])
        self.assertFalse(report["install_attempted"])
        self.assertIn("base_package_identity_mismatch", report["failures"])
        self.assertEqual(calls, [])

    def test_install_failure_is_a_completed_aggregate_diagnostic(self):
        report = check_b1_b2_dependency_smoke.run_dependency_smoke(
            torch_module=self.torch,
            version_getter=self.version_getter,
            import_module=self.import_module,
            run_command=lambda command, **kwargs: subprocess.CompletedProcess(
                command, 1, "resolver output", "network error"
            ),
        )
        self.assertTrue(report["probe_complete"])
        self.assertFalse(report["ready"])
        self.assertEqual(report["failures"], ["dependency_install_failed"])
        self.assertEqual(report["imports"], {})
        rendered = json.dumps(report)
        self.assertNotIn("resolver output", rendered)
        self.assertNotIn("network error", rendered)

    def test_source_contains_no_research_or_model_access(self):
        source = Path(check_b1_b2_dependency_smoke.__file__).read_text(
            encoding="utf-8"
        ).lower()
        for forbidden in (
            "from_pretrained",
            "nahw",
            "qalb",
            "huggingface token",
            "kaggle_api_token",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
