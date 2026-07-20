import ast
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "05_f2_private_dev_smoke.ipynb"


class F2DevSmokeNotebookStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = NOTEBOOK.read_text(encoding="utf-8")
        cls.payload = json.loads(cls.source)
        cls.code = "\n".join(
            "".join(cell["source"])
            for cell in cls.payload["cells"]
            if cell["cell_type"] == "code"
        )

    def test_notebook_and_code_cells_parse_without_saved_outputs(self):
        self.assertEqual(self.payload["nbformat"], 4)
        for index, cell in enumerate(self.payload["cells"]):
            self.assertTrue(cell.get("id"))
            if cell["cell_type"] == "code":
                ast.parse("".join(cell["source"]), filename=f"cell-{index}")
                self.assertIsNone(cell.get("execution_count"))
                self.assertEqual(cell.get("outputs"), [])

    def test_activation_is_disabled_and_uses_one_strict_private_config(self):
        for value in (
            "'stage': 'disabled'",
            "RUN_PRIVATE_DEV_SMOKE = EXECUTION_STAGE == 'private-dev-smoke'",
            "f2_dev_smoke_execution_config.json",
            "Expected at most one private",
            "set(EXECUTION_CONFIG) != CONFIG_KEYS",
            "RUN_F2_P1_PRIVATE_DEV_SMOKE_25",
            "issues/82#issuecomment-",
            "Do not edit this notebook to activate inference",
        ):
            self.assertIn(value, self.source)

    def test_activation_cell_defaults_off_and_accepts_only_exact_config(self):
        activation = "".join(self.payload["cells"][2]["source"])

        def execute_with(root: Path):
            source = activation.replace(
                "Path('/kaggle/input')", f"Path({str(root)!r})"
            )
            namespace = {}
            exec(compile(source, "activation-cell", "exec"), namespace)
            return namespace

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            defaults = execute_with(root)
            self.assertFalse(defaults["RUN_PRIVATE_DEV_SMOKE"])

            config_dir = root / "private-config"
            config_dir.mkdir()
            (config_dir / "f2_dev_smoke_execution_config.json").write_text(
                json.dumps(
                    {
                        "stage": "private-dev-smoke",
                        "approved_workflow_commit": "a" * 40,
                        "approval_reference": (
                            "https://github.com/ALBA7OOTH-Research-Lab/"
                            "Musahhih/issues/82#issuecomment-123456"
                        ),
                        "confirmation": "RUN_F2_P1_PRIVATE_DEV_SMOKE_25",
                    }
                ),
                encoding="utf-8",
            )
            activated = execute_with(root)
            self.assertTrue(activated["RUN_PRIVATE_DEV_SMOKE"])

            duplicate_dir = root / "duplicate"
            duplicate_dir.mkdir()
            (duplicate_dir / "f2_dev_smoke_execution_config.json").write_text(
                "{}", encoding="utf-8"
            )
            with self.assertRaisesRegex(RuntimeError, "Expected at most one"):
                execute_with(root)

    def test_repository_checks_out_the_exact_authorized_commit(self):
        setup = "".join(self.payload["cells"][4]["source"])
        for value in (
            "if dirty and RUN_PRIVATE_DEV_SMOKE:",
            "'fetch', '--no-tags', 'origin', 'main'",
            "'checkout', '--detach', APPROVED_WORKFLOW_COMMIT",
            "ACTUAL_WORKFLOW_COMMIT != APPROVED_WORKFLOW_COMMIT",
            "origin_url != REPO_URL",
        ):
            self.assertIn(value, setup)

    def test_checkpoint_and_development_inputs_are_hash_locked(self):
        for value in (
            "checkpoint-125",
            "935fdf02c95189934e40629f877d8692d325ef22895cbaa03fdb7390b0cd7b3e",
            "b07ab34155647961ea1de8fbfff0db8e17d00229da01f2b941a15a78499da986",
            "39edee5e31d79c791a4ab0b14b7b85b838e28bcc302d9e552f168a03ac870e1b",
            "f64edead0367e7659b107e5c4c309ed811d09071",
            "common_dev_records.jsonl",
            "validate_private_records(DEV_PATH, 'development')",
            "from scripts.f1_training_utils import sha256_file",
            "Selected adapter-model SHA-256 mismatch",
            "Selected adapter-config SHA-256 mismatch",
            "contains_corpus_text",
        ):
            self.assertIn(value, self.source)

    def test_model_is_reloaded_unmerged_without_training_construction(self):
        for value in (
            "FastModel.from_pretrained",
            "model_name=str(SELECTED_CHECKPOINT)",
            "load_in_4bit=True",
            "FastModel.for_inference(model)",
            "'adapter_merged': False",
        ):
            self.assertIn(value, self.code)
        for forbidden in (
            "get_peft_model",
            "SFTTrainer",
            "SFTConfig",
            "trainer.train",
            "optimizer.step",
        ):
            self.assertNotIn(forbidden, self.code)

    def test_selection_decoding_and_parser_are_frozen(self):
        for value in (
            'F2-P1-dev-smoke|{SEED}|',
            ")[:25]",
            "do_sample=False",
            "max_new_tokens=256",
            "'temperature_argument': None",
            "parse_model_response(response)",
            "input_tokens > MAX_SEQUENCE_LENGTH",
            "refusing truncation",
        ):
            self.assertIn(value, self.source)

    def test_outputs_preserve_private_rows_and_publish_no_development_metric(self):
        for value in (
            "dev_predictions.jsonl",
            "raw_response",
            "parsed_response",
            "f2_p1_dev_smoke_private_summary.json",
            "f2_p1_dev_smoke_public_summary.json",
            "'private_development_metric_published': False",
            "'nahw_passage_used': False",
            "'qalb_test_used': False",
            "'training_executed_in_smoke_kernel': False",
            "'f3_executed': False",
            "'xg_executed': False",
        ):
            self.assertIn(value, self.source)
        public_literal = self.code.split("public_summary =", 1)[1].split(
            "public_summary_path =", 1
        )[0]
        self.assertNotIn("private_exact_match_count", public_literal)

    def test_p100_setup_is_conditional_and_cpu_is_not_a_fallback(self):
        for value in (
            "P100_STACK = dict(P100_CORE_STACK)",
            "INITIAL_HEAVY_REPORT['compatible']",
            "https://download.pytorch.org/whl/cu124",
            "UNSLOTH_COMPILE_DISABLE",
            "CPU is not an inference fallback",
            "torch.ones(1, device='cuda')",
        ):
            self.assertIn(value, self.source)


if __name__ == "__main__":
    unittest.main()
