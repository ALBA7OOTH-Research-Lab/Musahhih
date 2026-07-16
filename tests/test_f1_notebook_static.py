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
            "'torchao': '0.16.0'",
            "'numpy': '2.0.2'",
            "'pillow': PIL.__version__",
            "https://download.pytorch.org/whl/cu124",
            "torch.ones(1, device='cuda')",
            "os.environ['UNSLOTH_COMPILE_DISABLE'] = '1'",
            "'unsloth_compile_disabled': os.environ.get('UNSLOTH_COMPILE_DISABLE') == '1'",
        ):
            self.assertIn(value, self.source)

    def test_private_kaggle_transport_keeps_checksum_archive(self):
        self.assertIn("KAGGLE_PRIVATE_SOURCE_DIR", self.source)
        self.assertIn("QALB-0.9.1-Dec03-2021-SharedTasks.zip.bin", self.source)
        self.assertIn("data/raw/qalb/QALB-0.9.1-Dec03-2021-SharedTasks.zip", self.source)

    def test_gemma3_uses_collate_time_response_masking(self):
        for value in (
            "from unsloth.trainer import UnslothVisionDataCollator",
            "train_on_responses_only=True",
            "completion_only_loss=True",
            "instruction_part='<start_of_turn>user\\\\n'",
            "response_part='<start_of_turn>model\\\\n'",
            "response_collator([private_data['train'][0]])['labels'][0]",
            "dataset_kwargs={'skip_prepare_dataset': True}",
            "remove_unused_columns=False",
        ):
            self.assertIn(value, self.source)
        self.assertNotIn("from unsloth.chat_templates import train_on_responses_only", self.source)

    def test_token_length_guard_measures_text_sequence_not_batch(self):
        for value in (
            "text_tokenizer = getattr(processor, 'tokenizer', processor)",
            "def rendered_token_count(messages):",
            "return_attention_mask=False",
            "isinstance(input_ids[0], (list, tuple))",
            "if not lengths or min(lengths) < 2:",
            "LONGEST_INDEX = max(range(len(lengths)), key=lengths.__getitem__)",
            "'validated_sequence_lengths': True",
            "'selection': selection_metadata",
        ):
            self.assertIn(value, self.source)
        self.assertNotIn("len(processor(processor.apply_chat_template", self.source)

    def test_test_sets_are_explicitly_prohibited(self):
        self.assertIn("QALB test and Nahw-Passage are never loaded here", self.source)
