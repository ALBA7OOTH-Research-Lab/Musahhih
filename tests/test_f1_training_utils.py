import json
from pathlib import Path
import tempfile
import unittest

from scripts.f1_training_utils import (
    FULL_TRAINING_CONFIRMATION,
    MIN_HEADROOM_BYTES,
    TRAIN_RECORDS,
    TrainingGateError,
    memory_gate,
    require_full_training_confirmation,
    validate_private_jsonl,
)


def record(index, split="train"):
    return {
        "record_id": f"synthetic-{index}",
        "prompt": [{"role": "user", "content": "PLACEHOLDER INPUT"}],
        "completion": [{"role": "assistant", "content": "PLACEHOLDER OUTPUT"}],
        "source": "QALB-2014-L1",
        "split": split,
    }


class F1TrainingUtilsTests(unittest.TestCase):
    def write_rows(self, rows):
        directory = tempfile.TemporaryDirectory()
        path = Path(directory.name) / "private.jsonl"
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        self.addCleanup(directory.cleanup)
        return path

    def test_private_validation_returns_text_free_metadata(self):
        path = self.write_rows([record(1), record(2)])
        summary = validate_private_jsonl(path, "train", 2)
        self.assertEqual(summary["records"], 2)
        self.assertFalse(summary["contains_corpus_text"])
        self.assertNotIn("PLACEHOLDER", json.dumps(summary))

    def test_private_validation_rejects_count_and_role(self):
        path = self.write_rows([record(1, split="development")])
        with self.assertRaisesRegex(TrainingGateError, "role mismatch"):
            validate_private_jsonl(path, "train", TRAIN_RECORDS)

    def test_memory_gate_requires_one_gibibyte_headroom(self):
        passed = memory_gate(10 * 1024**3, 9 * 1024**3)
        failed = memory_gate(10 * 1024**3, 10 * 1024**3 - MIN_HEADROOM_BYTES + 1)
        self.assertTrue(passed["passed"])
        self.assertFalse(failed["passed"])

    def test_full_training_requires_exact_confirmation_and_smoke(self):
        with self.assertRaisesRegex(TrainingGateError, "confirmation"):
            require_full_training_confirmation("yes", {"passed": True})
        with self.assertRaisesRegex(TrainingGateError, "smoke"):
            require_full_training_confirmation(FULL_TRAINING_CONFIRMATION, {"passed": False})
        require_full_training_confirmation(FULL_TRAINING_CONFIRMATION, {"passed": True})
