import inspect
from pathlib import Path
import unittest

from scripts.f2_f3_fixed_checkpoint_repair_utils import (
    CONFIRMATION,
    FAILED_SEEDS,
    GPU_NAME,
    GPU_PRODUCT,
    FixedCheckpointRepairError,
    validate_activation,
)
from scripts.prepare_f2_f3_fixed_checkpoint_repair import build_manifest
from scripts.run_f2_f3_fixed_checkpoint_repair import (
    main as repair_main,
    synthetic_batch_stability_gate,
)


COMMIT = "a" * 40
APPROVAL = (
    "https://github.com/ALBA7OOTH-Research-Lab/"
    "Musahhih/issues/194#issuecomment-123456"
)


class _StableGenerator:
    def __init__(self, _adapter, *, required_gpu):
        self.required_gpu = required_gpu
        self.model = None
        self.processor = None

    def load(self):
        return None

    def generate_batch(self, prompts):
        return [f"stable:{prompt}" for prompt in prompts]


class _UnstableGenerator(_StableGenerator):
    calls = 0

    def generate_batch(self, prompts):
        type(self).calls += 1
        return [f"call-{self.calls}:{prompt}" for prompt in prompts]


class FixedCheckpointRepairTests(unittest.TestCase):
    def test_activation_allows_only_the_two_failed_seeds(self):
        for seed in FAILED_SEEDS:
            value = validate_activation(
                seed=seed,
                approved_commit=COMMIT,
                actual_commit=COMMIT,
                approval_reference=APPROVAL,
                confirmation=CONFIRMATION,
            )
            self.assertTrue(value["fresh_from_record_zero"])
            self.assertFalse(value["source_predictions_reused"])
        with self.assertRaisesRegex(FixedCheckpointRepairError, "only failed seeds"):
            validate_activation(
                seed=3408,
                approved_commit=COMMIT,
                actual_commit=COMMIT,
                approval_reference=APPROVAL,
                confirmation=CONFIRMATION,
            )

    def test_gate_requires_repeated_batch16_not_single_batch_identity(self):
        result = synthetic_batch_stability_gate(
            Path("adapter"),
            required_gpu=GPU_NAME,
            generator_factory=_StableGenerator,
        )
        self.assertTrue(result["repeated_batch_equal"])
        self.assertFalse(result["single_batch_equivalence_required"])
        _UnstableGenerator.calls = 0
        with self.assertRaisesRegex(FixedCheckpointRepairError, "stability failed"):
            synthetic_batch_stability_gate(
                Path("adapter"),
                required_gpu=GPU_NAME,
                generator_factory=_UnstableGenerator,
            )

    def test_test_access_stays_after_batch_stability_gate(self):
        source = inspect.getsource(repair_main)
        self.assertLess(
            source.index("synthetic_batch_stability_gate("),
            source.index("validate_test_staging(test_root)"),
        )

    def test_manifest_contains_exactly_two_write_once_replacements(self):
        manifest = build_manifest(commit=COMMIT, approval_reference=APPROVAL)
        self.assertEqual(len(manifest["items"]), 2)
        self.assertEqual(
            {int(job["metadata"]["labels"]["musahhih.openai/seed"])
             for job in manifest["items"]},
            set(FAILED_SEEDS),
        )
        for job in manifest["items"]:
            self.assertEqual(job["metadata"]["namespace"], "aiea-interns")
            self.assertEqual(job["spec"]["backoffLimit"], 0)
            pod = job["spec"]["template"]["spec"]
            products = pod["affinity"]["nodeAffinity"][
                "requiredDuringSchedulingIgnoredDuringExecution"
            ]["nodeSelectorTerms"][0]["matchExpressions"][0]["values"]
            self.assertEqual(products, [GPU_PRODUCT])
            command = pod["containers"][0]["command"][-1]
            self.assertIn("supervise_f2_f3_fixed_checkpoint_repair", command)
            self.assertNotIn("run_f2_f3_nautilus_pair", command)
            self.assertIn("PIPESTATUS", command)


if __name__ == "__main__":
    unittest.main()
