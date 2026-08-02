import inspect
from pathlib import Path
import tempfile
import unittest

from scripts.f2_f3_eval_rtx3090_utils import (
    CONFIRMATION,
    GPU_NAME,
    GPU_PRODUCT,
    JOB_DEADLINE_SECONDS,
    rtx3090_preflight,
    validate_activation,
)
from scripts.f2_f3_nautilus_utils import SEEDS
from scripts.prepare_f2_f3_nautilus_rtx3090_eval import build_manifest
from scripts.run_f2_f3_nautilus_multiseed_eval import (
    main as evaluation_main,
    synthetic_equivalence_gate,
)
from scripts.supervise_f2_f3_rtx3090_eval import supervise


COMMIT = "a" * 40
APPROVAL = (
    "https://github.com/ALBA7OOTH-Research-Lab/"
    "Musahhih/issues/183#issuecomment-123456"
)


class _Value:
    def sum(self):
        return self

    def item(self):
        return 1


class _Properties:
    name = GPU_NAME
    major = 8
    minor = 6
    total_memory = 24 * 1024**3


class _Cuda:
    @staticmethod
    def is_available():
        return True

    @staticmethod
    def device_count():
        return 1

    @staticmethod
    def get_device_properties(_index):
        return _Properties()

    @staticmethod
    def synchronize():
        return None


class _Torch:
    cuda = _Cuda()

    @staticmethod
    def ones(_count, *, device):
        if device != "cuda":
            raise AssertionError("CUDA operation required")
        return _Value()


class _StableGenerator:
    def __init__(self, _adapter, *, required_gpu):
        self.required_gpu = required_gpu
        self.model = None
        self.processor = None

    def load(self):
        return None

    def __call__(self, prompt):
        return f"stable:{prompt}"

    def generate_batch(self, prompts):
        return [self(prompt) for prompt in prompts]


class _UnstableGenerator(_StableGenerator):
    def generate_batch(self, prompts):
        return [f"changed:{prompt}" for prompt in prompts]


class _Process:
    def __init__(self):
        self.code = None

    def poll(self):
        return self.code

    def terminate(self):
        self.code = -15

    def wait(self, timeout=None):
        return self.code

    def kill(self):
        self.code = -9


class Rtx3090EvaluationTests(unittest.TestCase):
    def test_activation_and_executable_gpu_gate(self):
        activation = validate_activation(
            seed=3407,
            approved_commit=COMMIT,
            actual_commit=COMMIT,
            approval_reference=APPROVAL,
            confirmation=CONFIRMATION,
        )
        self.assertTrue(activation["fresh_from_record_zero"])
        self.assertFalse(activation["source_prefixes_reused"])
        report = rtx3090_preflight(_Torch())
        self.assertEqual(report["gpu"], GPU_NAME)
        self.assertTrue(report["cuda_operation_passed"])

    def test_synthetic_gate_requires_single_batch_and_repeat_equivalence(self):
        result = synthetic_equivalence_gate(
            Path("adapter"),
            required_gpu=GPU_NAME,
            generator_factory=_StableGenerator,
        )
        self.assertTrue(result["single_equals_batch16"])
        self.assertTrue(result["repeated_batch16_equal"])
        with self.assertRaisesRegex(Exception, "equivalence failed"):
            synthetic_equivalence_gate(
                Path("adapter"),
                required_gpu=GPU_NAME,
                generator_factory=_UnstableGenerator,
            )

    def test_test_input_is_validated_only_after_synthetic_gate(self):
        source = inspect.getsource(evaluation_main)
        self.assertLess(
            source.index("synthetic_equivalence_gate("),
            source.index("validate_test_staging(test_root)"),
        )

    def test_manifest_is_five_fresh_identical_3090_jobs(self):
        manifest = build_manifest(
            commit=COMMIT,
            approval_reference=APPROVAL,
            confirmation=CONFIRMATION,
        )
        self.assertEqual(len(manifest["items"]), len(SEEDS))
        self.assertEqual(
            {int(job["metadata"]["labels"]["musahhih.openai/seed"])
             for job in manifest["items"]},
            set(SEEDS),
        )
        for job in manifest["items"]:
            self.assertEqual(job["spec"]["backoffLimit"], 0)
            self.assertEqual(
                job["spec"]["activeDeadlineSeconds"], JOB_DEADLINE_SECONDS
            )
            self.assertEqual(
                job["metadata"]["annotations"][
                    "musahhih.openai/source-prefixes-reused"
                ],
                "false",
            )
            pod = job["spec"]["template"]["spec"]
            products = pod["affinity"]["nodeAffinity"][
                "requiredDuringSchedulingIgnoredDuringExecution"
            ]["nodeSelectorTerms"][0]["matchExpressions"][0]["values"]
            self.assertEqual(products, [GPU_PRODUCT])
            container = pod["containers"][0]
            self.assertEqual(
                container["resources"]["requests"],
                container["resources"]["limits"],
            )
            self.assertEqual(
                container["resources"]["limits"]["nvidia.com/gpu"], "1"
            )
            self.assertNotIn("nvidia.com/a100", container["resources"]["limits"])
            command = container["command"][-1]
            self.assertIn("supervise_f2_f3_rtx3090_eval", command)
            self.assertIn("/private/evaluations/issue-183", command)
            self.assertNotIn("resume", command.lower())

    def test_supervisor_persists_no_progress_guard(self):
        process = _Process()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ticks = iter((0.0, 1201.0, 1201.0))
            code = supervise(
                command=["worker"],
                progress_path=root / "progress.json",
                summary_path=root / "public_summary.json",
                activation={
                    "seed": 3407,
                    "approved_commit": COMMIT,
                    "attempt_id": "123456",
                },
                popen_factory=lambda _command: process,
                now=lambda: next(ticks),
                sleep=lambda _seconds: None,
            )
            self.assertEqual(code, 91)
            self.assertTrue((root / "public_summary.json").is_file())


if __name__ == "__main__":
    unittest.main()
