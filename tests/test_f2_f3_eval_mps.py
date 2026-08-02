import subprocess
import unittest
from unittest.mock import patch

from scripts.f2_f3_eval_concurrency_utils import CONCURRENT_BATCH_SIZE, WORKER_COUNT
from scripts.f2_f3_eval_mps_utils import (
    CANARY_CONFIRMATION,
    validate_mps_activation,
)
from scripts.prepare_f2_f3_nautilus_eval_mps import build_mps_canary_job
from scripts.run_f2_f3_nautilus_eval_concurrency_canary import (
    SOAK_BATCHES,
    _mps_topology,
    validate_worker_summaries,
)


COMMIT = "a" * 40
APPROVAL = (
    "https://github.com/ALBA7OOTH-Research-Lab/"
    "Musahhih/issues/179#issuecomment-123456"
)


def worker_summaries() -> list[dict]:
    return [
        {
            "worker": worker,
            "status": "complete",
            "batch_size": CONCURRENT_BATCH_SIZE,
            "soak_batches": SOAK_BATCHES,
            "reference_output_sha256": "1" * 64,
            "durability_rows": CONCURRENT_BATCH_SIZE * SOAK_BATCHES,
            "per_row_fsync": True,
            "mps_pipe_configured": True,
            "mps_active_thread_percentage": 20,
            "contains_corpus_text": False,
        }
        for worker in range(WORKER_COUNT)
    ]


class EvaluationMpsTests(unittest.TestCase):
    def test_activation_is_exact_and_issue_specific(self):
        result = validate_mps_activation(
            approved_commit=COMMIT,
            actual_commit=COMMIT,
            approval_reference=APPROVAL,
            confirmation=CANARY_CONFIRMATION,
        )
        self.assertEqual(result["attempt_id"], "123456")
        with self.assertRaisesRegex(Exception, "issue #179"):
            validate_mps_activation(
                approved_commit=COMMIT,
                actual_commit=COMMIT,
                approval_reference=APPROVAL.replace("179", "177"),
                confirmation=CANARY_CONFIRMATION,
            )

    def test_mps_topology_requires_one_server_and_five_clients(self):
        responses = [
            subprocess.CompletedProcess([], 0, stdout="456\n", stderr=""),
            subprocess.CompletedProcess(
                [], 0, stdout="101\n102\n103\n104\n105\n", stderr=""
            ),
        ]
        with patch.dict(
            "os.environ",
            {
                "CUDA_MPS_PIPE_DIRECTORY": "/tmp/mps",
                "CUDA_MPS_ACTIVE_THREAD_PERCENTAGE": "20",
            },
        ), patch(
            "scripts.run_f2_f3_nautilus_eval_concurrency_canary.subprocess.run",
            side_effect=responses,
        ):
            result = _mps_topology()
        self.assertEqual(result["mps_server_count"], 1)
        self.assertEqual(result["mps_client_count"], 5)
        self.assertEqual(result["mps_active_thread_percentage"], 20)

    def test_worker_contract_requires_mps_markers(self):
        summaries = worker_summaries()
        self.assertTrue(
            validate_worker_summaries(summaries, mps_required=True)[
                "concurrent_worker_outputs_equivalent"
            ]
        )
        summaries[0]["mps_pipe_configured"] = False
        with self.assertRaisesRegex(Exception, "contract mismatch"):
            validate_worker_summaries(summaries, mps_required=True)

    def test_manifest_starts_and_stops_mps_without_test_mount(self):
        job = build_mps_canary_job(
            commit=COMMIT,
            approval_reference=APPROVAL,
            confirmation=CANARY_CONFIRMATION,
        )
        self.assertEqual(job["spec"]["backoffLimit"], 0)
        container = job["spec"]["template"]["spec"]["containers"][0]
        command = container["command"][-1]
        self.assertIn("nvidia-cuda-mps-control -d", command)
        self.assertIn("echo quit | nvidia-cuda-mps-control", command)
        self.assertIn("unset CUDA_MPS_ACTIVE_THREAD_PERCENTAGE", command)
        self.assertIn("CUDA_MPS_ACTIVE_THREAD_PERCENTAGE=20", command)
        self.assertLess(
            command.index("unset CUDA_MPS_ACTIVE_THREAD_PERCENTAGE"),
            command.index("nvidia-cuda-mps-control -d"),
        )
        self.assertLess(
            command.index("nvidia-cuda-mps-control -d"),
            command.index("export CUDA_MPS_ACTIVE_THREAD_PERCENTAGE=20"),
        )
        self.assertIn("--mps-canary", command)
        self.assertNotIn("/private/inputs", command)
        resources = container["resources"]
        self.assertEqual(resources["requests"], resources["limits"])
        self.assertEqual(resources["limits"]["memory"], "96Gi")
        products = job["spec"]["template"]["spec"]["affinity"][
            "nodeAffinity"
        ]["requiredDuringSchedulingIgnoredDuringExecution"]["nodeSelectorTerms"][0][
            "matchExpressions"
        ][
            0
        ][
            "values"
        ]
        self.assertEqual(len(products), 2)


if __name__ == "__main__":
    unittest.main()
