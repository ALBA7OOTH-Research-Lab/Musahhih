import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.prepare_f2_f3_training_records import (
    F2F3AdapterError,
    build_records,
    safe_private_output,
    write_idempotent,
)


def tibyan(index):
    return {
        "record_id": f"tibyan-{index}",
        "source_dataset": "Tibyan-corpus",
        "source_release": "Zenodo-14623621",
        "source_line_number": index + 1,
        "passage": f"PRIVATE PASSAGE {index}",
        "erroneous_word": "WRONG",
        "gold_correction": "RIGHT",
        "project_split": "train",
        "is_group_representative": True,
        "selection_rank": index + 1,
        "exact_overlap_qalb_test": False,
        "exact_overlap_qalb_train_development": False,
        "exact_overlap_nahw": False,
    }


def natural(index, split="train"):
    return {
        "record_id": f"natural-{index}",
        "prompt": [{"role": "user", "content": f"PRIVATE INPUT {index}"}],
        "completion": [{"role": "assistant", "content": "PRIVATE OUTPUT"}],
        "source": "QALB-2014-L1",
        "split": split,
    }


class F2F3TrainingRecordTests(unittest.TestCase):
    def fixture(self):
        tibyan_rows = [tibyan(index) for index in range(4)]
        natural_train = [natural(index) for index in range(4)]
        natural_dev = [natural(10, "development")]
        return tibyan_rows, natural_train, natural_dev

    def build_fixture(self):
        tibyan_rows, natural_train, natural_dev = self.fixture()
        with (
            patch(
                "scripts.prepare_f2_f3_training_records.F2_RECORDS", 4
            ),
            patch(
                "scripts.prepare_f2_f3_training_records.F3_HALF_RECORDS", 2
            ),
            patch(
                "scripts.prepare_f2_f3_training_records."
                "EXPECTED_TIBYAN_RECORD_IDS_SHA256",
                self.digest(tibyan_rows),
            ),
            patch(
                "scripts.prepare_f2_f3_training_records."
                "EXPECTED_TIBYAN_PREFIX_IDS_SHA256",
                self.digest(tibyan_rows[:2]),
            ),
            patch(
                "scripts.prepare_f2_f3_training_records."
                "EXPECTED_F1_PREFIX_IDS_SHA256",
                self.digest(natural_train[:2]),
            ),
        ):
            return build_records(tibyan_rows, natural_train, natural_dev)

    @staticmethod
    def digest(rows):
        import hashlib

        return hashlib.sha256(
            ("\n".join(row["record_id"] for row in rows) + "\n").encode()
        ).hexdigest()

    def test_builds_frozen_counts_and_provenance(self):
        payloads, summary = self.build_fixture()
        self.assertEqual(summary["f2"]["records"], 4)
        self.assertEqual(summary["f3"]["records"], 4)
        self.assertEqual(summary["f3"]["natural_records"], 2)
        self.assertEqual(summary["f3"]["synthetic_records"], 2)
        self.assertEqual(summary["common_development"]["records"], 1)
        self.assertFalse(summary["training_executed"])
        self.assertFalse(summary["inference_executed"])
        self.assertNotIn("PRIVATE", json.dumps(summary))
        self.assertEqual(set(payloads), {
            "f2_train_records.jsonl",
            "f3_train_records.jsonl",
            "common_dev_records.jsonl",
            "f2_f3_training_records_summary.json",
        })

    def test_f3_order_is_deterministic_and_composition_is_nested(self):
        first_payloads, first_summary = self.build_fixture()
        second_payloads, second_summary = self.build_fixture()
        self.assertEqual(first_payloads, second_payloads)
        self.assertEqual(first_summary, second_summary)
        rows = [
            json.loads(line)
            for line in first_payloads["f3_train_records.jsonl"]
            .decode()
            .splitlines()
        ]
        self.assertEqual(
            {row["record_id"] for row in rows},
            {"natural-0", "natural-1", "tibyan-0", "tibyan-1"},
        )

    def test_test_overlap_flag_is_rejected(self):
        tibyan_rows, natural_train, natural_dev = self.fixture()
        tibyan_rows[0]["exact_overlap_qalb_test"] = True
        with (
            patch("scripts.prepare_f2_f3_training_records.F2_RECORDS", 4),
            patch("scripts.prepare_f2_f3_training_records.F3_HALF_RECORDS", 2),
            self.assertRaisesRegex(F2F3AdapterError, "role or privacy"),
        ):
            build_records(tibyan_rows, natural_train, natural_dev)

    def test_private_output_is_idempotent_and_refuses_difference(self):
        payloads, _ = self.build_fixture()
        with tempfile.TemporaryDirectory() as directory:
            with patch(
                "scripts.prepare_f2_f3_training_records.ROOT",
                Path(directory),
            ):
                target = Path(directory) / "data/processed/test-output"
                target.mkdir(parents=True)
                write_idempotent(target, payloads)
                write_idempotent(target, payloads)
                changed = dict(payloads)
                changed["f2_train_records.jsonl"] += b"changed"
                with self.assertRaisesRegex(
                    F2F3AdapterError, "differs"
                ):
                    write_idempotent(target, changed)

    def test_output_path_must_stay_private(self):
        with self.assertRaisesRegex(F2F3AdapterError, "data/processed"):
            safe_private_output(Path.cwd() / "public-output")


if __name__ == "__main__":
    unittest.main()
