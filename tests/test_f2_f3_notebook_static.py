import ast
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "04_f2_f3_qlora.ipynb"


class F2F3NotebookStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = NOTEBOOK.read_text(encoding="utf-8")
        cls.payload = json.loads(cls.source)

    def test_notebook_and_code_cells_parse_without_saved_outputs(self):
        self.assertEqual(self.payload["nbformat"], 4)
        for index, cell in enumerate(self.payload["cells"]):
            if cell["cell_type"] == "code":
                ast.parse("".join(cell["source"]), filename=f"cell-{index}")
                self.assertIsNone(cell.get("execution_count"))
                self.assertEqual(cell.get("outputs"), [])

    def test_execution_and_approval_gates_default_off(self):
        for value in (
            "RUN_GPU_SMOKE = False",
            "RUN_FULL_TRAINING = False",
            "LOAD_PRIOR_SMOKE_SUMMARY = False",
            "APPROVED_WORKFLOW_COMMIT = ''",
            "APPROVAL_REFERENCE = ''",
            "GPU_SMOKE_CONFIRMATION_VALUE = ''",
            "FULL_TRAINING_CONFIRMATION_VALUE = ''",
        ):
            self.assertIn(value, self.source)

    def test_private_inputs_are_exactly_validated(self):
        for value in (
            "f2_train_records.jsonl",
            "f3_train_records.jsonl",
            "common_dev_records.jsonl",
            "validate_private_records(TRAIN_PATH, ARM)",
            "validate_private_records(DEV_PATH, 'development')",
            "require_execution_approval(APPROVED_WORKFLOW_COMMIT",
            "Only aggregate metadata was printed",
        ):
            self.assertIn(value, self.source)

    def test_p100_stack_and_gpu_probe_match_f1(self):
        for value in (
            "'torch': '2.6.0'",
            "'torchvision': '0.21.0'",
            "'xformers': '0.0.29.post3'",
            "'torchao': '0.16.0'",
            "'numpy': '2.0.2'",
            "https://download.pytorch.org/whl/cu124",
            "torch.ones(1, device='cuda')",
            "os.environ['UNSLOTH_COMPILE_DISABLE'] = '1'",
            "CPU is not a training fallback",
        ):
            self.assertIn(value, self.source)

    def test_model_lora_and_training_contract_are_frozen(self):
        for value in (
            "model_name=MODEL_ID",
            "revision=MODEL_REVISION",
            "max_seq_length=MAX_SEQUENCE_LENGTH",
            "load_in_4bit=True",
            "r=16",
            "lora_alpha=32",
            "lora_dropout=0.0",
            "random_state=SEED",
            "train_on_responses_only=True",
            "completion_only_loss=True",
            "eval_strategy='epoch'",
            "save_strategy='epoch'",
            "seed=SEED",
            "**TRAINING_CONFIG",
        ):
            self.assertIn(value, self.source)

    def test_length_smoke_and_full_training_gates_are_separate(self):
        for value in (
            "rendered_token_count(messages)",
            "max(lengths) > MAX_SEQUENCE_LENGTH",
            "LONGEST_INDEX = max",
            "require_smoke_confirmation(GPU_SMOKE_CONFIRMATION_VALUE",
            "require_full_training_confirmation(ARM",
            "SMOKE_RUNTIME_TAINTED",
            "workflow_commit",
            "ties within 1e-6 choose epoch 1",
        ):
            self.assertIn(value, self.source)

    def test_final_test_and_generation_are_out_of_scope(self):
        self.assertIn("QALB test and Nahw-Passage are never loaded here", self.source)
        self.assertIn("nahw_passage_used", self.source)
        self.assertIn("qalb_test_used", self.source)
        for forbidden in (
            "prepare_nahw_eval.py",
            "Nahw-Passage.json",
            "model.generate(",
            "XG training",
        ):
            self.assertNotIn(forbidden, self.source)


if __name__ == "__main__":
    unittest.main()
