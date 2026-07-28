import importlib.metadata
import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts import bootstrap_b1_b2_p100_runtime as bootstrap


class B1B2ProvenP100BootstrapTests(unittest.TestCase):
    def test_proven_stack_matches_completed_f2_runtime(self):
        self.assertEqual(bootstrap.RESTORED_P100_STACK["torch"], "2.6.0")
        self.assertEqual(bootstrap.RESTORED_P100_STACK["torchvision"], "0.21.0")
        self.assertEqual(bootstrap.RESTORED_P100_STACK["xformers"], "0.0.29.post3")
        self.assertEqual(bootstrap.RESTORED_P100_STACK["torchao"], "0.16.0")
        self.assertEqual(bootstrap.RESTORED_P100_STACK["numpy"], "2.0.2")
        self.assertEqual(bootstrap.RESTORED_P100_STACK["transformers"], "4.56.2")
        self.assertEqual(bootstrap.RESTORED_P100_STACK["unsloth"], "2026.7.3")
        self.assertEqual(bootstrap.RESTORED_P100_STACK["trl"], "0.22.2")

    def test_compatible_stack_skips_all_installs(self):
        versions = dict(bootstrap.RESTORED_P100_STACK)
        versions["torch"] += "+cu124"
        versions["torchvision"] += "+cu124"
        self.assertEqual(bootstrap.bootstrap_commands(versions), [])

    def test_incompatible_current_kaggle_base_restores_official_cu124_stack(self):
        versions = dict(bootstrap.RESTORED_P100_STACK)
        versions.update(
            {
                "torch": "2.10.0+cu128",
                "torchvision": "0.25.0+cu128",
                "xformers": "0.0.34",
                "unsloth": "2026.7.2",
                "trl": "0.23.0",
            }
        )
        commands = bootstrap.bootstrap_commands(versions)
        rendered = [" ".join(command) for command in commands]
        self.assertIn("torch==2.6.0", rendered[0])
        self.assertIn("torchvision==0.21.0", rendered[0])
        self.assertIn(bootstrap.PYTORCH_INDEX, rendered[0])
        self.assertTrue(any("xformers==0.0.29.post3" in item for item in rendered))
        self.assertTrue(any("unsloth==2026.7.3" in item for item in rendered))
        self.assertTrue(any("unsloth_zoo==2026.7.3" in item for item in rendered))
        self.assertTrue(any("transformers==4.56.2" in item for item in rendered))

    def test_bootstrap_reports_hashes_without_raw_installer_output(self):
        versions = dict(bootstrap.RESTORED_P100_STACK)
        versions["torch"] += "+cu124"
        versions["torchvision"] += "+cu124"

        def getter(name):
            value = versions.get(name)
            if value is None:
                raise importlib.metadata.PackageNotFoundError(name)
            return value

        report = bootstrap.bootstrap(getter=getter)
        self.assertTrue(report["passed"])
        self.assertFalse(report["install_performed"])
        self.assertEqual(report["command_reports"], [])
        self.assertFalse(report["private_input_accessed"])
        self.assertFalse(report["model_loaded"])

    def test_runtime_gate_requires_exact_stack_and_cuda_124(self):
        versions = dict(bootstrap.RESTORED_P100_STACK)
        versions["torch"] += "+cu124"
        versions["torchvision"] += "+cu124"

        def getter(name):
            value = versions.get(name)
            if value is None:
                raise importlib.metadata.PackageNotFoundError(name)
            return value

        report = bootstrap.require_proven_p100_stack(
            SimpleNamespace(version=SimpleNamespace(cuda="12.4")),
            getter=getter,
        )
        self.assertTrue(report["compatible"])
        self.assertEqual(report["cuda_runtime"], "12.4")
        with self.assertRaisesRegex(bootstrap.P100BootstrapError, "CUDA 12.4"):
            bootstrap.require_proven_p100_stack(
                SimpleNamespace(version=SimpleNamespace(cuda="12.8")),
                getter=getter,
            )

    def test_bootstrap_fails_closed_on_first_install_error(self):
        versions = dict(bootstrap.RESTORED_P100_STACK)
        versions["torch"] = "2.10.0+cu128"
        versions["torchvision"] = "0.25.0+cu128"

        def getter(name):
            value = versions.get(name)
            if value is None:
                raise importlib.metadata.PackageNotFoundError(name)
            return value

        with self.assertRaisesRegex(bootstrap.P100BootstrapError, "bootstrap failed"):
            bootstrap.bootstrap(
                getter=getter,
                run_command=lambda command, **kwargs: subprocess.CompletedProcess(
                    command, 1, "installer details", "network details"
                ),
            )

    def test_source_contains_no_research_or_model_access(self):
        source = Path(bootstrap.__file__).read_text(encoding="utf-8").lower()
        for forbidden in (
            "from_pretrained",
            "nahw",
            "qalb",
            "kaggle_api_token",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
