import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts.prepare_qalb_manifests import PUBLIC_RECORD_KEYS, build_manifest_data


ROOT_NAME = "QALB-0.9.1-Dec03-2021-SharedTasks"
GROUPS = {
    (2014, "L1", "train"): [
        ("t1.ar", "TRAIN_KEEP", "TRAIN_FIXED"),
        ("t2.ar", "TRAIN_DUP", "TRAIN_DUP_FIXED_1"),
        ("t3.ar", "TRAIN_DUP", "TRAIN_DUP_FIXED_2"),
        ("t4.ar", "QALB_TEST_MATCH", "TRAIN_LEAK_FIXED"),
    ],
    (2014, "L1", "dev"): [
        ("d1.ar", "DEV_KEEP", "DEV_FIXED"),
        ("d2.ar", "NAHW_MATCH", "DEV_NAHW_FIXED"),
    ],
    (2014, "L1", "test"): [("q1.ar", "QALB_TEST_MATCH", "TEST_FIXED")],
    (2015, "L1", "test"): [("q2.ar", "L1_TEST_ONLY", "L1_TEST_FIXED")],
    (2015, "L2", "train"): [("l2t.ar", "L2_TRAIN_KEEP", "L2_TRAIN_FIXED")],
    (2015, "L2", "dev"): [("l2d.ar", "L2_DEV_KEEP", "L2_DEV_FIXED")],
    (2015, "L2", "test"): [("l2q.ar", "L2_TEST_ONLY", "L2_TEST_FIXED")],
}


def member_stem(year, track, split):
    title_split = {"train": "Train", "dev": "Dev", "test": "Test"}[split]
    return f"{ROOT_NAME}/data/{year}/{split}/QALB-{year}-{track}-{title_split}"


def group_members(rows):
    sent = "".join(f"{doc_id} {source}\n" for doc_id, source, _ in rows)
    cor = "".join(f"S {correction}\n" for _, _, correction in rows)
    m2 = "".join(f"S {source}\n\n" for _, source, _ in rows)
    return sent.encode("utf-8-sig"), cor.encode("utf-8-sig"), m2.encode("utf-8-sig")


def write_fixture_archive(path, groups=GROUPS, extra_members=None):
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"{ROOT_NAME}/README.txt", "fixture readme".encode("utf-8-sig"))
        archive.writestr(f"{ROOT_NAME}/LICENSE.txt", "fixture license".encode("utf-8-sig"))
        for (year, track, split), rows in groups.items():
            sent, cor, m2 = group_members(rows)
            stem = member_stem(year, track, split)
            archive.writestr(f"{stem}.sent", sent)
            archive.writestr(f"{stem}.cor", cor)
            archive.writestr(f"{stem}.m2", m2)
        for name, payload in extra_members or []:
            archive.writestr(name, payload)


class QalbManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.archive = self.root / "qalb.zip"
        self.nahw = self.root / "Nahw-Passage.json"
        write_fixture_archive(self.archive)
        self.nahw.write_text(
            json.dumps([{"passage": "NAHW_MATCH"}], ensure_ascii=False),
            encoding="utf-8",
        )

    def test_preserves_within_train_duplicates_and_applies_leakage_policy(self):
        registry, metadata = build_manifest_data(self.archive, self.nahw)

        self.assertEqual(len(registry), 11)
        self.assertTrue(all(set(row) == PUBLIC_RECORD_KEYS for row in registry))
        duplicate_hash = hashlib.sha256("TRAIN_DUP".encode("utf-8")).hexdigest()
        duplicate_rows = [row for row in registry if row["source_sha256"] == duplicate_hash]
        self.assertEqual(len(duplicate_rows), 2)
        self.assertTrue(all(row["duplicate_source_within_split"] for row in duplicate_rows))
        self.assertTrue(all(row["eligible_for_training"] for row in duplicate_rows))

        qalb_leak = next(row for row in registry if row["document_id"] == "t4.ar")
        self.assertTrue(qalb_leak["exact_source_overlap_with_qalb_test"])
        self.assertFalse(qalb_leak["eligible_for_training"])

        nahw_leak = next(row for row in registry if row["document_id"] == "d2.ar")
        self.assertTrue(nahw_leak["exact_source_overlap_with_nahw"])
        self.assertFalse(nahw_leak["eligible_for_development"])

        self.assertTrue(
            all(not row["eligible_for_training"] for row in registry if row["split"] == "test")
        )
        self.assertTrue(
            all(not row["eligible_for_development"] for row in registry if row["split"] == "test")
        )


if __name__ == "__main__":
    unittest.main()
