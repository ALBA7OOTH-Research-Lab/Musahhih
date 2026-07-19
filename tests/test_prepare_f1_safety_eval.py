import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.prepare_f1_safety_eval import (
    ARABICMMLU_REVISION,
    SafetyPreparationError,
    WRITE_CONFIRMATION,
    _apply_m2_edits,
    _canonical_sha256,
    _records_sha256,
    build_overcorrection_records,
    build_capability_records,
    prepare,
    render_arabicmmlu_prompt,
)


class F1SafetyPreparationTests(unittest.TestCase):
    def test_applies_nonoverlapping_m2_edits_in_reverse_order(self):
        source = "one two three four"
        actions = [
            "A 1 2|||Edit|||TWO|||REQUIRED|||-NONE-|||0",
            "A 3 4|||Edit|||-NONE-|||REQUIRED|||-NONE-|||0",
        ]
        self.assertEqual(_apply_m2_edits(source, actions), "one TWO three")

    def test_rejects_overlapping_or_wrong_annotator_edits(self):
        with self.assertRaisesRegex(SafetyPreparationError, "overlapping"):
            _apply_m2_edits(
                "a b c",
                [
                    "A 0 2|||Edit|||x|||REQUIRED|||-NONE-|||0",
                    "A 1 3|||Edit|||y|||REQUIRED|||-NONE-|||0",
                ],
            )
        with self.assertRaisesRegex(SafetyPreparationError, "annotator 0"):
            _apply_m2_edits(
                "a b", ["A 0 1|||Edit|||x|||REQUIRED|||-NONE-|||1"]
            )

    def test_reconstructed_m2_target_must_match_official_cor(self):
        with tempfile.TemporaryDirectory() as tmp:
            m2_path = Path(tmp) / "sample.m2"
            cor_path = m2_path.with_suffix(".cor")
            m2_path.write_text(
                "S نص خطا\nA 1 2|||Edit|||صحيح|||REQUIRED|||-NONE-|||0\n",
                encoding="utf-8",
            )
            cor_path.write_text("S نص صحيح\n", encoding="utf-8-sig")
            with (
                patch("scripts.prepare_f1_safety_eval.QALB_SHA256", hashlib.sha256(m2_path.read_bytes()).hexdigest()),
                patch("scripts.prepare_f1_safety_eval.QALB_COR_SHA256", hashlib.sha256(cor_path.read_bytes()).hexdigest()),
                patch("scripts.prepare_f1_safety_eval.EXPECTED_QALB_RECORDS", 1),
            ):
                self.assertEqual(len(build_overcorrection_records(m2_path)), 1)
            cor_path.write_text("S نص مختلف\n", encoding="utf-8-sig")
            with (
                patch("scripts.prepare_f1_safety_eval.QALB_SHA256", hashlib.sha256(m2_path.read_bytes()).hexdigest()),
                patch("scripts.prepare_f1_safety_eval.QALB_COR_SHA256", hashlib.sha256(cor_path.read_bytes()).hexdigest()),
                patch("scripts.prepare_f1_safety_eval.EXPECTED_QALB_RECORDS", 1),
                self.assertRaisesRegex(SafetyPreparationError, "differs"),
            ):
                build_overcorrection_records(m2_path)
    def test_official_prompt_shape_and_choices_are_stable(self):
        row = {
            "Subject": "Science", "Level": "High", "Country": "KSA",
            "Question": "Question text", "Context": "Context text",
            "Option 1": "first", "Option 2": "second", "Option 3": "",
            "Option 4": "", "Option 5": "",
        }
        prompt, choices = render_arabicmmlu_prompt(row)
        self.assertEqual(choices, ["A", "B"])
        self.assertEqual(
            prompt,
            "This is a Science question for high school in KSA. Select the correct answer!\n\n"
            "Question: Context text\n\nQuestion text\nA. first\nB. second\n\nAnswer:",
        )

    def test_capability_selection_is_25_per_task_and_label_independent(self):
        schema = [
            "ID", "Source", "Country", "Group", "Subject", "Level", "Question",
            "Context", "Answer Key", "Option 1", "Option 2", "Option 3", "Option 4",
            "Option 5", "is_few_shot",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for task_index in range(40):
                folder = root / f"Task {task_index:02d}"
                folder.mkdir()
                with (folder / "test.csv").open("w", encoding="utf-8", newline="") as stream:
                    writer = csv.DictWriter(stream, fieldnames=schema)
                    writer.writeheader()
                    for index in range(30):
                        writer.writerow({
                            "ID": str(index), "Source": "source", "Country": "",
                            "Group": "group", "Subject": "Subject", "Level": "",
                            "Question": f"q-{index}", "Context": "", "Answer Key": "A",
                            "Option 1": "one", "Option 2": "two", "Option 3": "",
                            "Option 4": "", "Option 5": "", "is_few_shot": "False",
                        })
            with patch("scripts.prepare_f1_safety_eval._git_revision", return_value=ARABICMMLU_REVISION):
                first, manifest = build_capability_records(root)
            for path in root.glob("*/test.csv"):
                with path.open(encoding="utf-8", newline="") as stream:
                    rows = list(csv.DictReader(stream))
                for row in rows:
                    row["Answer Key"] = "B"
                with path.open("w", encoding="utf-8", newline="") as stream:
                    writer = csv.DictWriter(stream, fieldnames=schema)
                    writer.writeheader(); writer.writerows(rows)
            with patch("scripts.prepare_f1_safety_eval._git_revision", return_value=ARABICMMLU_REVISION):
                second, _ = build_capability_records(root)
            self.assertEqual(len(first), 1000)
            self.assertEqual(len(manifest), 40)
            self.assertEqual(
                [(row["task"], row["source_id"]) for row in first],
                [(row["task"], row["source_id"]) for row in second],
            )
            self.assertTrue(all(row["gold_choice"] == "A" for row in first))
            self.assertTrue(all(row["gold_choice"] == "B" for row in second))

    def test_private_write_is_confirmed_nonoverwriting_and_hash_exact(self):
        over = [{"record_id": "over"}]
        capability = [{"record_id": "cap", "choices": ["A", "B"]}]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "data" / "processed" / "safety"
            patches = (
                patch("scripts.prepare_f1_safety_eval.ROOT", root),
                patch("scripts.prepare_f1_safety_eval.build_overcorrection_records", return_value=over),
                patch("scripts.prepare_f1_safety_eval.build_capability_records", return_value=(capability, [])),
                patch(
                    "scripts.prepare_f1_safety_eval.EXPECTED_OVERCORRECTION_PREPARED_SHA256",
                    _records_sha256(over),
                ),
                patch(
                    "scripts.prepare_f1_safety_eval.EXPECTED_CAPABILITY_PREPARED_SHA256",
                    _records_sha256(capability),
                ),
                patch(
                    "scripts.prepare_f1_safety_eval.EXPECTED_SOURCE_MANIFEST_SHA256",
                    _canonical_sha256([]),
                ),
            )
            with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
                with self.assertRaisesRegex(SafetyPreparationError, "confirmation"):
                    prepare(Path("q"), Path("a"), output,
                            write_private_records=True, confirmation="wrong")
                summary = prepare(
                    Path("q"), Path("a"), output,
                    write_private_records=True, confirmation=WRITE_CONFIRMATION,
                )
                self.assertEqual(
                    hashlib.sha256((output / "overcorrection.jsonl").read_bytes()).hexdigest(),
                    summary["overcorrection"]["prepared_records_sha256"],
                )
                self.assertEqual(
                    hashlib.sha256((output / "arabicmmlu.jsonl").read_bytes()).hexdigest(),
                    summary["capability"]["prepared_records_sha256"],
                )
                with self.assertRaisesRegex(SafetyPreparationError, "already exists"):
                    prepare(
                        Path("q"), Path("a"), output,
                        write_private_records=True, confirmation=WRITE_CONFIRMATION,
                    )


if __name__ == "__main__":
    unittest.main()
