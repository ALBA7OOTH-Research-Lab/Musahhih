import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts.f2_f3_eval_utils import (
    APPROVAL_PATTERN,
    ARM_SPECS,
    CONFIRMATION,
    EXPECTED_F1_PREDICTIONS_SHA256,
    ArmSpec,
    EvaluationSafetyError,
    load_validated_reference_predictions,
    matched_comparisons,
    require_execution_authorization,
    validate_adapter_checkpoint,
)
from scripts.run_f2_f3_final_eval import ROOT, validate_outputs_root


class F2F3EvaluationTests(unittest.TestCase):
    def _synthetic_adapter(self, root: Path, arm: str, checkpoint: str):
        adapter = root / checkpoint
        adapter.mkdir()
        model_path = adapter / "adapter_model.safetensors"
        config_path = adapter / "adapter_config.json"
        selection_path = root / "checkpoint_selection.json"
        model_path.write_bytes(b"synthetic-adapter")
        config_path.write_text(
            json.dumps(
                {
                    "base_model_name_or_path": (
                        "unsloth/gemma-3-4b-it-unsloth-bnb-4bit"
                    ),
                    "peft_type": "LORA",
                    "r": 16,
                    "lora_alpha": 32,
                    "lora_dropout": 0.0,
                    "bias": "none",
                    "inference_mode": True,
                    "target_modules": [
                        "q_proj",
                        "k_proj",
                        "v_proj",
                        "o_proj",
                        "gate_proj",
                        "up_proj",
                        "down_proj",
                    ],
                    "auto_mapping": {
                        "base_model_class": "Gemma3ForConditionalGeneration"
                    },
                }
            ),
            encoding="utf-8",
        )
        selection_path.write_text(
            json.dumps(
                {
                    "arm": arm,
                    "selected_checkpoint": checkpoint,
                    "evaluations": [{"epoch": 1}, {"epoch": 2}],
                }
            ),
            encoding="utf-8",
        )
        spec = ArmSpec(
            arm=arm,
            checkpoint=checkpoint,
            adapter_model_sha256=hashlib.sha256(model_path.read_bytes()).hexdigest(),
            adapter_config_sha256=hashlib.sha256(config_path.read_bytes()).hexdigest(),
            checkpoint_selection_sha256=hashlib.sha256(
                selection_path.read_bytes()
            ).hexdigest(),
        )
        return adapter, spec

    def test_frozen_arm_identities(self):
        self.assertEqual(ARM_SPECS["F2-P1"].checkpoint, "checkpoint-125")
        self.assertEqual(ARM_SPECS["F3-P1"].checkpoint, "checkpoint-250")
        self.assertEqual(
            ARM_SPECS["F2-P1"].adapter_model_sha256,
            "935fdf02c95189934e40629f877d8692d325ef22895cbaa03fdb7390b0cd7b3e",
        )
        self.assertEqual(
            ARM_SPECS["F3-P1"].adapter_model_sha256,
            "95bd333caac28e08b40fcafe7bc033f323188e817d7c16ecbe7745b34c1b44dc",
        )
        self.assertEqual(
            EXPECTED_F1_PREDICTIONS_SHA256,
            "8c4d0ca25b48776a08ea02984af6c5c3ec0bc830d2d1a6994e0fb5eef995faa3",
        )

    def test_adapter_validation_locks_bytes_config_selection_and_arm(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter, spec = self._synthetic_adapter(
                Path(directory), "F2-P1", "checkpoint-125"
            )
            result = validate_adapter_checkpoint(adapter, spec)
            self.assertEqual(result["arm"], "F2-P1")
            self.assertFalse(result["adapter_merged"])
            (adapter / "adapter_model.safetensors").write_bytes(b"changed")
            with self.assertRaisesRegex(EvaluationSafetyError, "adapter model"):
                validate_adapter_checkpoint(adapter, spec)

    def test_reference_predictions_require_hash_count_ids_and_boolean_score(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "predictions.jsonl"
            path.write_text(
                json.dumps({"record_id": "n1", "exact_match": True}) + "\n",
                encoding="utf-8",
            )
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            rows = load_validated_reference_predictions(
                path, expected_sha256=digest, label="fixture", expected_records=1
            )
            self.assertEqual(len(rows), 1)
            with self.assertRaisesRegex(EvaluationSafetyError, "SHA-256"):
                load_validated_reference_predictions(
                    path,
                    expected_sha256="0" * 64,
                    label="fixture",
                    expected_records=1,
                )

    def test_authorization_requires_exact_issue_comment_and_checkout(self):
        completed = subprocess.CompletedProcess(
            args=["git"], returncode=0, stdout="a" * 40 + "\n", stderr=""
        )
        with patch("scripts.f2_f3_eval_utils.subprocess.run", return_value=completed):
            require_execution_authorization(
                CONFIRMATION,
                "a" * 40,
                (
                    "https://github.com/ALBA7OOTH-Research-Lab/"
                    "Musahhih/issues/96#issuecomment-123456"
                ),
                repository=Path("."),
            )
        self.assertTrue(
            APPROVAL_PATTERN.fullmatch(
                "https://github.com/ALBA7OOTH-Research-Lab/"
                "Musahhih/issues/96#issuecomment-123456"
            )
        )
        with self.assertRaisesRegex(EvaluationSafetyError, "issue #96"):
            require_execution_authorization(
                CONFIRMATION,
                "a" * 40,
                "https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/93#issuecomment-1",
                repository=Path("."),
            )

    def test_primary_and_secondary_comparison_directions_are_frozen(self):
        b0 = [
            {"record_id": "a", "exact_match": False},
            {"record_id": "b", "exact_match": False},
            {"record_id": "c", "exact_match": True},
        ]
        f1 = [
            {"record_id": "a", "exact_match": True},
            {"record_id": "b", "exact_match": False},
            {"record_id": "c", "exact_match": True},
        ]
        f2 = [
            {"record_id": "a", "exact_match": False},
            {"record_id": "b", "exact_match": True},
            {"record_id": "c", "exact_match": True},
        ]
        f3 = [
            {"record_id": "a", "exact_match": True},
            {"record_id": "b", "exact_match": True},
            {"record_id": "c", "exact_match": False},
        ]
        result = matched_comparisons(
            b0_rows=b0,
            f1_rows=f1,
            f2_rows=f2,
            f3_rows=f3,
            bootstrap_samples=200,
        )
        primary = result["primary_f3_minus_f2"]
        self.assertEqual(primary["baseline_wrong_adapter_right"], 1)
        self.assertEqual(primary["baseline_right_adapter_wrong"], 1)
        self.assertEqual(
            set(result),
            {
                "primary_f3_minus_f2",
                "secondary_f2_minus_b0",
                "secondary_f3_minus_b0",
                "secondary_f2_minus_f1",
                "secondary_f3_minus_f1",
            },
        )

    def test_disabled_cli_does_not_require_existing_private_or_test_inputs(self):
        command = [
            sys.executable,
            "-m",
            "scripts.run_f2_f3_final_eval",
            "--f2-adapter",
            "missing-f2",
            "--f3-adapter",
            "missing-f3",
            "--input",
            "missing-nahw",
            "--baseline-predictions",
            "missing-b0",
            "--f1-predictions",
            "missing-f1",
        ]
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "disabled")
        self.assertFalse(payload["inference_executed"])
        self.assertFalse(payload["final_test_accessed"])

    def test_cli_help_exposes_all_execution_gates(self):
        result = subprocess.run(
            [sys.executable, "-m", "scripts.run_f2_f3_final_eval", "--help"],
            check=True,
            text=True,
            capture_output=True,
        )
        for flag in (
            "--execute",
            "--confirmation",
            "--approved-protocol-commit",
            "--approval-reference",
            "--f2-adapter",
            "--f3-adapter",
        ):
            self.assertIn(flag, result.stdout)

    def test_repository_local_outputs_must_stay_ignored(self):
        self.assertEqual(
            validate_outputs_root(ROOT / "outputs"), (ROOT / "outputs").resolve()
        )
        with self.assertRaisesRegex(EvaluationSafetyError, "ignored outputs"):
            validate_outputs_root(ROOT / "results")

    def test_evaluator_has_no_training_or_qalb_test_path(self):
        source = (ROOT / "scripts" / "run_f2_f3_final_eval.py").read_text(
            encoding="utf-8"
        )
        self.assertLess(source.index('("F2-P1", args.f2_adapter)'), source.index(
            '("F3-P1", args.f3_adapter)'
        ))
        for forbidden in (
            "SFTTrainer",
            "trainer.train",
            "optimizer.step",
            "qalb_test.jsonl",
            "private_exact_match_count",
        ):
            self.assertNotIn(forbidden, source)
        public_literal = source.split("summary = {", 1)[1].split(
            "public_summary_path.write_text", 1
        )[0]
        for private_field in (
            '"passage"',
            '"erroneous_word"',
            '"gold_correction"',
            '"full_prompt"',
            '"raw_model_response"',
            '"parsed_correction"',
            '"record_id"',
        ):
            self.assertNotIn(private_field, public_literal)


if __name__ == "__main__":
    unittest.main()
