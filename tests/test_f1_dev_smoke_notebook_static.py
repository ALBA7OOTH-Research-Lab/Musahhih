import ast
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "03_f1_private_dev_smoke.ipynb"


class F1DevSmokeNotebookStaticTests(unittest.TestCase):
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

    def test_generation_gate_is_disabled_by_default(self):
        self.assertIn("RUN_PRIVATE_DEV_SMOKE = False", self.source)
        self.assertIn("RUN_F1_P1_PRIVATE_DEV_SMOKE_25", self.source)

    def test_frozen_decoding_and_selection_are_explicit(self):
        for value in (
            "F1-P1-dev-smoke|3407|",
            "do_sample=False, max_new_tokens=256",
            "'temperature_argument': None",
            "'content': [{'type': 'text', 'text': message['content']}]",
            "[:25]",
            "checkpoint-250",
        ):
            self.assertIn(value, self.source)
        self.assertNotIn("max_new_tokens=32", self.source)

    def test_reload_only_workflow_has_no_training_construction(self):
        self.assertIn("FastModel.from_pretrained", self.source)
        self.assertIn("FastModel.for_inference", self.source)
        self.assertNotIn("SFTTrainer", self.source)
        self.assertNotIn("get_peft_model", self.source)
        self.assertNotIn("trainer.train", self.source)

    def test_private_and_test_set_safeguards_are_explicit(self):
        for value in (
            "dev_predictions.jsonl",
            "contains_corpus_text",
            "qalb_test_used",
            "nahw_passage_used",
            "checkpoint_selection_changed",
            "private_exact_match_metric_publication_allowed",
        ):
            self.assertIn(value, self.source)
        self.assertIn("never printed", self.source)


if __name__ == "__main__":
    unittest.main()
