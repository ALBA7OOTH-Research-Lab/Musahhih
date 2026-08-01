import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.f2_f3_eval_repair_utils import (
    CANARY_CONFIRMATION,
    CONTINUATION_CONFIRMATION,
    SOURCE_ATTEMPT_ID,
    SOURCE_EVALUATION_COMMIT,
    SOURCE_PROGRESS_COUNTS,
    validate_interrupted_source_identity,
    validate_repair_activation,
)
from scripts.prepare_f2_f3_nautilus_eval_repair import build_manifest
from scripts.run_f2_f3_nautilus_eval_repair_canary import run_canary
from scripts.run_f2_f3_nautilus_multiseed_eval import (
    REPAIR_BATCH_SIZE,
    _generate_arm_batched,
    _load_resume,
)
from scripts.run_f2_f3_final_eval import KernelTimeBudget
from scripts.supervise_f2_f3_nautilus_eval_repair import (
    supervise,
    validate_canary_summary,
)


COMMIT = "a" * 40
APPROVAL = (
    "https://github.com/ALBA7OOTH-Research-Lab/"
    "Musahhih/issues/173#issuecomment-123456"
)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def record(index: int) -> dict:
    return {
        "id": f"n{index}",
        "passage_id": f"p{index}",
        "source": "synthetic-test-double",
        "split": "test-double",
        "passage": f"passage-{index}",
        "error": f"error-{index}",
        "gold_correction": f"gold-{index}",
        "prompt": f"prompt-{index}",
    }


def prediction(item: dict) -> dict:
    return {
        "record_id": item["id"],
        "passage_id": item["passage_id"],
        "source": item["source"],
        "split": item["split"],
        "passage": item["passage"],
        "erroneous_word": item["error"],
        "gold_correction": item["gold_correction"],
        "full_prompt": item["prompt"],
        "raw_model_response": item["gold_correction"],
        "parsed_correction": item["gold_correction"],
        "exact_match": True,
        "parsing_warnings": [],
    }


