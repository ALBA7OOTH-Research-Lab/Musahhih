import json
from pathlib import Path
import tempfile
import unittest

from scripts.aggregate_f2_f3_rtx3090_eval import validate_private_seed_result
from scripts.f1_eval_utils import (
    BOOTSTRAP_SAMPLES,
    EXPECTED_TEST_RECORDS,
    EXPECTED_TEST_SHA256,
    paired_comparison,
    sha256_file,
)
from scripts.f2_f3_eval_rtx3090_utils import BATCH_SIZE, GPU_NAME
from scripts.f2_f3_rtx3090_aggregate_utils import (
    CONFIRMATION,
    EVALUATION_COMMIT,
    SOURCE_ATTEMPT_ID,
    validate_activation,
)
from scripts.prepare_f2_f3_rtx3090_aggregate import build_manifest


COMMIT = "a" * 40
APPROVAL = (
    "https://github.com/ALBA7OOTH-Research-Lab/"
    "Musahhih/issues/185#issuecomment-123456"
)


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")


def _write_seed(root: Path, seed: int) -> Path:
    attempt = root / f"seed-{seed}" / "attempts" / SOURCE_ATTEMPT_ID
    attempt.mkdir(parents=True)
    rows = {}
    arms = {}
    for arm, correct in (("F2-P1", 100), ("F3-P1", 150)):
        values = [
            {
                "record_id": f"private-{index}",
                "exact_match": index < correct,
                "raw_model_response": "private",
            }
            for index in range(EXPECTED_TEST_RECORDS)
        ]
        path = attempt / f"{arm.lower()}_predictions.jsonl"
        path.write_text(
            "".join(json.dumps(value) + "\n" for value in values),
            encoding="utf-8",
        )
        rows[arm] = values
        arms[arm] = {
            "records": EXPECTED_TEST_RECORDS,
            "correct": correct,
            "accuracy": correct / EXPECTED_TEST_RECORDS,
            "predictions_sha256": sha256_file(path),
        }
    paired = paired_comparison(
        rows["F2-P1"],
        rows["F3-P1"],
        bootstrap_samples=BOOTSTRAP_SAMPLES,
        seed=seed,
    )
    _write_json(
        attempt / "public_summary.json",
        {
            "run_status": "complete",
            "seed": seed,
            "attempt_id": SOURCE_ATTEMPT_ID,
            "approved_commit": EVALUATION_COMMIT,
            "records": EXPECTED_TEST_RECORDS,
            "test_sha256": EXPECTED_TEST_SHA256,
            "batch_size": BATCH_SIZE,
            "inference_gpu_required": GPU_NAME,
            "pretest_gate": {"status": "passed"},
            "automatic_retry": False,
            "training_executed": False,
            "qalb_test_used": False,
            "arms": arms,
            "comparison": {
                "f3_minus_f2": paired[
                    "accuracy_difference_adapter_minus_baseline"
                ],
                "f2_wrong_f3_right": paired["baseline_wrong_adapter_right"],
                "f2_right_f3_wrong": paired["baseline_right_adapter_wrong"],
                "mcnemar_two_sided_exact_p_value": paired[
                    "mcnemar_two_sided_exact_p_value"
                ],
                "paired_bootstrap_95_percentile_ci": paired[
                    "paired_bootstrap_95_percentile_ci"
                ],
                "bootstrap_samples": BOOTSTRAP_SAMPLES,
                "bootstrap_seed": seed,
            },
            "contains_corpus_text": False,
        },
    )
    return attempt


class Rtx3090AggregateTests(unittest.TestCase):
    def test_activation_requires_issue_185_exact_commit(self):
        result = validate_activation(
            approved_commit=COMMIT,
            actual_commit=COMMIT,
            approval_reference=APPROVAL,
            confirmation=CONFIRMATION,
        )
        self.assertEqual(result["source_attempt_id"], SOURCE_ATTEMPT_ID)
        with self.assertRaisesRegex(Exception, "issue #185"):
            validate_activation(
                approved_commit=COMMIT,
                actual_commit=COMMIT,
                approval_reference=APPROVAL.replace("185", "183"),
                confirmation=CONFIRMATION,
            )

    def test_manifest_is_one_cpu_only_write_once_job(self):
        manifest = build_manifest(
            commit=COMMIT,
            approval_reference=APPROVAL,
            confirmation=CONFIRMATION,
        )
        self.assertEqual(len(manifest["items"]), 1)
        job = manifest["items"][0]
        self.assertEqual(job["spec"]["backoffLimit"], 0)
        self.assertEqual(job["spec"]["activeDeadlineSeconds"], 3600)
        self.assertNotIn("nvidia.com", str(job).lower())
        self.assertIn("test ! -e", str(job))
        self.assertIn(SOURCE_ATTEMPT_ID, str(job))
        self.assertIn(EVALUATION_COMMIT, str(job))

    def test_private_seed_validation_recomputes_hash_count_and_statistics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            attempt = _write_seed(root, 3407)
            result = validate_private_seed_result(root, seed=3407)
            self.assertEqual(
                len(result["record_order_sha256"]), 64
            )
            self.assertEqual(set(result["prediction_sha256"]), {"F2-P1", "F3-P1"})
            f3_path = attempt / "f3-p1_predictions.jsonl"
            rows = f3_path.read_text(encoding="utf-8").splitlines()
            value = json.loads(rows[0])
            value["record_id"] = "different-private-id"
            rows[0] = json.dumps(value)
            f3_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(Exception, "metric/hash mismatch"):
                validate_private_seed_result(root, seed=3407)


if __name__ == "__main__":
    unittest.main()
