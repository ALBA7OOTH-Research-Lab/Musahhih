import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.f1_eval_utils import (
    BASE_MODEL_ID,
    CONFIRMATION,
    EvaluationSafetyError,
    exact_mcnemar_p_value,
    load_validated_baseline_predictions,
    load_and_validate_nahw_records,
    paired_bootstrap_interval,
    paired_comparison,
    require_execution_authorization,
    validate_adapter_checkpoint,
)
from scripts.baseline_prompts import render_b0_prompt
from scripts.run_f1_adapter_eval import ROOT, validate_outputs_root


class F1EvaluationTests(unittest.TestCase):
    def test_adapter_checkpoint_validates_frozen_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            adapter = root / "checkpoint-250"
            adapter.mkdir()
            config = {
                "base_model_name_or_path": BASE_MODEL_ID,
                "peft_type": "LORA", "r": 16, "lora_alpha": 32,
                "lora_dropout": 0.0, "bias": "none", "inference_mode": True,
                "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj",
                                   "gate_proj", "up_proj", "down_proj"],
                "auto_mapping": {"base_model_class": "Gemma3ForConditionalGeneration"},
            }
            selection = {"selected_checkpoint": "checkpoint-250"}
            config_path = adapter / "adapter_config.json"
            selection_path = root / "checkpoint_selection.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            selection_path.write_text(json.dumps(selection), encoding="utf-8")
            result = validate_adapter_checkpoint(
                adapter,
                expected_adapter_sha256=hashlib.sha256(config_path.read_bytes()).hexdigest(),
                expected_selection_sha256=hashlib.sha256(selection_path.read_bytes()).hexdigest(),
            )
            self.assertEqual(result["adapter_path"], str(adapter.resolve()))
            config["r"] = 8
            config_path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(EvaluationSafetyError, "adapter config mismatch"):
                validate_adapter_checkpoint(
                    adapter,
                    expected_adapter_sha256=hashlib.sha256(config_path.read_bytes()).hexdigest(),
                    expected_selection_sha256=hashlib.sha256(selection_path.read_bytes()).hexdigest(),
                )

    def test_nahw_validator_checks_hash_count_markers_prompt_and_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nahw.jsonl"
            rows = [{"id": "n1", "passage_id": 1, "passage": "alpha beta",
                     "error": "beta", "gold_correction": "better", "split": "test",
                     "source": "Nahw-Passage",
                     "prompt": render_b0_prompt("alpha beta", "beta")}]
            path.write_text(json.dumps(rows[0]) + "\n", encoding="utf-8")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(len(load_and_validate_nahw_records(
                path, expected_sha256=digest, expected_records=1)), 1)
            rows[0]["prompt"] = "changed"
            path.write_text(json.dumps(rows[0]) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(EvaluationSafetyError, "frozen B0"):
                load_and_validate_nahw_records(
                    path,
                    expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    expected_records=1,
                )

    def test_baseline_predictions_require_frozen_hash_and_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "b0.jsonl"
            path.write_text(
                json.dumps({"record_id": "n1", "exact_match": False}) + "\n",
                encoding="utf-8",
            )
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(
                len(load_validated_baseline_predictions(
                    path, expected_sha256=digest, expected_records=1
                )),
                1,
            )
            with self.assertRaisesRegex(EvaluationSafetyError, "SHA-256"):
                load_validated_baseline_predictions(
                    path, expected_sha256="0" * 64, expected_records=1
                )

    def test_execution_requires_exact_confirmation_commit_and_reference(self):
        with patch("scripts.f1_eval_utils.subprocess.run") as run:
            run.return_value.returncode = 0
            require_execution_authorization(
                CONFIRMATION, "a" * 40,
                "https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/60",
                repository=Path("."),
            )
        with self.assertRaisesRegex(EvaluationSafetyError, "confirmation"):
            require_execution_authorization(
                "wrong", "a" * 40, "https://github.com/example/repo/issues/1",
                repository=Path("."),
            )

    def test_exact_mcnemar_values(self):
        self.assertEqual(exact_mcnemar_p_value(0, 0), 1.0)
        self.assertEqual(exact_mcnemar_p_value(1, 0), 1.0)
        self.assertAlmostEqual(exact_mcnemar_p_value(5, 0), 0.0625)
        self.assertEqual(exact_mcnemar_p_value(3, 3), 1.0)

    def test_paired_bootstrap_is_deterministic(self):
        first = paired_bootstrap_interval([1, 1, 0, -1], samples=200, seed=3407)
        second = paired_bootstrap_interval([1, 1, 0, -1], samples=200, seed=3407)
        self.assertEqual(first, second)
        self.assertLessEqual(first[0], first[1])

    def test_paired_comparison_uses_matching_ids(self):
        baseline = [{"record_id": "a", "exact_match": False},
                    {"record_id": "b", "exact_match": True},
                    {"record_id": "c", "exact_match": False}]
        adapter = [{"record_id": "c", "exact_match": True},
                   {"record_id": "a", "exact_match": True},
                   {"record_id": "b", "exact_match": False}]
        result = paired_comparison(baseline, adapter, bootstrap_samples=200)
        self.assertEqual(result["baseline_wrong_adapter_right"], 2)
        self.assertEqual(result["baseline_right_adapter_wrong"], 1)
        self.assertAlmostEqual(result["accuracy_difference_adapter_minus_baseline"], 1 / 3)
        with self.assertRaisesRegex(EvaluationSafetyError, "do not match"):
            paired_comparison(baseline, adapter[:-1], bootstrap_samples=10)

    def test_cli_help_does_not_load_model_and_exposes_gates(self):
        result = subprocess.run(
            [sys.executable, "-m", "scripts.run_f1_adapter_eval", "--help"],
            check=True, text=True, capture_output=True,
        )
        self.assertIn("--execute", result.stdout)
        self.assertIn("--approved-protocol-commit", result.stdout)
        self.assertIn("--approval-reference", result.stdout)

    def test_repository_local_outputs_must_stay_under_ignored_tree(self):
        self.assertEqual(validate_outputs_root(ROOT / "outputs"), (ROOT / "outputs").resolve())
        with self.assertRaisesRegex(EvaluationSafetyError, "ignored outputs"):
            validate_outputs_root(ROOT / "results")


if __name__ == "__main__":
    unittest.main()
