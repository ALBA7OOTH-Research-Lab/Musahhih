import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.baseline_prompts import render_b0_prompt
from scripts.f1_eval_utils import EvaluationSafetyError
from scripts.f1_safety_eval_utils import (
    CONFIRMATION,
    load_capability_records,
    load_overcorrection_records,
    paired_binary_comparison,
    require_execution_authorization,
    select_highest_logit,
    stratified_paired_bootstrap_interval,
)
from scripts.run_f1_safety_eval import ROOT, validate_outputs_root


def write_jsonl(path: Path, rows: list[dict]) -> str:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    return hashlib.sha256(path.read_bytes()).hexdigest()


class F1SafetyEvaluationTests(unittest.TestCase):
    def test_overcorrection_loader_checks_frozen_record_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "over.jsonl"
            passage = "نص صحيح"
            token = "صحيح"
            row = {
                "record_id": "q1",
                "source": "QALB-2015-L2-Dev",
                "split": "dev",
                "passage": passage,
                "selected_token_position": 1,
                "selected_token": token,
                "gold_unchanged_token": token,
                "prompt": render_b0_prompt(passage, token),
            }
            digest = write_jsonl(path, [row])
            self.assertEqual(len(load_overcorrection_records(
                path, expected_sha256=digest, expected_records=1
            )), 1)
            row["gold_unchanged_token"] = "تغيير"
            digest = write_jsonl(path, [row])
            with self.assertRaisesRegex(EvaluationSafetyError, "not unchanged"):
                load_overcorrection_records(
                    path, expected_sha256=digest, expected_records=1
                )

    def test_capability_loader_requires_40_balanced_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "capability.jsonl"
            rows = []
            for task in range(40):
                for index in range(25):
                    rows.append({
                        "record_id": f"r-{task}-{index}",
                        "task": f"task-{task}",
                        "source_id": str(index),
                        "source": "MBZUAI/ArabicMMLU",
                        "split": "test",
                        "prompt": "This is a test.\n\nAnswer:",
                        "choices": ["A", "B", "C", "D"],
                        "gold_choice": "A",
                    })
            digest = write_jsonl(path, rows)
            self.assertEqual(len(load_capability_records(
                path, expected_sha256=digest, expected_records=1000
            )), 1000)
            rows[-1]["task"] = "task-new"
            digest = write_jsonl(path, rows)
            with self.assertRaisesRegex(EvaluationSafetyError, "task balance"):
                load_capability_records(
                    path, expected_sha256=digest, expected_records=1000
                )

    def test_stratified_bootstrap_and_paired_comparison_are_deterministic(self):
        strata = {"b": [1, -1], "a": [1, 0]}
        first = stratified_paired_bootstrap_interval(strata, samples=200, seed=3407)
        second = stratified_paired_bootstrap_interval(strata, samples=200, seed=3407)
        self.assertEqual(first, second)
        baseline = [
            {"record_id": "a", "task": "one", "ok": False},
            {"record_id": "b", "task": "one", "ok": True},
            {"record_id": "c", "task": "two", "ok": False},
        ]
        adapter = [
            {"record_id": "c", "task": "two", "ok": True},
            {"record_id": "a", "task": "one", "ok": True},
            {"record_id": "b", "task": "one", "ok": False},
        ]
        result = paired_binary_comparison(
            baseline,
            adapter,
            outcome_field="ok",
            stratum_field="task",
            bootstrap_samples=200,
        )
        self.assertEqual(result["baseline_wrong_adapter_right"], 2)
        self.assertEqual(result["baseline_right_adapter_wrong"], 1)
        self.assertEqual(result["bootstrap_strata"], 2)

    def test_execution_gate_requires_exact_confirmation_commit_and_reference(self):
        with patch("scripts.f1_safety_eval_utils.subprocess.run") as run:
            run.return_value.returncode = 0
            require_execution_authorization(
                CONFIRMATION,
                "a" * 40,
                "https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/63",
                repository=Path("."),
            )
        with self.assertRaisesRegex(EvaluationSafetyError, "confirmation"):
            require_execution_authorization(
                "wrong",
                "a" * 40,
                "https://github.com/example/repo/issues/1",
                repository=Path("."),
            )

    def test_choice_ties_use_earliest_displayed_option(self):
        self.assertEqual(
            select_highest_logit(["A", "B", "C"], {"A": 1.0, "B": 2.0, "C": 2.0}),
            "B",
        )
        with self.assertRaisesRegex(EvaluationSafetyError, "do not match"):
            select_highest_logit(["A", "B"], {"A": 1.0})

    def test_cli_help_does_not_import_gpu_dependencies(self):
        result = subprocess.run(
            [sys.executable, "-m", "scripts.run_f1_safety_eval", "--help"],
            check=True,
            text=True,
            capture_output=True,
        )
        self.assertIn("--execute", result.stdout)
        self.assertIn("--approved-protocol-commit", result.stdout)
        self.assertIn("--approval-reference", result.stdout)

    def test_repository_local_outputs_must_stay_ignored(self):
        self.assertEqual(validate_outputs_root(ROOT / "outputs"), (ROOT / "outputs").resolve())
        with self.assertRaisesRegex(EvaluationSafetyError, "ignored outputs"):
            validate_outputs_root(ROOT / "results")


if __name__ == "__main__":
    unittest.main()
