import tempfile
import unittest
from pathlib import Path

from scripts.f2_f3_nautilus_utils import (
    NautilusReplicationError,
    PAIR_CONFIRMATION,
    PREFLIGHT_CONFIRMATION,
    SEEDS,
    a100_preflight,
    arm_order,
    atomic_write_json,
    validate_activation,
)
from scripts.prepare_f2_f3_nautilus_jobs import build_manifest


APPROVAL = (
    "https://github.com/ALBA7OOTH-Research-Lab/Musahhih/" "issues/155#issuecomment-1"
)
COMMIT = "a" * 40


class FakeProperties:
    name = "NVIDIA A100-SXM4-80GB"
    major = 8
    minor = 0
    total_memory = 80 * 1024**3


class FakeScalar:
    def item(self):
        return 1


class FakeTensor:
    def sum(self):
        return FakeScalar()


class FakeCuda:
    def __init__(self, *, available=True, count=1, properties=None):
        self._available = available
        self._count = count
        self._properties = properties or FakeProperties()
        self.synchronized = False

    def is_available(self):
        return self._available

    def device_count(self):
        return self._count

    def get_device_properties(self, index):
        self.index = index
        return self._properties

    def synchronize(self):
        self.synchronized = True


class FakeTorch:
    def __init__(self, **cuda_kwargs):
        self.cuda = FakeCuda(**cuda_kwargs)

    def ones(self, count, device):
        self.request = (count, device)
        return FakeTensor()


class NautilusReplicationTests(unittest.TestCase):
    def test_five_seeds_have_balanced_deterministic_orders(self):
        self.assertEqual(SEEDS, (3407, 3408, 3409, 3410, 3411))
        self.assertEqual(arm_order(3407), ("F2-P1", "F3-P1"))
        self.assertEqual(arm_order(3408), ("F3-P1", "F2-P1"))
        self.assertEqual(sum(order[0] == "F2-P1" for order in map(arm_order, SEEDS)), 3)

    def test_activation_requires_exact_commit_comment_and_confirmation(self):
        result = validate_activation(
            stage="paired-training",
            seed=3409,
            approved_commit=COMMIT,
            actual_commit=COMMIT,
            approval_reference=APPROVAL,
            confirmation=PAIR_CONFIRMATION,
        )
        self.assertEqual(result["arm_order"], ["F2-P1", "F3-P1"])
        for change in (
            {"actual_commit": "b" * 40},
            {"approval_reference": APPROVAL.split("#")[0]},
            {"confirmation": "yes"},
            {"seed": 99},
        ):
            arguments = {
                "stage": "paired-training",
                "seed": 3409,
                "approved_commit": COMMIT,
                "actual_commit": COMMIT,
                "approval_reference": APPROVAL,
                "confirmation": PAIR_CONFIRMATION,
            }
            arguments.update(change)
            with self.subTest(change=change):
                with self.assertRaises(NautilusReplicationError):
                    validate_activation(**arguments)

    def test_preflight_refuses_seed_and_training_requires_seed(self):
        validate_activation(
            stage="a100-preflight",
            seed=None,
            approved_commit=COMMIT,
            actual_commit=COMMIT,
            approval_reference=APPROVAL,
            confirmation=PREFLIGHT_CONFIRMATION,
        )
        with self.assertRaises(NautilusReplicationError):
            validate_activation(
                stage="a100-preflight",
                seed=3407,
                approved_commit=COMMIT,
                actual_commit=COMMIT,
                approval_reference=APPROVAL,
                confirmation=PREFLIGHT_CONFIRMATION,
            )

    def test_a100_preflight_executes_cuda_and_rejects_wrong_gpu(self):
        torch = FakeTorch()
        summary = a100_preflight(torch)
        self.assertTrue(summary["cuda_operation_passed"])
        self.assertEqual(torch.request, (1, "cuda"))
        self.assertTrue(torch.cuda.synchronized)

        wrong = FakeProperties()
        wrong.name = "NVIDIA Tesla P100-PCIE-16GB"
        wrong.major = 6
        wrong.minor = 0
        with self.assertRaisesRegex(NautilusReplicationError, "A100"):
            a100_preflight(FakeTorch(properties=wrong))

    def test_atomic_json_is_write_once(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            atomic_write_json(path, {"contains_corpus_text": False})
            self.assertIn('"contains_corpus_text": false', path.read_text())
            with self.assertRaisesRegex(NautilusReplicationError, "overwrite"):
                atomic_write_json(path, {"contains_corpus_text": False})

    def test_training_manifest_has_five_a100_jobs_and_one_rwx_pvc(self):
        manifest = build_manifest(
            stage="paired-training",
            commit=COMMIT,
            approval_reference=APPROVAL,
            confirmation=PAIR_CONFIRMATION,
        )
        self.assertEqual(len(manifest["items"]), 6)
        pvc, *jobs = manifest["items"]
        self.assertEqual(pvc["kind"], "PersistentVolumeClaim")
        self.assertEqual(pvc["spec"]["accessModes"], ["ReadWriteMany"])
        self.assertEqual(pvc["spec"]["storageClassName"], "cephfs")
        self.assertEqual(len({job["metadata"]["name"] for job in jobs}), 5)
        for job in jobs:
            self.assertEqual(job["spec"]["backoffLimit"], 0)
            container = job["spec"]["template"]["spec"]["containers"][0]
            self.assertEqual(
                container["resources"]["requests"],
                container["resources"]["limits"],
            )
            self.assertEqual(container["resources"]["limits"]["nvidia.com/a100"], "1")
            serialized = str(job).lower()
            self.assertNotIn("nahw", serialized)
            self.assertNotIn("qalb_test", serialized)

    def test_preflight_manifest_has_no_private_volume(self):
        manifest = build_manifest(
            stage="a100-preflight",
            commit=COMMIT,
            approval_reference=APPROVAL,
            confirmation=PREFLIGHT_CONFIRMATION,
        )
        self.assertEqual(len(manifest["items"]), 1)
        job = manifest["items"][0]
        volumes = job["spec"]["template"]["spec"]["volumes"]
        self.assertEqual(volumes, [{"name": "repository", "emptyDir": {}}])


if __name__ == "__main__":
    unittest.main()
