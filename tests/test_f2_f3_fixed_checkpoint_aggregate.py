import json
from pathlib import Path
import tempfile
import unittest

from scripts.aggregate_f2_f3_fixed_checkpoint_eval import (
    ARMS,
    build_policy_aggregate,
    validate_unselected_private_seed_result,
)
from scripts.f1_eval_utils import (
    BOOTSTRAP_SAMPLES,
    EXPECTED_TEST_RECORDS,
    EXPECTED_TEST_SHA256,
    paired_comparison,
    sha256_file,
)
from scripts.f2_f3_eval_rtx3090_utils import BATCH_SIZE, GPU_NAME
from scripts.f2_f3_fixed_checkpoint_aggregate_utils import (
    CONFIRMATION,
    validate_activation,
)
from scripts.f2_f3_multiseed_eval_utils import TRAINING_COMMIT
from scripts.f2_f3_nautilus_utils import SEEDS
from scripts.prepare_f2_f3_fixed_checkpoint_aggregate import build_manifest


COMMIT = "a" * 40
APPROVAL = (
    "https://github.com/ALBA7OOTH-Research-Lab/"
    "Musahhih/issues/196#issuecomment-123456"
)


def _adapter(arm: str, seed: int, checkpoint: str, selected: str) -> dict:
    return {
        "arm": arm,
        "seed": seed,
        "checkpoint": checkpoint,
        "checkpoint_policy": "unselected_epoch_checkpoint",
        "selected_checkpoint": selected,
        "adapter_model_bytes": 100,
        "adapter_model_sha256": ("1" if arm == "F2-P1" else "2") * 64,
        "adapter_config_sha256": ("3" if arm == "F2-P1" else "4") * 64,
        "training_commit": TRAINING_COMMIT,
        "adapter_merged": False,
        "contains_corpus_text": False,
    }


def _write_unselected(root: Path, seed: int, attempt_id: str, commit: str) -> tuple[Path, dict]:
    attempt = root / f"seed-{seed}" / "attempts" / attempt_id
    attempt.mkdir(parents=True)
    expected_adapters = {
        "F2-P1": _adapter("F2-P1", seed, "checkpoint-250", "checkpoint-125"),
        "F3-P1": _adapter("F3-P1", seed, "checkpoint-125", "checkpoint-250"),
    }
    rows = {}
    arms = {}
    for arm, correct in (("F2-P1", 100), ("F3-P1", 150)):
        values = [
            {"record_id": f"private-{index}", "exact_match": index < correct}
            for index in range(EXPECTED_TEST_RECORDS)
        ]
        path = attempt / f"{arm.lower()}_predictions.jsonl"
        path.write_text(
            "".join(json.dumps(value) + "\n" for value in values), encoding="utf-8"
        )
        rows[arm] = values
        arms[arm] = {
            "records": EXPECTED_TEST_RECORDS,
            "correct": correct,
            "accuracy": correct / EXPECTED_TEST_RECORDS,
            "predictions_sha256": sha256_file(path),
        }
    paired = paired_comparison(
        rows["F2-P1"], rows["F3-P1"], bootstrap_samples=BOOTSTRAP_SAMPLES, seed=seed
    )
    summary = {
        "run_status": "complete",
        "seed": seed,
        "attempt_id": attempt_id,
        "approved_commit": commit,
        "training_commit": TRAINING_COMMIT,
        "records": EXPECTED_TEST_RECORDS,
        "test_sha256": EXPECTED_TEST_SHA256,
        "batch_size": BATCH_SIZE,
        "inference_gpu_required": GPU_NAME,
        "pretest_gate": {"status": "passed"},
        "automatic_retry": False,
        "training_executed": False,
        "qalb_test_used": False,
        "prompt_or_parser_changed": False,
        "development_values_exposed": False,
        "contains_corpus_text": False,
        "adapters": expected_adapters,
        "arms": arms,
        "comparison": {
            "f3_minus_f2": paired["accuracy_difference_adapter_minus_baseline"],
            "f2_wrong_f3_right": paired["baseline_wrong_adapter_right"],
            "f2_right_f3_wrong": paired["baseline_right_adapter_wrong"],
            "mcnemar_two_sided_exact_p_value": paired["mcnemar_two_sided_exact_p_value"],
            "paired_bootstrap_95_percentile_ci": paired[
                "paired_bootstrap_95_percentile_ci"
            ],
            "bootstrap_samples": BOOTSTRAP_SAMPLES,
            "bootstrap_seed": seed,
        },
    }
    (attempt / "public_summary.json").write_text(
        json.dumps(summary) + "\n", encoding="utf-8"
    )
    return attempt, expected_adapters


