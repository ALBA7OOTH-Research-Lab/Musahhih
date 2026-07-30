import tempfile
import unittest
from os import environ
from pathlib import Path
from unittest.mock import patch

from scripts.f2_f3_nautilus_utils import (
    NautilusReplicationError,
    PAIR_CONFIRMATION,
    PREFLIGHT_CONFIRMATION,
    SEEDS,
    STAGING_CONFIRMATION,
    a100_preflight,
    arm_order,
    atomic_write_json,
    validate_activation,
)
from scripts.prepare_f2_f3_nautilus_jobs import (
    GIT_IMAGE,
    PYTORCH_IMAGE,
    build_manifest,
    validate_pinned_image,
)
from scripts.run_f2_f3_nautilus_pair import (
    REQUIRED_IMPORTS,
    actual_commit,
    compiler_path,
    validate_staging_manifest,
)


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
    def test_commit_attestation_needs_no_git_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".git").mkdir()
            (root / ".git" / "HEAD").write_text(COMMIT + "\n", encoding="ascii")
            with patch.dict(environ, {"PATH": ""}):
                self.assertEqual(actual_commit(root), COMMIT)

    def test_commit_attestation_rejects_non_detached_or_missing_head(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".git").mkdir()
            head = root / ".git" / "HEAD"
            for value in ("ref: refs/heads/main\n", "a" * 39, "A" * 40):
                head.write_text(value, encoding="ascii")
                with self.subTest(value=value):
                    with self.assertRaisesRegex(RuntimeError, "detached lowercase"):
                        actual_commit(root)
            head.unlink()
            with self.assertRaisesRegex(RuntimeError, "cannot read"):
                actual_commit(root)

    def test_container_images_use_complete_sha256_pins(self):
        self.assertEqual(validate_pinned_image(GIT_IMAGE), GIT_IMAGE)
        self.assertEqual(validate_pinned_image(PYTORCH_IMAGE), PYTORCH_IMAGE)
        self.assertEqual(len(GIT_IMAGE.rsplit(":", 1)[1]), 64)
        self.assertIn("2.6.0-cuda12.4-cudnn9-devel@", PYTORCH_IMAGE)
        for malformed in (
            "alpine/git:2.47.2",
            "alpine/git:2.47.2@sha256:" + "a" * 62,
            "alpine/git:2.47.2@sha256:" + "A" * 64,
        ):
            with self.subTest(image=malformed):
                with self.assertRaisesRegex(ValueError, "full lowercase sha256"):
                    validate_pinned_image(malformed)

    def test_compiler_gate_accepts_devel_toolchain_and_fails_without_it(self):
        with patch(
            "scripts.run_f2_f3_nautilus_pair.shutil.which",
            side_effect=lambda name: "/usr/bin/gcc" if name == "gcc" else None,
        ):
            self.assertEqual(compiler_path(), "/usr/bin/gcc")
        with patch(
            "scripts.run_f2_f3_nautilus_pair.shutil.which",
            return_value=None,
        ):
            with self.assertRaisesRegex(RuntimeError, "requires a C compiler"):
                compiler_path()

    def test_unsloth_is_imported_before_training_frameworks(self):
        self.assertEqual(REQUIRED_IMPORTS[0], "unsloth")
        self.assertLess(
            REQUIRED_IMPORTS.index("unsloth"), REQUIRED_IMPORTS.index("trl")
        )

    def test_training_requires_exact_private_staging_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "staging_manifest.json"
            manifest.write_text(
                '{"status":"complete","records":{"f2":2000,"f3":2000,'
                '"development":975},"contains_corpus_text":false}\n',
                encoding="utf-8",
            )
            self.assertEqual(validate_staging_manifest(root)["status"], "complete")
            manifest.write_text('{"status":"complete"}\n', encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "contract mismatch"):
                validate_staging_manifest(root)

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

    def test_training_manifest_has_only_five_a100_jobs_for_prestaged_pvc(self):
        manifest = build_manifest(
            stage="paired-training",
            commit=COMMIT,
            approval_reference=APPROVAL,
            confirmation=PAIR_CONFIRMATION,
        )
        self.assertEqual(len(manifest["items"]), 5)
        jobs = manifest["items"]
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

    def test_private_staging_manifest_has_one_rwx_pvc_and_no_gpu(self):
        manifest = build_manifest(
            stage="private-staging",
            commit=COMMIT,
            approval_reference=APPROVAL,
            confirmation=STAGING_CONFIRMATION,
        )
        self.assertEqual(len(manifest["items"]), 2)
        pvc, pod = manifest["items"]
        self.assertEqual(pvc["kind"], "PersistentVolumeClaim")
        self.assertEqual(pvc["spec"]["accessModes"], ["ReadWriteMany"])
        self.assertEqual(pvc["spec"]["storageClassName"], "cephfs")
        self.assertEqual(pod["kind"], "Pod")
        self.assertEqual(pod["spec"]["restartPolicy"], "Never")
        serialized = str(pod).lower()
        self.assertNotIn("nvidia.com", serialized)
        self.assertIn("staging_manifest.json", serialized)
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