class EvaluationRepairTests(unittest.TestCase):
    def test_activation_and_interrupted_source_are_exact(self):
        canary = validate_repair_activation(
            stage="utilization-canary",
            seed=None,
            approved_commit=COMMIT,
            actual_commit=COMMIT,
            approval_reference=APPROVAL,
            confirmation=CANARY_CONFIRMATION,
        )
        self.assertEqual(canary["attempt_id"], "123456")
        continuation = validate_repair_activation(
            stage="continuation",
            seed=3408,
            approved_commit=COMMIT,
            actual_commit=COMMIT,
            approval_reference=APPROVAL,
            confirmation=CONTINUATION_CONFIRMATION,
        )
        self.assertEqual(continuation["source_attempt_id"], SOURCE_ATTEMPT_ID)
        source = validate_interrupted_source_identity(
            seed=3408,
            source_attempt_id=SOURCE_ATTEMPT_ID,
            source_commit=SOURCE_EVALUATION_COMMIT,
        )
        self.assertEqual(source["recorded_counts"], {"F2-P1": 236, "F3-P1": 511})
        with self.assertRaisesRegex(Exception, "issue #173"):
            validate_repair_activation(
                stage="continuation",
                seed=3408,
                approved_commit=COMMIT,
                actual_commit=COMMIT,
                approval_reference=APPROVAL.replace("173", "171"),
                confirmation=CONTINUATION_CONFIRMATION,
            )

    def test_interrupted_prefix_resumes_without_missing_summary(self):
        records = [record(index) for index in range(511)]
        adapter_meta = {
            "F2-P1": {"adapter_model_sha256": "2" * 64},
            "F3-P1": {"adapter_model_sha256": "3" * 64},
        }
        source = validate_interrupted_source_identity(
            seed=3408,
            source_attempt_id=SOURCE_ATTEMPT_ID,
            source_commit=SOURCE_EVALUATION_COMMIT,
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / SOURCE_ATTEMPT_ID
            root.mkdir()
            for arm, count in SOURCE_PROGRESS_COUNTS[3408].items():
                path = root / f"{arm.lower()}_predictions.jsonl"
                with path.open("w", encoding="utf-8") as stream:
                    for item in records[:count]:
                        stream.write(json.dumps(prediction(item)) + "\n")
            from scripts.f1_eval_utils import sha256_file

            write_json(
                root / "progress.json",
                {
                    "schema_version": 1,
                    "status": "running",
                    "seed": 3408,
                    "approved_commit": SOURCE_EVALUATION_COMMIT,
                    "attempt_id": SOURCE_ATTEMPT_ID,
                    "completed_records": SOURCE_PROGRESS_COUNTS[3408],
                    "prediction_sha256": {
                        arm: sha256_file(root / f"{arm.lower()}_predictions.jsonl")
                        for arm in ("F2-P1", "F3-P1")
                    },
                    "runtime": {},
                    "adapters": adapter_meta,
                    "test_sha256": (
                        "acb3cfd204b35d5415532fbd32a4a5231b553fae329ab8f48e8454609e10279b"
                    ),
                    "contains_corpus_text": False,
                },
            )
            prefixes, _ = _load_resume(
                root,
                records=records,
                seed=3408,
                approved_commit=COMMIT,
                adapter_meta=adapter_meta,
                resume_source_commit=SOURCE_EVALUATION_COMMIT,
                interrupted_source=source,
            )
            self.assertEqual(len(prefixes["F2-P1"]), 236)
            self.assertEqual(len(prefixes["F3-P1"]), 511)
            with self.assertRaisesRegex(Exception, "source contract"):
                _load_resume(
                    root,
                    records=records,
                    seed=3408,
                    approved_commit=COMMIT,
                    adapter_meta=adapter_meta,
                    resume_source_commit=COMMIT,
                    interrupted_source=source,
                )

    def test_batched_generation_keeps_per_row_progress(self):
        records = [record(index) for index in range(511)]

        class FakeGenerator:
            def __init__(self, _adapter):
                self.runtime = {"gpu": "A100"}
                self.model = None
                self.processor = None

            def generate_batch(self, prompts):
                return [prompt.replace("prompt", "gold") for prompt in prompts]

        progress = []
        with tempfile.TemporaryDirectory() as directory:
            rows, _ = _generate_arm_batched(
                arm="F2-P1",
                adapter=Path("adapter"),
                records=records,
                predictions_path=Path(directory) / "predictions.jsonl",
                prefix_rows=[],
                budget=KernelTimeBudget(0, now=lambda: 1),
                progress_callback=lambda count, _runtime: progress.append(count),
                batch_size=REPAIR_BATCH_SIZE,
                generator_factory=FakeGenerator,
            )
            self.assertEqual(len(rows), 511)
            self.assertEqual(progress, list(range(1, 512)))

    def test_supervisor_stops_at_memory_guard_without_retry(self):
        class FakeProcess:
            def __init__(self, _command):
                self.terminated = False

            def poll(self):
                return None if not self.terminated else -15

            def terminate(self):
                self.terminated = True

            def wait(self, timeout=None):
                return -15

            def kill(self):
                self.terminated = True

        activation = {
            "approved_commit": COMMIT,
            "attempt_id": "123456",
            "source_attempt_id": SOURCE_ATTEMPT_ID,
        }
        with tempfile.TemporaryDirectory() as directory:
            result = supervise(
                command=["worker"],
                attempt_root=Path(directory) / "attempt",
                seed=3407,
                activation=activation,
                now=lambda: 1,
                sleep=lambda _seconds: None,
                memory_reader=lambda: (90, 100),
                popen=FakeProcess,
            )
            self.assertEqual(result["guard_reason"], "memory_high_water")
            self.assertFalse(result["metrics_printed"])
            summary = json.loads(
                (Path(directory) / "attempt" / "public_summary.json").read_text()
            )
            self.assertFalse(summary["automatic_retry"])

    def test_canary_contract_and_mocked_soak(self):
        class FakeGenerator:
            def __call__(self, prompt):
                return "TOKEN"

            def generate_batch(self, prompts):
                return ["TOKEN"] * len(prompts)

        def fake_sampler(stop, samples):
            samples["gpu"].extend([80] * 12)
            samples["memory"].extend([(30, 100)] * 12)

        with patch(
            "scripts.run_f2_f3_nautilus_eval_repair_canary._sample_resources",
            side_effect=fake_sampler,
        ):
            result = run_canary(FakeGenerator())
        self.assertTrue(result["single_batch_equivalent"])
        self.assertGreater(result["mean_gpu_utilization_percent"], 40)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(
                root / "public_summary.json",
                {
                    "status": "complete",
                    "approved_commit": COMMIT,
                    "single_batch_equivalent": True,
                    "batch_size": REPAIR_BATCH_SIZE,
                    "mean_gpu_utilization_percent": 80,
                    "peak_memory_fraction": 0.3,
                    "nahw_passage_used": False,
                    "metric_computed": False,
                    "contains_corpus_text": False,
                },
            )
            self.assertEqual(validate_canary_summary(root, COMMIT)["status"], "complete")

    def test_manifests_limit_gpu_concurrency_and_right_size_resources(self):
        canary = build_manifest(
            stage="utilization-canary",
            commit=COMMIT,
            approval_reference=APPROVAL,
            confirmation=CANARY_CONFIRMATION,
        )
        self.assertEqual(len(canary["items"]), 1)
        self.assertNotIn("/private/inputs", str(canary))
        self.assertNotIn("nahw_gec_test", str(canary))
        continuation = build_manifest(
            stage="continuation",
            commit=COMMIT,
            approval_reference=APPROVAL,
            confirmation=CONTINUATION_CONFIRMATION,
            canary_attempt_id="123455",
        )
        self.assertEqual(len(continuation["items"]), 2)
        covered = set()
        for job in continuation["items"]:
            self.assertEqual(job["spec"]["backoffLimit"], 0)
            container = job["spec"]["template"]["spec"]["containers"][0]
            resources = container["resources"]["limits"]
            self.assertEqual(resources["cpu"], "2")
            self.assertEqual(resources["memory"], "64Gi")
            self.assertEqual(resources["nvidia.com/a100"], "1")
            covered.update(
                int(seed)
                for seed in job["metadata"]["annotations"][
                    "musahhih.openai/seeds"
                ].split(",")
            )
        self.assertEqual(covered, {3407, 3408, 3409, 3410, 3411})


if __name__ == "__main__":
    unittest.main()