def _source(seed: int, *, selected: bool) -> dict:
    if selected:
        checkpoints = {"F2-P1": "checkpoint-125", "F3-P1": "checkpoint-250"}
        correct = {"F2-P1": 100 + seed % 3, "F3-P1": 150 + seed % 4}
        attempt = "selected"
    else:
        checkpoints = {"F2-P1": "checkpoint-250", "F3-P1": "checkpoint-125"}
        correct = {"F2-P1": 110 + seed % 3, "F3-P1": 140 + seed % 4}
        attempt = "unselected"
    adapters = {
        arm: {"selected_checkpoint": "checkpoint-125" if arm == "F2-P1" else "checkpoint-250", **({} if selected else {"checkpoint": checkpoints[arm]})}
        for arm in ARMS
    }
    return {
        "summary": {
            "attempt_id": attempt,
            "adapters": adapters,
            "arms": {
                arm: {
                    "correct": correct[arm],
                    "accuracy": correct[arm] / EXPECTED_TEST_RECORDS,
                }
                for arm in ARMS
            },
        },
        "prediction_sha256": {arm: ("a" if arm == "F2-P1" else "b") * 64 for arm in ARMS},
    }


class FixedCheckpointAggregateTests(unittest.TestCase):
    def test_activation_and_manifest_are_issue_specific_cpu_only_write_once(self):
        activation = validate_activation(
            approved_commit=COMMIT,
            actual_commit=COMMIT,
            approval_reference=APPROVAL,
            confirmation=CONFIRMATION,
        )
        self.assertEqual(activation["attempt_id"], "123456")
        manifest = build_manifest(
            commit=COMMIT, approval_reference=APPROVAL, confirmation=CONFIRMATION
        )
        job = manifest["items"][0]
        self.assertEqual(job["spec"]["backoffLimit"], 0)
        self.assertEqual(job["spec"]["activeDeadlineSeconds"], 3600)
        self.assertNotIn("nvidia.com", str(job).lower())
        self.assertIn("test ! -e", str(job))
        self.assertIn("5155890101", str(job))
        self.assertIn("5157509573,5158062318", str(job))

    def test_unselected_validation_recomputes_private_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            attempt, expected = _write_unselected(root, 3407, "repair", COMMIT)
            result = validate_unselected_private_seed_result(
                root,
                seed=3407,
                attempt_id="repair",
                evaluation_commit=COMMIT,
                expected_adapters=expected,
            )
            self.assertEqual(set(result["prediction_sha256"]), set(ARMS))
            path = attempt / "f2-p1_predictions.jsonl"
            rows = path.read_text(encoding="utf-8").splitlines()
            value = json.loads(rows[0])
            value["record_id"] = "changed-private-id"
            rows[0] = json.dumps(value)
            path.write_text("\n".join(rows) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(Exception, "metric/hash mismatch"):
                validate_unselected_private_seed_result(
                    root,
                    seed=3407,
                    attempt_id="repair",
                    evaluation_commit=COMMIT,
                    expected_adapters=expected,
                )

    def test_policy_aggregate_uses_each_checkpoint_once_and_keeps_selected_policy(self):
        validated = [
            {"seed": seed, "selected": _source(seed, selected=True), "unselected": _source(seed, selected=False)}
            for seed in SEEDS
        ]
        result = build_policy_aggregate(validated)
        self.assertEqual(len(result["per_seed"]), 5)
        first = result["per_seed"][0]["policies"]
        self.assertEqual(first["fixed_epoch_1"]["arms"]["F2-P1"]["source_kind"], "selected")
        self.assertEqual(first["fixed_epoch_1"]["arms"]["F3-P1"]["source_kind"], "unselected")
        self.assertEqual(first["fixed_epoch_2"]["arms"]["F2-P1"]["source_kind"], "unselected")
        self.assertEqual(first["fixed_epoch_2"]["arms"]["F3-P1"]["source_kind"], "selected")
        self.assertEqual(first["dev_selected"]["arms"]["F2-P1"]["source_kind"], "selected")
        self.assertEqual(len(result["compact_table"]), 3)


if __name__ == "__main__":
    unittest.main()
