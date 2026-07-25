import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.f2_f3_eval_utils import (
    APPROVAL_PATTERN,
    ARM_SPECS,
    CONFIRMATION,
    EXPECTED_F1_PREDICTIONS_SHA256,
    RUN_ID,
    SAFE_STOP_ELAPSED_SECONDS,
    ArmSpec,
    EvaluationSafetyError,
    load_validated_reference_predictions,
    matched_comparisons,
    require_execution_authorization,
    validate_adapter_checkpoint,
)
from scripts.run_f2_f3_final_eval import (
    ROOT,
    KernelTimeBudget,
    TimeBudgetExhausted,
    execute,
    load_resume_prefixes,
    validate_outputs_root,
)


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
        self.assertEqual(
            CONFIRMATION, "RUN_F2_F3_MATCHED_NAHW_FINAL_511_TIMEOUT_SAFE"
        )
        self.assertEqual(SAFE_STOP_ELAPSED_SECONDS, 34_200)
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
                    "Musahhih/issues/98#issuecomment-123456"
                ),
                repository=Path("."),
            )
        self.assertTrue(
            APPROVAL_PATTERN.fullmatch(
                "https://github.com/ALBA7OOTH-Research-Lab/"
                "Musahhih/issues/98#issuecomment-123456"
            )
        )
        with self.assertRaisesRegex(EvaluationSafetyError, "issue #98"):
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
            "--kernel-start-epoch-seconds",
            "--resume-from",
        ):
            self.assertIn(flag, result.stdout)

    def test_time_budget_stops_before_the_observed_platform_cutoff(self):
        now = [1_000.0]
        budget = KernelTimeBudget(
            900.0,
            now=lambda: now[0],
            safe_stop_elapsed_seconds=200,
        )
        budget.require_next_record_budget()
        now[0] = 1_100.0
        with self.assertRaises(TimeBudgetExhausted):
            budget.require_next_record_budget()
        with self.assertRaisesRegex(EvaluationSafetyError, "future"):
            KernelTimeBudget(2_000.0, now=lambda: 1_000.0)

    def test_resume_requires_hash_verified_private_prefix_and_runtime(self):
        record = {
            "id": "n1",
            "passage_id": "p1",
            "source": "fixture",
            "split": "test",
            "passage": "private passage",
            "error": "private error",
            "gold_correction": "private correction",
            "prompt": "private prompt",
        }
        row = {
            "record_id": "n1",
            "passage_id": "p1",
            "source": "fixture",
            "split": "test",
            "passage": "private passage",
            "erroneous_word": "private error",
            "gold_correction": "private correction",
            "full_prompt": "private prompt",
            "raw_model_response": "private response",
            "parsed_correction": "private correction",
            "exact_match": True,
            "parsing_warnings": [],
        }
        commit = "a" * 40
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            predictions = root / "f2-p1_predictions.jsonl"
            predictions.write_text(
                json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            digest = hashlib.sha256(predictions.read_bytes()).hexdigest()
            (root / "public_summary.json").write_text(
                json.dumps(
                    {
                        "run_status": "incomplete_time_budget",
                        "git_commit": commit,
                    }
                ),
                encoding="utf-8",
            )
            (root / "progress.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "experiment_id": RUN_ID,
                        "git_commit": commit,
                        "completed_records": {"F2-P1": 1, "F3-P1": 0},
                        "prediction_sha256": {"F2-P1": digest, "F3-P1": None},
                        "runtime": {"F2-P1": {"gpu": "Tesla P100"}},
                    }
                ),
                encoding="utf-8",
            )
            prefixes, runtimes = load_resume_prefixes(
                root, records=[record], approved_protocol_commit=commit
            )
            self.assertEqual(len(prefixes["F2-P1"][0]), 1)
            self.assertEqual(runtimes["F2-P1"]["gpu"], "Tesla P100")
            predictions.write_text("{}\n", encoding="utf-8")
            with self.assertRaises(EvaluationSafetyError):
                load_resume_prefixes(
                    root, records=[record], approved_protocol_commit=commit
                )

    def test_execute_gracefully_preserves_a_metric_free_timed_handoff(self):
        class ExhaustedBudget:
            def elapsed_seconds(self):
                return SAFE_STOP_ELAPSED_SECONDS

            def require_next_record_budget(self):
                raise TimeBudgetExhausted

        record = {
            "id": "n1",
            "passage_id": "p1",
            "source": "fixture",
            "split": "test",
            "passage": "private passage",
            "error": "private error",
            "gold_correction": "private correction",
            "prompt": "private prompt",
        }
        with tempfile.TemporaryDirectory() as directory:
            args = SimpleNamespace(
                replicate=1,
                outputs_root=Path(directory),
                kernel_start_epoch_seconds=1.0,
                resume_from=None,
                approved_protocol_commit="a" * 40,
                approval_reference=(
                    "https://github.com/ALBA7OOTH-Research-Lab/"
                    "Musahhih/issues/98#issuecomment-123"
                ),
                f2_adapter=Path("unused-f2"),
                f3_adapter=Path("unused-f3"),
            )
            with patch(
                "scripts.run_f2_f3_final_eval.KernelTimeBudget",
                return_value=ExhaustedBudget(),
            ):
                summary = execute(
                    args,
                    records=[record],
                    b0_rows=[],
                    f1_rows=[],
                    adapter_meta={},
                )
            self.assertEqual(summary["run_status"], "incomplete_time_budget")
            self.assertFalse(summary["metrics_reported"])
            self.assertEqual(
                summary["completed_records"], {"F2-P1": 0, "F3-P1": 0}
            )
            run_dir = Path(directory) / RUN_ID
            self.assertTrue((run_dir / "progress.json").is_file())
            self.assertFalse((run_dir / "f2-p1_predictions.jsonl").exists())

    def test_repository_local_outputs_must_stay_ignored(self):
        self.assertEqual(
            validate_outputs_root(ROOT / "outputs"), (ROOT / "outputs").resolve()
        )
        with self.assertRaisesRegex(EvaluationSafetyError, "ignored outputs"):
            validate_outputs_root(ROOT / "results")
        with self.assertRaisesRegex(EvaluationSafetyError, "ignored outputs"):
            load_resume_prefixes(
                ROOT / "results" / "private-resume",
                records=[],
                approved_protocol_commit="a" * 40,
            )

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
            "_write_json_atomic(public_summary_path, summary)", 1
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
