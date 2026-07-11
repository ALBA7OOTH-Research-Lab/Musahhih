import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts.prepare_qalb_dev_prompt_records import (
    DevInputError,
    build_prompt_records,
    write_private_records,
)
from scripts.prepare_qalb_manifests import ROOT_NAME, SplitSpec


class PrepareQalbDevPromptRecordsTests(unittest.TestCase):
    def make_fixture(self, root: Path):
        spec = SplitSpec(2014, "L1", "dev")
        sent_member = f"{spec.stem}.sent"
        m2_member = f"{spec.stem}.m2"
        archive_path = root / "qalb.zip"
        source = "alpha beta gamma delta epsilon"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr(sent_member, f"doc1 {source}\n")
            archive.writestr(
                m2_member,
                "S alpha beta gamma delta epsilon\n"
                "A 1 2|||Edit|||better|||REQUIRED|||-NONE-|||0\n",
            )
        manifest_path = root / "dev.jsonl"
        manifest_path.write_text(
            json.dumps(
                {
                    "record_key": "qalb-0.9.1:2014:L1:dev:000001:doc1",
                    "release": "0.9.1",
                    "year": 2014,
                    "track": "L1",
                    "split": "dev",
                    "document_id": "doc1",
                    "line_number": 1,
                    "sent_member": sent_member,
                    "m2_member": m2_member,
                    "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                    "eligible_for_development": True,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return archive_path, manifest_path

    def test_builds_deterministic_private_runner_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive, manifest = self.make_fixture(Path(tmp))
            first, first_summary = build_prompt_records(archive, manifest)
            second, second_summary = build_prompt_records(archive, manifest)

            self.assertEqual(first, second)
            self.assertEqual(first_summary, second_summary)
            self.assertEqual(first[0]["error"], "beta")
            self.assertEqual(first[0]["gold_correction"], "better")
            self.assertEqual(first[0]["passage"], "alpha beta gamma delta epsilon")
            self.assertEqual(first_summary["number_of_records"], 1)

    def test_rejects_manifest_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive, manifest = self.make_fixture(Path(tmp))
            row = json.loads(manifest.read_text(encoding="utf-8"))
            row["source_sha256"] = "0" * 64
            manifest.write_text(json.dumps(row) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(DevInputError, "source hash mismatch"):
                build_prompt_records(archive, manifest)

    def test_private_writer_refuses_public_path_and_overwrite(self):
        records = [{"record_id": "r1", "passage": "private", "error": "private"}]
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "records.jsonl"
            with self.assertRaisesRegex(DevInputError, "must stay under"):
                write_private_records(output, records)
            write_private_records(output, records, allow_outside_private_root=True)
            with self.assertRaisesRegex(DevInputError, "already exists"):
                write_private_records(output, records, allow_outside_private_root=True)


if __name__ == "__main__":
    unittest.main()
