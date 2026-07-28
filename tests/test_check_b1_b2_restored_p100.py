import subprocess
import unittest
from pathlib import Path

from scripts import check_b1_b2_restored_p100


class B1B2RestoredP100PreflightTests(unittest.TestCase):
    def test_bootstrap_runs_before_fresh_process_preflight(self):
        calls = []

        def run_command(command, **kwargs):
            calls.append((command, kwargs))
            return subprocess.CompletedProcess(command, 0)

        report = check_b1_b2_restored_p100.run_restored_preflight(
            run_command=run_command,
            executable="/python",
            base_environment={"SAFE": "1"},
        )

        self.assertEqual(
            [call[0] for call in calls],
            [
                ["/python", "-m", "scripts.bootstrap_b1_b2_p100_runtime"],
                ["/python", "-m", "scripts.check_b1_b2_gpu_preflight"],
            ],
        )
        self.assertTrue(all(call[1]["check"] for call in calls))
        self.assertEqual([call[1]["timeout"] for call in calls], [600, 180])
        self.assertTrue(
            all(
                call[1]["env"]["UNSLOTH_COMPILE_DISABLE"] == "1"
                for call in calls
            )
        )
        self.assertTrue(report["passed"])
        self.assertTrue(report["fresh_processes"])
        self.assertEqual(report["maximum_subprocess_seconds"], 780)
        self.assertFalse(report["private_input_accessed"])
        self.assertFalse(report["model_loaded"])

    def test_source_has_no_data_model_or_evaluation_access(self):
        source = Path(check_b1_b2_restored_p100.__file__).read_text(
            encoding="utf-8"
        ).lower()
        for forbidden in (
            "from_pretrained",
            "/kaggle/input",
            "nahw",
            "qalb",
            "run_prompt_baseline",
            "kaggle_api_token",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
