import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.f2_f3_safety_eval_utils import (
    APPROVAL_PATTERN,
    CONFIRMATION,
    EXPECTED_STAGE_RECORDS,
    RUN_ID,
    SAFE_STOP_ELAPSED_SECONDS,
    STAGES,
    EvaluationSafetyError,
    require_execution_authorization,
)
from scripts.prepare_f2_f3_safety_kaggle_kernel import (
    KernelPreparationError,
    build_metadata,
    build_wrapper,
    write_package,
)
from scripts.run_f2_f3_safety_eval import (
    ROOT,
    KernelTimeBudget,
    TimeBudgetExhausted,
    execute,
    load_reference_predictions,
    load_resume_prefixes,
    validate_outputs_root,
)


class FakeSystem:
    def __init__(self, system_id, adapter_path):
        self.system_id = system_id
        self.adapter_path = adapter_path

    def load(self):
        return {"gpu": "Tesla P100-PCIE-16GB", "system": self.system_id}

    def generate_correction(self, prompt):
        return "same"

    def score_choices(self, prompt, choices):
        logits = {choice: float(len(choices) - index) for index, choice in enumerate(choices)}
        return choices[0], logits

    def close(self):
        return None


class F2F3SafetyEvaluationTests(unittest.TestCase):
    def test_frozen_contract(self):
        self.assertEqual(CONFIRMATION, "RUN_MATCHED_F2_F3_SAFETY_DIAGNOSTICS_TIMEOUT_SAFE")
        self.assertEqual(SAFE_STOP_ELAPSED_SECONDS, 34_200)
        self.assertEqual(len(STAGES), 4)
        self.assertEqual(EXPECTED_STAGE_RECORDS["F2-P1_overcorrection"], 154)
        self.assertEqual(EXPECTED_STAGE_RECORDS["F3-P1_capability"], 1_000)

    def test_authorization_requires_issue_200_and_exact_checkout(self):
        completed = subprocess.CompletedProcess(
            args=["git"], returncode=0, stdout="a" * 40 + "\n", stderr=""
        )
        reference = (
            "https://github.com/ALBA7OOTH-Research-Lab/"
            "Musahhih/issues/200#issuecomment-123456"
        )
        self.assertTrue(APPROVAL_PATTERN.fullmatch(reference))
        with patch("scripts.f2_f3_safety_eval_utils.subprocess.run", return_value=completed):
            require_execution_authorization(
                CONFIRMATION, "a" * 40, reference, repository=Path(".")
            )
        with self.assertRaisesRegex(EvaluationSafetyError, "issue #200"):
            require_execution_authorization(
                CONFIRMATION,
                "a" * 40,
                "https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/196#issuecomment-1",
                repository=Path("."),
            )

    def test_disabled_cli_does_not_access_private_inputs_or_models(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "scripts.run_f2_f3_safety_eval",
                "--f2-adapter",
                "missing-f2",
                "--f3-adapter",
                "missing-f3",
                "--overcorrection-input",
                "missing-over",
                "--capability-input",
                "missing-capability",
                "--b0-overcorrection-predictions",
                "missing-b0-over",
                "--f1-overcorrection-predictions",
                "missing-f1-over",
                "--b0-capability-predictions",
                "missing-b0-cap",
                "--f1-capability-predictions",
                "missing-f1-cap",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "disabled")
        self.assertFalse(payload["private_input_accessed"])
        self.assertFalse(payload["model_loaded"])
        self.assertFalse(payload["inference_executed"])
        self.assertFalse(payload["metrics_computed"])

    def test_time_budget_fails_before_platform_cutoff(self):
        now = [1_000.0]
        budget = KernelTimeBudget(900.0, now=lambda: now[0], safe_stop_elapsed_seconds=200)
        budget.require_next_record_budget()
        now[0] = 1_100.0
        with self.assertRaises(TimeBudgetExhausted):
            budget.require_next_record_budget()

    def test_complete_synthetic_execution_writes_only_aggregate_public_summary(self):
        class OpenBudget:
            def elapsed_seconds(self):
                return 1

            def require_next_record_budget(self):
                return None

        over = [{
            "record_id": "o1",
            "source": "fixture",
            "split": "dev",
            "passage": "private passage",
            "selected_token": "same",
            "selected_token_position": 0,
            "gold_unchanged_token": "same",
            "prompt": "private correction prompt",
        }]
        capability = [{
            "record_id": "c1",
            "source": "fixture",
            "source_id": "private-source-id",
            "split": "test",
            "task": "fixture-task",
            "prompt": "private question",
            "choices": ["A", "B"],
            "gold_choice": "A",
        }]
        reference_rows = {
            f"{system}_overcorrection": [{
                **over[0],
                "system_id": system,
                "raw_model_response": "same",
                "parsed_correction": "same",
                "parsing_warnings": [],
                "unchanged_exact": True,
            }]
            for system in ("B0", "F1-P1")
        }
        reference_rows.update({
            f"{system}_capability": [{
                **capability[0],
                "system_id": system,
                "candidate_logits": {"A": 2.0, "B": 1.0},
                "predicted_choice": "A",
                "exact_match": True,
            }]
            for system in ("B0", "F1-P1")
        })
        reference = (
            "https://github.com/ALBA7OOTH-Research-Lab/"
            "Musahhih/issues/200#issuecomment-123"
        )
        with tempfile.TemporaryDirectory() as directory:
            args = SimpleNamespace(
                replicate=1,
                outputs_root=Path(directory),
                kernel_start_epoch_seconds=0.0,
                resume_from=None,
                approved_protocol_commit="a" * 40,
                approval_reference=reference,
                f2_adapter=Path("f2"),
                f3_adapter=Path("f3"),
            )
            expected = {stage: 1 for stage in STAGES}
            with patch.dict(
                "scripts.run_f2_f3_safety_eval.EXPECTED_STAGE_RECORDS",
                expected,
                clear=True,
            ), patch(
                "scripts.run_f2_f3_safety_eval.BOOTSTRAP_SAMPLES", 20
            ), patch(
                "scripts.run_f2_f3_safety_eval.KernelTimeBudget",
                return_value=OpenBudget(),
            ):
                summary = execute(
                    args,
                    overcorrection_records=over,
                    capability_records=capability,
                    adapter_meta={"F2-P1": {}, "F3-P1": {}},
                    reference_rows=reference_rows,
                    model_factory=FakeSystem,
                )
            self.assertEqual(summary["run_status"], "complete")
            self.assertEqual(
                summary["comparisons"]["overcorrection_unchanged_accuracy"][
                    "primary_f3_minus_f2"
                ][
                    "accuracy_difference_adapter_minus_baseline"
                ],
                0.0,
            )
            public_text = (Path(directory) / RUN_ID / "public_summary.json").read_text(
                encoding="utf-8"
            )
            for private_value in (
                "private passage",
                "private correction prompt",
                "private question",
                "private-source-id",
            ):
                self.assertNotIn(private_value, public_text)

    def test_empty_metric_free_handoff_is_valid_resume_source(self):
        commit = "a" * 40
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "public_summary.json").write_text(
                json.dumps({"run_status": "incomplete_time_budget", "git_commit": commit}),
                encoding="utf-8",
            )
            (root / "progress.json").write_text(
                json.dumps({
                    "schema_version": 1,
                    "experiment_family": RUN_ID,
                    "git_commit": commit,
                    "completed_records": {stage: 0 for stage in STAGES},
                    "prediction_sha256": {stage: None for stage in STAGES},
                    "runtime": {},
                }),
                encoding="utf-8",
            )
            prefixes, runtimes = load_resume_prefixes(
                root,
                overcorrection_records=[],
                capability_records=[],
                approved_protocol_commit=commit,
            )
            self.assertEqual(set(prefixes), set(STAGES))
            self.assertEqual(runtimes, {})

    def test_immutable_reference_predictions_are_hash_and_contract_checked(self):
        import hashlib

        over = [{
            "record_id": "o1",
            "source": "fixture",
            "split": "dev",
            "passage": "private passage",
            "selected_token": "same",
            "selected_token_position": 0,
            "gold_unchanged_token": "same",
            "prompt": "private prompt",
        }]
        capability = [{
            "record_id": "c1",
            "source": "fixture",
            "source_id": "private-source-id",
            "split": "test",
            "task": "fixture-task",
            "prompt": "private question",
            "choices": ["A", "B"],
            "gold_choice": "A",
        }]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = {}
            hashes = {}
            for system in ("B0", "F1-P1"):
                over_label = f"{system}_overcorrection"
                over_path = root / f"{over_label}.jsonl"
                over_path.write_text(json.dumps({
                    **over[0],
                    "system_id": system,
                    "raw_model_response": "same",
                    "parsed_correction": "same",
                    "parsing_warnings": [],
                    "unchanged_exact": True,
                }, sort_keys=True) + "\n", encoding="utf-8")
                paths[over_label] = over_path
                hashes[over_label] = hashlib.sha256(over_path.read_bytes()).hexdigest()

                cap_label = f"{system}_capability"
                cap_path = root / f"{cap_label}.jsonl"
                cap_path.write_text(json.dumps({
                    **capability[0],
                    "system_id": system,
                    "candidate_logits": {"A": 2.0, "B": 1.0},
                    "predicted_choice": "A",
                    "exact_match": True,
                }, sort_keys=True) + "\n", encoding="utf-8")
                paths[cap_label] = cap_path
                hashes[cap_label] = hashlib.sha256(cap_path.read_bytes()).hexdigest()
            with patch.dict(
                "scripts.run_f2_f3_safety_eval.REFERENCE_PREDICTION_SHA256",
                hashes,
                clear=True,
            ):
                loaded = load_reference_predictions(
                    paths,
                    overcorrection_records=over,
                    capability_records=capability,
                )
            self.assertEqual(set(loaded), set(paths))

    def test_resume_rejects_later_stage_before_earlier_completion(self):
        import hashlib

        commit = "a" * 40
        capability = [{
            "record_id": "c1",
            "source": "fixture",
            "source_id": "private-source-id",
            "split": "test",
            "task": "fixture-task",
            "prompt": "private question",
            "choices": ["A", "B"],
            "gold_choice": "A",
        }]
        row = {
            **capability[0],
            "system_id": "F2-P1",
            "candidate_logits": {"A": 2.0, "B": 1.0},
            "predicted_choice": "A",
            "exact_match": True,
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "f2_p1_capability_predictions.jsonl"
            path.write_text(json.dumps(row, sort_keys=True) + "\n", encoding="utf-8")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            completed = {stage: 0 for stage in STAGES}
            completed["F2-P1_capability"] = 1
            hashes = {stage: None for stage in STAGES}
            hashes["F2-P1_capability"] = digest
            (root / "public_summary.json").write_text(
                json.dumps({"run_status": "incomplete_time_budget", "git_commit": commit}),
                encoding="utf-8",
            )
            (root / "progress.json").write_text(
                json.dumps({
                    "schema_version": 1,
                    "experiment_family": RUN_ID,
                    "git_commit": commit,
                    "completed_records": completed,
                    "prediction_sha256": hashes,
                    "runtime": {"F2-P1": {"gpu": "Tesla P100"}},
                }),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(EvaluationSafetyError, "out of order"):
                load_resume_prefixes(
                    root,
                    overcorrection_records=[],
                    capability_records=capability,
                    approved_protocol_commit=commit,
                )

    def test_timeout_preserves_metric_free_handoff(self):
        class ExhaustedBudget:
            def elapsed_seconds(self):
                return SAFE_STOP_ELAPSED_SECONDS

            def require_next_record_budget(self):
                raise TimeBudgetExhausted

        over = [{
            "record_id": "o1",
            "source": "fixture",
            "split": "dev",
            "passage": "private passage",
            "selected_token": "same",
            "selected_token_position": 0,
            "gold_unchanged_token": "same",
            "prompt": "private prompt",
        }]
        capability = [{
            "record_id": "c1",
            "source": "fixture",
            "source_id": "private-source-id",
            "split": "test",
            "task": "fixture-task",
            "prompt": "private question",
            "choices": ["A", "B"],
            "gold_choice": "A",
        }]
        reference_rows = {
            "B0_overcorrection": [],
            "F1-P1_overcorrection": [],
            "B0_capability": [],
            "F1-P1_capability": [],
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
                    "Musahhih/issues/200#issuecomment-123"
                ),
                f2_adapter=Path("f2"),
                f3_adapter=Path("f3"),
            )
            with patch(
                "scripts.run_f2_f3_safety_eval.KernelTimeBudget",
                return_value=ExhaustedBudget(),
            ):
                summary = execute(
                    args,
                    overcorrection_records=over,
                    capability_records=capability,
                    adapter_meta={"F2-P1": {}, "F3-P1": {}},
                    reference_rows=reference_rows,
                    model_factory=FakeSystem,
                )
            self.assertEqual(summary["run_status"], "incomplete_time_budget")
            self.assertFalse(summary["metrics_reported"])
            self.assertTrue(summary["resume_requires_fresh_authorization"])
            self.assertNotIn("primary_comparisons", summary)

    def test_kernel_package_is_private_p100_and_write_once(self):
        reference = (
            "https://github.com/ALBA7OOTH-Research-Lab/"
            "Musahhih/issues/200#issuecomment-123"
        )
        wrapper = build_wrapper(approved_commit="a" * 40, approval_reference=reference)
        metadata = build_metadata(
            kernel_id="owner/f2-f3-diagnostics-r01",
            safety_dataset_source="owner/safety-inputs",
            f1_safety_kernel_source="owner/f1-safety",
            f2_kernel_source="owner/f2-training",
            f3_kernel_source="owner/f3-training",
        )
        self.assertTrue(metadata["is_private"])
        self.assertEqual(metadata["machine_shape"], "NvidiaTeslaP100")
        self.assertEqual(len(metadata["kernel_sources"]), 3)
        self.assertIn("incomplete_time_budget", wrapper)
        self.assertIn(CONFIRMATION, wrapper)
        compile(wrapper, "generated_f2_f3_safety_wrapper.py", "exec")
        continuation = build_wrapper(
            approved_commit="a" * 40,
            approval_reference=reference,
            replicate=2,
            resume_summary_sha256="b" * 64,
        )
        self.assertIn("REPLICATE = 2", continuation)
        self.assertIn("expected exactly one authorized resume summary", continuation)
        continued_metadata = build_metadata(
            kernel_id="owner/f2-f3-diagnostics-r02",
            safety_dataset_source="owner/safety-inputs",
            f1_safety_kernel_source="owner/f1-safety",
            f2_kernel_source="owner/f2-training",
            f3_kernel_source="owner/f3-training",
            resume_kernel_source="owner/f2-f3-diagnostics-r01",
        )
        self.assertEqual(len(continued_metadata["kernel_sources"]), 4)
        with self.assertRaisesRegex(KernelPreparationError, "continuation"):
            build_wrapper(
                approved_commit="a" * 40,
                approval_reference=reference,
                replicate=2,
            )
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "package"
            write_package(target, wrapper, metadata)
            with self.assertRaises(KernelPreparationError):
                write_package(target, wrapper, metadata)

    def test_repository_local_outputs_must_be_ignored(self):
        self.assertEqual(validate_outputs_root(ROOT / "outputs"), (ROOT / "outputs").resolve())
        with self.assertRaisesRegex(EvaluationSafetyError, "ignored outputs"):
            validate_outputs_root(ROOT / "results")

    def test_evaluator_contains_no_training_or_prohibited_test_path(self):
        source = (ROOT / "scripts" / "run_f2_f3_safety_eval.py").read_text(encoding="utf-8")
        for forbidden in (
            "SFTTrainer",
            "trainer.train",
            "optimizer.step",
            "nahw_gec_test.jsonl",
            "QALB-Test",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
