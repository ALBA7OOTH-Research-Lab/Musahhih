import ast
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "02_f1_natural_qlora.ipynb"


class F1NotebookStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
        cls.source = NOTEBOOK.read_text(encoding="utf-8")

    def test_notebook_and_code_cells_parse(self):
        self.assertEqual(self.payload["nbformat"], 4)
        for index, cell in enumerate(self.payload["cells"]):
            if cell["cell_type"] == "code":
                ast.parse("".join(cell["source"]), filename=f"cell-{index}")
                self.assertIsNone(cell.get("execution_count"))
                self.assertEqual(cell.get("outputs"), [])

    def test_execution_gates_default_off(self):
        for setting in (
            "RUN_GPU_SMOKE = False",
            "RUN_FULL_TRAINING = False",
            "RUN_PRIVATE_DEV_SMOKE = False",
        ):
            self.assertIn(setting, self.source)

    def test_kaggle_is_primary_and_t4_is_not_assumed(self):
        self.assertIn("/kaggle/working", self.source)
        self.assertIn("KAGGLE_PRIVATE_INPUT_DIR", self.source)
        self.assertIn("CPU is not a training fallback", self.source)
        self.assertNotIn('"gpuType": "T4"', self.source)

    def test_p100_stack_is_explicit_and_probed(self):
        for value in (
            "'torch': '2.6.0'",
            "'torchvision': '0.21.0'",
            "'xformers': '0.0.29.post3'",
            "'torchao': '0.12.0'",
            "https://download.pytorch.org/whl/cu124",
            "torch.ones(1, device='cuda')",
        ):
            self.assertIn(value, self.source)

    def test_private_kaggle_transport_keeps_checksum_archive(self):
        self.assertIn("KAGGLE_PRIVATE_SOURCE_DIR", self.source)
        self.assertIn("QALB-0.9.1-Dec03-2021-SharedTasks.zip.bin", self.source)
        self.assertIn("data/raw/qalb/QALB-0.9.1-Dec03-2021-SharedTasks.zip", self.source)

    def test_test_sets_are_explicitly_prohibited(self):
        self.assertIn("QALB test and Nahw-Passage are never loaded here", self.source)
