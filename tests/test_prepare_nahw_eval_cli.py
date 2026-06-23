from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
RAW_PASSAGE = ROOT / "data" / "raw" / "nahw" / "Nahw-Passage.json"
PREPARED = ROOT / "data" / "processed" / "nahw_gec_test.jsonl"


class PrepareNahwEvalCliTests(unittest.TestCase):
    @unittest.skipUnless(RAW_PASSAGE.exists(), "Nahw data has not been downloaded")
    def test_writes_platform_independent_lf_jsonl(self):
        subprocess.run([sys.executable, "scripts/prepare_nahw_eval.py"], cwd=ROOT, check=True)
        content = PREPARED.read_bytes()
        self.assertEqual(content.count(b"\n"), 511)
        self.assertNotIn(b"\r\n", content)


if __name__ == "__main__":
    unittest.main()
