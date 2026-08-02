import json
from pathlib import Path
import tempfile
import unittest

from scripts.f2_f3_fixed_checkpoint_utils import (
    CONFIRMATION,
    GPU_PRODUCT,
    FixedCheckpointError,
    validate_activation,
    validate_unselected_training_pair,
)
from scripts.f2_f3_multiseed_eval_utils import TRAINING_COMMIT
from scripts.f2_f3_nautilus_utils import SEEDS, arm_order
from scripts.prepare_f2_f3_fixed_checkpoint_eval import build_manifest
from scripts.run_f2_f3_nautilus_pair import checkpoint_identity


COMMIT = "a" * 40
APPROVAL = (
    "https://github.com/ALBA7OOTH-Research-Lab/"
    "Musahhih/issues/192#issuecomment-123456"
)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")


def write_training_pair(root: Path, seed: int) -> Path:
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
            (checkpoint / "adapter_config.json").write_text("{}\n", encoding="utf-8")
            identities.append(checkpoint_identity(checkpoint))
        selected = "checkpoint-125" if arm == "F2-P1" else "checkpoint-250"
        write_json(arm_root / "checkpoint_selection.json", {
            "arm": arm,
            "seed": seed,
            "workflow_commit": TRAINING_COMMIT,
            "precision": "float16",
            "selected_checkpoint": selected,
            "checkpoints": identities,
            "contains_corpus_text": False,
        })
        write_json(seed_root / f"{position}0_{arm.lower()}_complete.json", {
            "arm": arm,
            "seed": seed,
            "selected_checkpoint": selected,
            "contains_corpus_text": False,
        })
    write_json(seed_root / "99_pair_complete.json", {
        "seed": seed,
        "arm_order": list(order),
        "completed_arms": list(order),
        "workflow_commit": TRAINING_COMMIT,
        "contains_corpus_text": False,
        "nahw_passage_used": False,
        "qalb_test_used": False,
    })
    return seed_root


class FixedCheckpointTests(unittest.TestCase):
    def test_activation_is_issue_and_commit_bound(self):
        result = validate_activation(
            seed=3407,
            approved_commit=COMMIT,
            actual_commit=COMMIT,
            approval_reference=APPROVAL,
            confirmation=CONFIRMATION,
        )
        self.assertEqual(result["attempt_id"], "123456")
        with self.assertRaisesRegex(FixedCheckpointError, "issue #192"):
            validate_activation(
                seed=3407,
                approved_commit=COMMIT,
                actual_commit=COMMIT,
                approval_reference=APPROVAL.replace("192", "171"),
                confirmation=CONFIRMATION,
            )

    def test_only_unselected_epoch_is_returned_after_both_hashes_validate(self):
        with tempfile.TemporaryDirectory() as directory:
            seed_root = write_training_pair(Path(directory), 3407)
            result = validate_unselected_training_pair(seed_root, 3407)
            self.assertEqual(result["F2-P1"]["checkpoint"], "checkpoint-250")
            self.assertEqual(result["F3-P1"]["checkpoint"], "checkpoint-125")
            self.assertEqual(
                result["F2-P1"]["checkpoint_policy"],
                "unselected_epoch_checkpoint",
            )
            selected = seed_root / "f2-p1" / "checkpoint-125"
            (selected / "adapter_model.safetensors").write_bytes(b"tampered")
            with self.assertRaisesRegex(FixedCheckpointError, "checkpoint validation"):
                validate_unselected_training_pair(seed_root, 3407)

    def test_manifest_has_five_write_once_jobs_and_no_training(self):
        manifest = build_manifest(commit=COMMIT, approval_reference=APPROVAL)
        self.assertEqual(len(manifest["items"]), len(SEEDS))
        for job in manifest["items"]:
            self.assertEqual(job["spec"]["backoffLimit"], 0)
            self.assertEqual(job["metadata"]["annotations"]["musahhih.openai/training"], "false")
            pod = job["spec"]["template"]["spec"]
            products = pod["affinity"]["nodeAffinity"][
                "requiredDuringSchedulingIgnoredDuringExecution"
            ]["nodeSelectorTerms"][0]["matchExpressions"][0]["values"]
            self.assertEqual(products, [GPU_PRODUCT])
            command = pod["containers"][0]["command"][-1]
            self.assertIn("supervise_f2_f3_fixed_checkpoint_eval", command)
            self.assertNotIn("run_f2_f3_nautilus_pair", command)
            self.assertNotIn("SFTTrainer", command)
            self.assertIn("PIPESTATUS", command)


if __name__ == "__main__":
    unittest.main()
