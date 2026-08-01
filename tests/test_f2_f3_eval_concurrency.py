import json
from pathlib import Path
import tempfile
import unittest

from scripts.f2_f3_eval_concurrency_utils import (
    CANARY_CONFIRMATION,
    CONCURRENT_BATCH_SIZE,
    CONTINUATION_CONFIRMATION,
    INCOMPLETE_ARMS,
    WORKER_COUNT,
    validate_concurrency_activation,
)
from scripts.prepare_f2_f3_nautilus_eval_concurrency import build_manifest
from scripts.run_f2_f3_nautilus_eval_concurrency_canary import (
    SOAK_BATCHES,
    validate_worker_summaries,
)
from scripts.supervise_f2_f3_nautilus_eval_concurrency import (
    validate_concurrency_canary,
)


COMMIT = "a" * 40
APPROVAL = (
    "https://github.com/ALBA7OOTH-Research-Lab/"
    "Musahhih/issues/177#issuecomment-123456"
)


class EvaluationConcurrencyTests(unittest.TestCase):
    def test_activation_is_issue_177_specific(self):
        canary = validate_concurrency_activation(
            stage="concurrency-canary",
            seed=None,
            approved_commit=COMMIT,
            actual_commit=COMMIT,
            approval_reference=APPROVAL,
            confirmation=CANARY_CONFIRMATION,
        )
        self.assertEqual(canary["attempt_id"], "123456")
        continuation = validate_concurrency_activation(
            stage="continuation",
            seed=3407,
            approved_commit=COMMIT,
            actual_commit=COMMIT,
            approval_reference=APPROVAL,
            confirmation=CONTINUATION_CONFIRMATION,
        )
        self.assertEqual(continuation["source_attempt_id"], "5144097114")
        with self.assertRaisesRegex(Exception, "issue #177"):
            validate_concurrency_activation(
                stage="concurrency-canary",
                seed=None,
                approved_commit=COMMIT,
                actual_commit=COMMIT,
                approval_reference=APPROVAL.replace("177", "175"),
                confirmation=CANARY_CONFIRMATION,
            )

    def test_exactly_one_incomplete_arm_per_seed(self):
        self.assertEqual(
            INCOMPLETE_ARMS,
            {
                3407: "F3-P1",
                3408: "F2-P1",
                3409: "F3-P1",
                3410: "F2-P1",
                3411: "F3-P1",
            },
        )

    def test_worker_evidence_requires_five_equal_batch16_outputs(self):
        rows = CONCURRENT_BATCH_SIZE * SOAK_BATCHES
        summaries = [
            {
                "worker": worker,
                "status": "complete",
                "batch_size": CONCURRENT_BATCH_SIZE,
                "soak_batches": SOAK_BATCHES,
                "reference_output_sha256": "1" * 64,
                "durability_rows": rows,
                "per_row_fsync": True,
                "contains_corpus_text": False,
            }
            for worker in range(WORKER_COUNT)
        ]
        evidence = validate_worker_summaries(summaries)
        self.assertEqual(evidence["worker_count"], 5)
        self.assertEqual(evidence["synthetic_generations"], rows * 5)
        summaries[-1]["reference_output_sha256"] = "2" * 64
        with self.assertRaisesRegex(Exception, "outputs differ"):
            validate_worker_summaries(summaries)

    def test_canary_contract_requires_utilization_and_memory_headroom(self):
        payload = {
            "status": "complete",
            "approved_commit": COMMIT,
            "worker_count": WORKER_COUNT,
            "batch_size": CONCURRENT_BATCH_SIZE,
            "concurrent_worker_outputs_equivalent": True,
            "per_row_fsync": True,
            "mean_gpu_utilization_percent": 70,
            "peak_gpu_memory_fraction": 0.6,
            "peak_host_memory_fraction": 0.5,
            "nahw_passage_used": False,
            "metric_computed": False,
            "contains_corpus_text": False,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "public_summary.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual(validate_concurrency_canary(path.parent, COMMIT)["status"], "complete")
            payload["mean_gpu_utilization_percent"] = 39.9
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(Exception, "contract mismatch"):
                validate_concurrency_canary(path.parent, COMMIT)

    def test_manifests_use_one_80gb_a100_job_and_no_retry(self):
        canary = build_manifest(
            stage="concurrency-canary",
            commit=COMMIT,
            approval_reference=APPROVAL,
            confirmation=CANARY_CONFIRMATION,
        )
        self.assertEqual(len(canary["items"]), 1)
        self.assertNotIn("/private/inputs", str(canary))
        continuation = build_manifest(
            stage="continuation",
            commit=COMMIT,
            approval_reference=APPROVAL,
            confirmation=CONTINUATION_CONFIRMATION,
            canary_attempt_id="123455",
        )
        self.assertEqual(len(continuation["items"]), 1)
        job = continuation["items"][0]
        self.assertEqual(job["spec"]["backoffLimit"], 0)
        pod = job["spec"]["template"]["spec"]
        products = pod["affinity"]["nodeAffinity"][
            "requiredDuringSchedulingIgnoredDuringExecution"
        ]["nodeSelectorTerms"][0]["matchExpressions"][0]["values"]
        self.assertEqual(
            set(products), {"NVIDIA-A100-SXM4-80GB", "NVIDIA-A100-80GB-PCIe"}
        )
        resources = pod["containers"][0]["resources"]
        self.assertEqual(resources["requests"], resources["limits"])
        self.assertEqual(resources["limits"]["nvidia.com/a100"], "1")
        self.assertEqual(resources["limits"]["memory"], "96Gi")
        self.assertIn("supervise_f2_f3_nautilus_eval_concurrency", str(job))


if __name__ == "__main__":
    unittest.main()
