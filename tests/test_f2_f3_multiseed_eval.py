import hashlib
import inspect
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from scripts.f1_eval_utils import EXPECTED_TEST_RECORDS, EXPECTED_TEST_SHA256
from scripts.f2_f3_multiseed_eval_utils import (
    AGGREGATE_CONFIRMATION,
    EVALUATION_CONFIRMATION,
    MultiSeedEvaluationError,
    TEST_STAGING_CONFIRMATION,
    TRAINING_COMMIT,
    aggregate_seed_summaries,
    validate_activation,
    validate_training_pair,
)
from scripts.f2_f3_nautilus_utils import SEEDS, arm_order
from scripts.prepare_f2_f3_nautilus_multiseed_eval import build_manifest
from scripts.run_f2_f3_final_eval import AdapterGenerator
from scripts.run_f2_f3_nautilus_multiseed_eval import (
    SAFE_STOP_ELAPSED_SECONDS,
    _load_resume,
    execute,
    validate_test_staging,
)
from scripts.run_f2_f3_final_eval import TimeBudgetExhausted
from scripts.run_f2_f3_nautilus_pair import checkpoint_identity


COMMIT = "a" * 40
APPROVAL = (
    "https://github.com/ALBA7OOTH-Research-Lab/"
    "Musahhih/issues/171#issuecomment-123456"
)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")


