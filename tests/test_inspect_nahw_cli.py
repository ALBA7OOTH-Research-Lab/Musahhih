import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
RAW_PASSAGE = ROOT / "data" / "raw" / "nahw" / "Nahw-Passage.json"


class InspectNahwCliTests(unittest.TestCase):
    @unittest.skipUnless(RAW_PASSAGE.exists(), "Nahw data has not been downloaded")
    def test_prints_arabic_when_parent_console_uses_cp1252(self):
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "cp1252"
        result = subprocess.run(
            [sys.executable, "scripts/inspect_nahw.py"],
            cwd=ROOT,
            env=environment,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
        self.assertIn("records: 511", result.stdout.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