class MultiSeedEvaluationTests(unittest.TestCase):
    def _training_pair(self, root: Path, seed: int) -> Path:
        seed_root = root / f"seed-{seed}"
        order = arm_order(seed)
        for position, arm in enumerate(order, 1):
            arm_root = seed_root / arm.lower()
            identities = []
            for step in (125, 250):
                checkpoint = arm_root / f"checkpoint-{step}"
                checkpoint.mkdir(parents=True)
                (checkpoint / "adapter_model.safetensors").write_bytes(
                    f"{seed}-{arm}-{step}".encode("ascii")
                )
                (checkpoint / "adapter_config.json").write_text(
                    "{}\n", encoding="utf-8"
                )
                identities.append(checkpoint_identity(checkpoint))
            selected = "checkpoint-125" if arm == "F2-P1" else "checkpoint-250"
            write_json(
                arm_root / "checkpoint_selection.json",
                {
                    "arm": arm,
                    "seed": seed,
                    "workflow_commit": TRAINING_COMMIT,
                    "precision": "float16",
                    "selected_checkpoint": selected,
                    "checkpoints": identities,
                    "contains_corpus_text": False,
                },
            )
            write_json(
                seed_root / f"{position}0_{arm.lower()}_complete.json",
                {
                    "arm": arm,
                    "seed": seed,
                    "selected_checkpoint": selected,
                    "contains_corpus_text": False,
                },
            )
        write_json(
            seed_root / "99_pair_complete.json",
            {
                "seed": seed,
                "arm_order": list(order),
                "completed_arms": list(order),
                "workflow_commit": TRAINING_COMMIT,
                "attempt_id": "5136464333",
                "contains_corpus_text": False,
                "nahw_passage_used": False,
                "qalb_test_used": False,
            },
        )
        return seed_root

    def test_activation_separates_all_three_fresh_go_stages(self):
        for stage, seed, confirmation in (
            ("test-staging", None, TEST_STAGING_CONFIRMATION),
            ("paired-evaluation", 3407, EVALUATION_CONFIRMATION),
            ("aggregate-evaluation", None, AGGREGATE_CONFIRMATION),
        ):
            with self.subTest(stage=stage):
                result = validate_activation(
                    stage=stage,
                    seed=seed,
                    approved_commit=COMMIT,
                    actual_commit=COMMIT,
                    approval_reference=APPROVAL,
                    confirmation=confirmation,
                )
                self.assertEqual(result["seed"], seed)
        with self.assertRaisesRegex(MultiSeedEvaluationError, "issue #171"):
            validate_activation(
                stage="paired-evaluation",
                seed=3407,
                approved_commit=COMMIT,
                actual_commit=COMMIT,
                approval_reference=APPROVAL.replace("171", "167"),
                confirmation=EVALUATION_CONFIRMATION,
            )

    def test_training_pair_validation_hashes_both_epochs_and_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            seed_root = self._training_pair(Path(directory), 3408)
            result = validate_training_pair(seed_root, 3408)
            self.assertEqual(set(result), {"F2-P1", "F3-P1"})
            self.assertEqual(result["F2-P1"]["selected_checkpoint"], "checkpoint-125")
            self.assertNotIn("evaluations", str(result))
            selected = result["F2-P1"]["adapter_path"]
            (selected / "adapter_model.safetensors").write_bytes(b"tampered")
            with self.assertRaisesRegex(
                MultiSeedEvaluationError, "checkpoint validation"
            ):
                validate_training_pair(seed_root, 3408)

    def test_test_staging_manifest_is_exact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(
                root / "staging_manifest.json",
                {
                    "status": "complete",
                    "filename": "nahw_gec_test.jsonl",
                    "records": EXPECTED_TEST_RECORDS,
                    "sha256": EXPECTED_TEST_SHA256,
                    "contains_corpus_text": False,
                },
            )
            self.assertEqual(validate_test_staging(root)["records"], 511)
            write_json(root / "wrong.json", {})
            (root / "staging_manifest.json").write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(Exception, "contract mismatch"):
                validate_test_staging(root)

    def test_manifest_stages_are_separate_and_fail_closed(self):
        staging = build_manifest(
            stage="test-staging",
            commit=COMMIT,
            approval_reference=APPROVAL,
            confirmation=TEST_STAGING_CONFIRMATION,
        )
        self.assertEqual(len(staging["items"]), 1)
        self.assertEqual(staging["items"][0]["kind"], "Pod")
        staging_text = str(staging).lower()
        self.assertNotIn("nvidia.com", staging_text)
        self.assertEqual(
            staging["items"][0]["spec"]["volumes"][0][
                "persistentVolumeClaim"
            ]["claimName"],
            "musahhih-f2-f3-replication",
        )
        self.assertIn(EXPECTED_TEST_SHA256, staging_text)

        evaluation = build_manifest(
            stage="paired-evaluation",
            commit=COMMIT,
            approval_reference=APPROVAL,
            confirmation=EVALUATION_CONFIRMATION,
        )
        self.assertEqual(len(evaluation["items"]), 5)
        self.assertEqual(
            {job["metadata"]["labels"]["musahhih.openai/seed"] for job in evaluation["items"]},
            {str(seed) for seed in SEEDS},
        )
        for job in evaluation["items"]:
            self.assertEqual(job["spec"]["backoffLimit"], 0)
            container = job["spec"]["template"]["spec"]["containers"][0]
            self.assertEqual(container["resources"]["limits"]["nvidia.com/a100"], "1")
            self.assertIn("kernel_start", str(container))
            self.assertIn("MUSAHHIH_RESUME_ATTEMPT_ID", str(container))

        aggregate = build_manifest(
            stage="aggregate-evaluation",
            commit=COMMIT,
            approval_reference=APPROVAL,
            confirmation=AGGREGATE_CONFIRMATION,
            source_attempt_id="123456",
            evaluation_commit=COMMIT,
        )
        self.assertEqual(len(aggregate["items"]), 1)
        self.assertNotIn("nvidia.com", str(aggregate).lower())
        self.assertEqual(aggregate["items"][0]["spec"]["backoffLimit"], 0)
        self.assertIn("PIPESTATUS", str(aggregate))
        self.assertIn("automatic_retry", str(aggregate))

    def test_resume_accepts_only_one_fsynced_orphan_row(self):
        record = {
            "id": "n1",
            "passage_id": "p1",
            "source": "Nahw-Passage",
            "split": "test",
            "passage": "private passage",
            "error": "private error",
            "gold_correction": "private correction",
            "prompt": "private prompt",
        }
        row = {
            "record_id": "n1",
            "passage_id": "p1",
            "source": "Nahw-Passage",
            "split": "test",
            "passage": "private passage",
            "erroneous_word": "private error",
            "gold_correction": "private correction",
            "full_prompt": "private prompt",
            "raw_model_response": "response",
            "parsed_correction": "private correction",
            "parsing_warnings": [],
            "exact_match": True,
        }
        adapter_meta = {
            "F2-P1": {"hash": "f2", "contains_corpus_text": False},
            "F3-P1": {"hash": "f3", "contains_corpus_text": False},
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "f2-p1_predictions.jsonl").write_text(
                json.dumps(row) + "\n", encoding="utf-8"
            )
            write_json(
                root / "public_summary.json",
                {
                    "run_status": "incomplete_time_budget",
                    "seed": 3407,
                    "approved_commit": COMMIT,
                    "metrics_reported": False,
                },
            )
            write_json(
                root / "progress.json",
                {
                    "schema_version": 1,
                    "seed": 3407,
                    "approved_commit": COMMIT,
                    "adapters": adapter_meta,
                    "test_sha256": EXPECTED_TEST_SHA256,
                    "completed_records": {"F2-P1": 0, "F3-P1": 0},
                    "prediction_sha256": {"F2-P1": None, "F3-P1": None},
                    "runtime": {},
                    "contains_corpus_text": False,
                },
            )
            prefixes, _ = _load_resume(
                root,
                records=[record],
                seed=3407,
                approved_commit=COMMIT,
                adapter_meta=adapter_meta,
            )
            self.assertEqual(len(prefixes["F2-P1"]), 1)
            with (root / "f2-p1_predictions.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row) + "\n")
            with self.assertRaisesRegex(Exception, "count mismatch"):
                _load_resume(
                    root,
                    records=[record, record],
                    seed=3407,
                    approved_commit=COMMIT,
                    adapter_meta=adapter_meta,
                )

    def test_frozen_aggregate_uses_sample_sd_and_all_five_seeds(self):
        summaries = []
        for index, seed in enumerate(SEEDS):
            f2_correct = 100 + index
            f3_correct = 150 + 2 * index
            summaries.append(
                {
                    "run_status": "complete",
                    "seed": seed,
                    "records": 511,
                    "test_sha256": EXPECTED_TEST_SHA256,
                    "arms": {
                        "F2-P1": {
                            "records": 511,
                            "correct": f2_correct,
                            "accuracy": f2_correct / 511,
                        },
                        "F3-P1": {
                            "records": 511,
                            "correct": f3_correct,
                            "accuracy": f3_correct / 511,
                        },
                    },
                    "comparison": {
                        "f3_minus_f2": (f3_correct - f2_correct) / 511
                    },
                    "contains_corpus_text": False,
                }
            )
        result = aggregate_seed_summaries(summaries)
        self.assertEqual(len(result["per_seed"]), 5)
        self.assertGreater(result["F3-P1_minus_F2-P1"]["sample_sd"], 0)
        self.assertIn("n-1", result["standard_deviation_definition"])
        with self.assertRaisesRegex(MultiSeedEvaluationError, "all five"):
            aggregate_seed_summaries(summaries[:-1])

    def test_inference_gpu_requirement_defaults_to_original_p100(self):
        original = AdapterGenerator(Path("adapter"))
        replication = AdapterGenerator(Path("adapter"), required_gpu="A100")
        self.assertEqual(original.required_gpu, "P100")
        self.assertEqual(replication.required_gpu, "A100")
        source = inspect.getsource(AdapterGenerator.load)
        self.assertIn("self.required_gpu", source)
        self.assertEqual(SAFE_STOP_ELAPSED_SECONDS, 64_800)

    def test_execute_writes_complete_corpus_free_summary_without_adapter_paths(self):
        records = [{"id": f"n{index}"} for index in range(511)]
        adapter_meta = {
            "F2-P1": {
                "adapter_path": Path("private-f2"),
                "training_commit": TRAINING_COMMIT,
                "adapter_model_sha256": "2" * 64,
                "contains_corpus_text": False,
            },
            "F3-P1": {
                "adapter_path": Path("private-f3"),
                "training_commit": TRAINING_COMMIT,
                "adapter_model_sha256": "3" * 64,
                "contains_corpus_text": False,
            },
        }

        def fake_generate(*, arm, records, predictions_path, progress_callback, **_):
            rows = []
            with predictions_path.open("x", encoding="utf-8") as stream:
                for index, record in enumerate(records):
                    exact = index < (100 if arm == "F2-P1" else 150)
                    row = {
                        "record_id": record["id"],
                        "exact_match": exact,
                        "parsed_correction": "x",
                        "parsing_warnings": [],
                    }
                    rows.append(row)
                    stream.write(json.dumps(row) + "\n")
            progress_callback(len(rows), {"gpu": "A100"})
            return rows, {"gpu": "A100"}

        activation = {
            "seed": 3407,
            "approved_commit": COMMIT,
            "approval_reference": APPROVAL,
            "attempt_id": "123456",
        }
        with tempfile.TemporaryDirectory() as directory, patch(
            "scripts.run_f2_f3_nautilus_multiseed_eval._generate_arm",
            side_effect=fake_generate,
        ):
            summary = execute(
                activation=activation,
                records=records,
                adapter_meta=adapter_meta,
                output_root=Path(directory),
                resume_root=None,
                kernel_start_epoch_seconds=time.time(),
            )
            self.assertEqual(summary["run_status"], "complete")
            self.assertEqual(summary["arms"]["F2-P1"]["correct"], 100)
            self.assertEqual(summary["arms"]["F3-P1"]["correct"], 150)
            self.assertNotIn("adapter_path", str(summary))
            self.assertFalse(summary["contains_corpus_text"])

    def test_execute_safe_stop_is_metric_free_and_requires_fresh_go(self):
        activation = {
            "seed": 3407,
            "approved_commit": COMMIT,
            "approval_reference": APPROVAL,
            "attempt_id": "123456",
        }
        adapter_meta = {
            arm: {
                "adapter_path": Path(f"private-{arm}"),
                "training_commit": TRAINING_COMMIT,
                "contains_corpus_text": False,
            }
            for arm in ("F2-P1", "F3-P1")
        }
        with tempfile.TemporaryDirectory() as directory, patch(
            "scripts.run_f2_f3_nautilus_multiseed_eval._generate_arm",
            side_effect=TimeBudgetExhausted,
        ):
            summary = execute(
                activation=activation,
                records=[{"id": "n1"}],
                adapter_meta=adapter_meta,
                output_root=Path(directory),
                resume_root=None,
                kernel_start_epoch_seconds=time.time(),
            )
            self.assertEqual(summary["run_status"], "incomplete_time_budget")
            self.assertFalse(summary["metrics_reported"])
            self.assertTrue(summary["resume_requires_fresh_authorization"])


if __name__ == "__main__":
    unittest.main()
