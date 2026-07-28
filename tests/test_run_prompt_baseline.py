import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.run_prompt_baseline import (
    DEFAULT_MAX_NEW_TOKENS,
    FINAL_CONFIRMATION,
    FINAL_MODEL_ID,
    FINAL_MODEL_REVISION,
    GemmaGenerator,
    KernelTimeBudget,
    ROOT,
    PromptRecord,
    RunConfig,
    RunSafetyError,
    TimeBudgetExhausted,
    assert_final_eval_allowed,
    build_summary,
    execute_run,
    experiment_id,
    aggregate_prompt_sha256,
    load_prompt_records,
    load_protocol_demos,
    prepare_run_directory,
    require_single_p100_runtime,
    require_final_execution_authorization,
    sha256_file,
    validate_private_path,
    validate_experiment_id,
)


class FakeCudaProbe:
    def __add__(self, other):
        return self

    def sum(self):
        return self

    def item(self):
        return 2


class PromptBaselineRunTests(unittest.TestCase):
    def write_jsonl(self, path, rows):
        path.write_text(
            "".join(json.dumps(row) + "\n" for row in rows),
            encoding="utf-8",
        )

    def test_gemma_generator_loads_pinned_quantized_model_with_unsloth(self):
        calls = []

        class FakeModel:
            def eval(self):
                calls.append("eval")

        class FakeFastModel:
            @staticmethod
            def from_pretrained(**kwargs):
                calls.append(kwargs)
                return FakeModel(), object()

        fake_unsloth = SimpleNamespace(FastModel=FakeFastModel)
        fake_torch = SimpleNamespace(
            __version__="torch-version",
            bfloat16="bfloat16",
            float16="float16",
            float32="float32",
            manual_seed=lambda seed: calls.append(("manual_seed", seed)),
            ones=lambda *args, **kwargs: FakeCudaProbe(),
            cuda=SimpleNamespace(
                is_available=lambda: True,
                is_bf16_supported=lambda: False,
                device_count=lambda: 1,
                get_device_name=lambda index: "Tesla P100-PCIE-16GB",
                manual_seed_all=lambda seed: calls.append(("cuda_seed", seed)),
                synchronize=lambda: calls.append("cuda_synchronize"),
            ),
        )
        generator = GemmaGenerator("example/model", "pinned-revision", 32)
        with (
            patch.dict(sys.modules, {"torch": fake_torch, "unsloth": fake_unsloth}),
            patch(
                "scripts.run_prompt_baseline.importlib.metadata.version",
                side_effect=lambda package: f"{package}-version",
            ),
        ):
            generator._load()

        self.assertEqual(
            next(call for call in calls if isinstance(call, dict)),
            {
                "model_name": "example/model",
                "revision": "pinned-revision",
                "max_seq_length": 2048,
                "dtype": "float16",
                "load_in_4bit": True,
                "full_finetuning": False,
            },
        )
        self.assertIn("eval", calls)
        self.assertEqual(generator.metadata["backend"], "unsloth")
        self.assertTrue(generator.metadata["load_in_4bit"])
        self.assertEqual(generator.metadata["temperature"], None)
        self.assertEqual(generator.metadata["seed"], 3407)

    def test_kernel_budget_stops_at_safe_boundary_and_rejects_future_start(self):
        now = 100_000.0
        budget = KernelTimeBudget(
            now - 34_199,
            now=lambda: now,
        )
        budget.require_next_record_budget()
        boundary = KernelTimeBudget(
            now - 34_200,
            now=lambda: now,
        )
        with self.assertRaises(TimeBudgetExhausted):
            boundary.require_next_record_budget()
        with self.assertRaisesRegex(RunSafetyError, "future"):
            KernelTimeBudget(now + 301, now=lambda: now)

    def test_p100_preflight_uses_pytorch_cuda_without_external_command(self):
        fake_torch = SimpleNamespace(
            ones=lambda *args, **kwargs: FakeCudaProbe(),
            cuda=SimpleNamespace(
                is_available=lambda: True,
                device_count=lambda: 1,
                get_device_name=lambda index: "Tesla P100-PCIE-16GB",
                synchronize=lambda: None,
            )
        )
        self.assertEqual(
            require_single_p100_runtime(fake_torch),
            {
                "cuda_available": True,
                "cuda_device_count": 1,
                "cuda_operation_passed": True,
                "device_name": "Tesla P100-PCIE-16GB",
                "require_p100": True,
            },
        )

    def test_p100_preflight_fails_closed_when_cuda_operation_cannot_execute(self):
        fake_torch = SimpleNamespace(
            ones=lambda *args, **kwargs: (_ for _ in ()).throw(
                RuntimeError("no kernel image is available")
            ),
            cuda=SimpleNamespace(
                is_available=lambda: True,
                device_count=lambda: 1,
                get_device_name=lambda index: "Tesla P100-PCIE-16GB",
                synchronize=lambda: None,
            ),
        )
        with self.assertRaisesRegex(RunSafetyError, "executable P100 CUDA operation"):
            require_single_p100_runtime(fake_torch)

    def test_p100_preflight_fails_closed_on_cuda_count_and_device(self):
        cases = [
            (
                SimpleNamespace(
                    cuda=SimpleNamespace(
                        is_available=lambda: False,
                        device_count=lambda: 0,
                        get_device_name=lambda index: "",
                    )
                ),
                "requires CUDA",
            ),
            (
                SimpleNamespace(
                    cuda=SimpleNamespace(
                        is_available=lambda: True,
                        device_count=lambda: 2,
                        get_device_name=lambda index: "Tesla P100",
                    )
                ),
                "exactly one CUDA device",
            ),
            (
                SimpleNamespace(
                    cuda=SimpleNamespace(
                        is_available=lambda: True,
                        device_count=lambda: 1,
                        get_device_name=lambda index: "Tesla T4",
                    )
                ),
                "requires a P100",
            ),
        ]
        for fake_torch, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(
                RunSafetyError, message
            ):
                require_single_p100_runtime(fake_torch)

    def test_experiment_id_uses_canonical_pattern(self):
        run_id = experiment_id("B1-P1", "gemma3-4b-it", "qalb14-dev", 3407, 1)
        self.assertEqual(run_id, "B1-P1__gemma3-4b-it__qalb14-dev__s3407__r01")
        self.assertEqual(validate_experiment_id(run_id), run_id)
        with self.assertRaisesRegex(RunSafetyError, "Invalid experiment ID"):
            validate_experiment_id("B1-P1__Gemma__nahw-passage__s3407__r1")

    def test_prepare_run_directory_refuses_to_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_id = experiment_id("B2-P1", "gemma3-4b-it", "qalb14-dev", 3407, 1)
            created = prepare_run_directory(root, run_id)
            self.assertEqual(created, root / run_id)
            self.assertTrue(created.is_dir())
            with self.assertRaisesRegex(RunSafetyError, "already exists"):
                prepare_run_directory(root, run_id)

    def test_final_nahw_evaluation_requires_explicit_confirmation(self):
        assert_final_eval_allowed("qalb14-dev", confirm_final_eval=False)
        with self.assertRaisesRegex(RunSafetyError, "Nahw-Passage final evaluation"):
            assert_final_eval_allowed("nahw-passage", confirm_final_eval=False)
        assert_final_eval_allowed("nahw-passage", confirm_final_eval=True)

    def test_build_summary_records_hashes_without_private_payloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_file = root / "input.jsonl"
            bundle_file = root / "bundle.json"
            prompt_file = root / "prompt.txt"
            predictions_file = root / "predictions.jsonl"
            input_file.write_text('{"id":"1"}\n', encoding="utf-8")
            bundle_file.write_text('{"field":"licensed corpus payload"}\n', encoding="utf-8")
            prompt_file.write_text("أعد الكلمة فقط\n", encoding="utf-8")
            predictions_file.write_text('{"parsed_correction":"x","exact_match":false}\n', encoding="utf-8")

            config = RunConfig(
                experiment_id="B1-P1__gemma3-4b-it__qalb14-dev__s3407__r01",
                protocol_id="B1-P1",
                model_slug="gemma3-4b-it",
                evaluation_slug="qalb14-dev",
                seed=3407,
                replicate=1,
            )
            summary = build_summary(
                config,
                input_path=input_file,
                prompt_template_path=prompt_file,
                predictions_path=predictions_file,
                bundle_path=bundle_file,
                run_status="planned",
            )

            self.assertEqual(summary["experiment_id"], config.experiment_id)
            self.assertEqual(summary["run_status"], "planned")
            self.assertEqual(summary["input_sha256"], sha256_file(input_file))
            self.assertEqual(summary["bundle_sha256"], sha256_file(bundle_file))
            self.assertEqual(
                summary["prediction_sha256"],
                hashlib.sha256(predictions_file.read_bytes()).hexdigest(),
            )
            serialized = json.dumps(summary, ensure_ascii=False)
            self.assertNotIn("licensed corpus payload", serialized)
            self.assertNotIn("أعد الكلمة فقط", serialized)

    def test_load_prompt_records_preserves_valid_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.jsonl"
            self.write_jsonl(
                path,
                [
                    {
                        "record_id": "r1",
                        "passage": "alpha beta",
                        "error": "beta",
                        "gold_correction": "better",
                        "metadata": {"split": "dev"},
                    },
                    {
                        "record_id": "r2",
                        "passage": "gamma delta",
                        "error": "delta",
                    },
                ],
            )

            rows = load_prompt_records(path)

            self.assertEqual(
                rows[0],
                PromptRecord(
                    record_id="r1",
                    passage="alpha beta",
                    error="beta",
                    gold_correction="better",
                    metadata={"split": "dev"},
                ),
            )
            self.assertIsNone(rows[1].gold_correction)
            self.assertEqual(rows[1].metadata, {})

    def test_load_prompt_records_accepts_frozen_nahw_id_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.jsonl"
            self.write_jsonl(
                path,
                [
                    {
                        "id": "nahw-1",
                        "passage": "alpha beta",
                        "error": "beta",
                        "gold_correction": "better",
                    }
                ],
            )

            rows = load_prompt_records(path)

            self.assertEqual(rows[0].record_id, "nahw-1")

    def test_load_prompt_records_rejects_conflicting_id_aliases(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.jsonl"
            self.write_jsonl(
                path,
                [
                    {
                        "id": "legacy",
                        "record_id": "canonical",
                        "passage": "alpha beta",
                        "error": "beta",
                    }
                ],
            )
            with self.assertRaisesRegex(RunSafetyError, "disagree"):
                load_prompt_records(path)

    def test_load_prompt_records_rejects_duplicates_and_invalid_fields(self):
        cases = [
            (
                [
                    {"record_id": "r1", "passage": "a", "error": "b"},
                    {"record_id": "r1", "passage": "c", "error": "d"},
                ],
                "duplicate record_id",
            ),
            ([{"record_id": "", "passage": "a", "error": "b"}], "record_id"),
            ([{"record_id": "r1", "passage": 3, "error": "b"}], "passage"),
            ([{"record_id": "r1", "passage": "a", "error": ""}], "error"),
            (
                [
                    {
                        "record_id": "r1",
                        "passage": "a",
                        "error": "b",
                        "gold_correction": 3,
                    }
                ],
                "gold_correction",
            ),
            (
                [
                    {
                        "record_id": "r1",
                        "passage": "a",
                        "error": "b",
                        "metadata": [],
                    }
                ],
                "metadata",
            ),
        ]
        for rows, message in cases:
            with self.subTest(message=message), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "input.jsonl"
                self.write_jsonl(path, rows)
                with self.assertRaisesRegex(RunSafetyError, message):
                    load_prompt_records(path)

    def test_private_paths_fail_closed_inside_repository(self):
        validate_private_path(Path("/private/tmp/input.jsonl"), label="input")
        validate_private_path(
            ROOT / "data" / "processed" / "qalb" / "input.jsonl",
            label="input",
        )
        validate_private_path(
            ROOT / "outputs" / "private" / "predictions.jsonl",
            label="output",
        )
        with self.assertRaisesRegex(RunSafetyError, "input path"):
            validate_private_path(ROOT / "README.md", label="input")

    def test_protocol_bundle_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "bundle.json"
            bundle.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "demonstrations": [
                            {
                                "source": f"source-{index}",
                                "error": f"error-{index}",
                                "correction": f"fix-{index}",
                            }
                            for index in range(5)
                        ],
                    }
                ),
                encoding="utf-8",
            )

            demos = load_protocol_demos("B1-P1", bundle)

            self.assertEqual(len(demos), 5)
            self.assertEqual(demos[0].passage, "source-0")
            with self.assertRaisesRegex(RunSafetyError, "does not accept"):
                load_protocol_demos("B2-P1", bundle)
            with self.assertRaisesRegex(RunSafetyError, "requires --bundle"):
                load_protocol_demos("B1-P1", None)

    def test_b1_bundle_rejects_wrong_schema_count_and_field_types(self):
        invalid_payloads = [
            {"schema_version": 2, "demonstrations": []},
            {"schema_version": 1, "demonstrations": []},
            {
                "schema_version": 1,
                "demonstrations": [
                    {"source": "s", "error": "e", "correction": "c"}
                    for _ in range(4)
                ]
                + [{"source": "s", "error": 2, "correction": "c"}],
            },
        ]
        for payload in invalid_payloads:
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as tmp:
                bundle = Path(tmp) / "bundle.json"
                bundle.write_text(json.dumps(payload), encoding="utf-8")
                with self.assertRaises(RunSafetyError):
                    load_protocol_demos("B1-P1", bundle)

    def test_execute_run_captures_private_predictions_and_text_free_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "input.jsonl"
            prompt_path = root / "prompt.txt"
            input_path.write_text('{"private":"payload"}\n', encoding="utf-8")
            prompt_path.write_text("frozen-template", encoding="utf-8")
            records = [
                PromptRecord("r1", "alpha beta", "beta", "fixed", {"split": "dev"}),
                PromptRecord("r2", "gamma delta", "delta", None, {}),
            ]
            config = RunConfig(
                experiment_id="B2-P1__gemma3-4b-it__qalb14-dev__s3407__r01",
                protocol_id="B2-P1",
                model_slug="gemma3-4b-it",
                evaluation_slug="qalb14-dev",
                seed=3407,
                replicate=1,
            )

            summary = execute_run(
                config,
                records,
                [],
                lambda prompt: "**fixed**",
                outputs_root=root / "outputs",
                input_path=input_path,
                prompt_template_path=prompt_path,
                runtime_metadata={"backend": "synthetic"},
                allow_outside_private_output=True,
            )

            run_dir = root / "outputs" / config.experiment_id
            prediction_rows = [
                json.loads(line)
                for line in (run_dir / "predictions.jsonl").read_text(
                    encoding="utf-8"
                ).splitlines()
            ]
            self.assertEqual(summary["run_status"], "complete")
            self.assertEqual(summary["counts"]["number_of_records"], 2)
            self.assertEqual(summary["counts"]["number_scored"], 1)
            self.assertEqual(summary["counts"]["number_correct"], 1)
            self.assertEqual(summary["runtime"], {"backend": "synthetic"})
            self.assertEqual(prediction_rows[0]["parsed_correction"], "fixed")
            self.assertTrue(prediction_rows[0]["exact_match"])
            self.assertIsNone(prediction_rows[1]["exact_match"])
            self.assertIn("outer_formatting_removed", prediction_rows[0]["parsing_warnings"])
            self.assertIn("alpha beta", prediction_rows[0]["prompt"])
            self.assertEqual(
                summary["aggregate_prompt_sha256"],
                aggregate_prompt_sha256(
                    [row["prompt_sha256"] for row in prediction_rows]
                ),
            )
            self.assertEqual(
                summary["prediction_sha256"],
                hashlib.sha256((run_dir / "predictions.jsonl").read_bytes()).hexdigest(),
            )
            serialized_summary = json.dumps(summary)
            self.assertNotIn("alpha beta", serialized_summary)
            self.assertNotIn("fixed", serialized_summary)
            self.assertEqual(
                (run_dir / "run.log").read_text(encoding="utf-8"),
                "run completed\n",
            )

            with self.assertRaisesRegex(RunSafetyError, "already exists"):
                execute_run(
                    config,
                    records,
                    [],
                    lambda prompt: "fixed",
                    outputs_root=root / "outputs",
                    input_path=input_path,
                    prompt_template_path=prompt_path,
                    allow_outside_private_output=True,
                )

    def test_execute_run_preserves_invalid_partial_artifacts_without_text_leak(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "input.jsonl"
            prompt_path = root / "prompt.txt"
            input_path.write_text('{"private":"payload"}\n', encoding="utf-8")
            prompt_path.write_text("frozen-template", encoding="utf-8")
            records = [
                PromptRecord("r1", "first private text", "private", "fixed", {}),
                PromptRecord("r2", "second private text", "private", "fixed", {}),
            ]
            config = RunConfig(
                experiment_id="B2-P1__gemma3-4b-it__qalb14-dev__s3407__r02",
                protocol_id="B2-P1",
                model_slug="gemma3-4b-it",
                evaluation_slug="qalb14-dev",
                seed=3407,
                replicate=2,
            )
            calls = 0

            def fail_on_second(prompt):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise RuntimeError("second private text must not leak")
                return "fixed"

            with self.assertRaisesRegex(RunSafetyError, "inference execution failed"):
                execute_run(
                    config,
                    records,
                    [],
                    fail_on_second,
                    outputs_root=root / "outputs",
                    input_path=input_path,
                    prompt_template_path=prompt_path,
                    allow_outside_private_output=True,
                )

            run_dir = root / "outputs" / config.experiment_id
            prediction_lines = (run_dir / "predictions.jsonl").read_text(
                encoding="utf-8"
            ).splitlines()
            summary_text = (run_dir / "summary.json").read_text(encoding="utf-8")
            log_text = (run_dir / "run.log").read_text(encoding="utf-8")
            summary = json.loads(summary_text)
            self.assertEqual(len(prediction_lines), 1)
            self.assertEqual(summary["run_status"], "invalid")
            self.assertEqual(summary["counts"]["completed_records"], 1)
            self.assertEqual(summary["error_type"], "RuntimeError")
            self.assertNotIn("private text", summary_text)
            self.assertNotIn("private text", log_text)
            self.assertEqual(log_text, "run invalid: inference execution failed\n")

    def test_timeout_handoff_is_metric_free_and_resume_skips_exact_prefix(self):
        class OneRecordBudget:
            safe_stop_elapsed_seconds = 34_200

            def __init__(self):
                self.checks = 0

            def elapsed_seconds(self):
                return 34_200 if self.checks > 1 else 100

            def require_next_record_budget(self):
                self.checks += 1
                if self.checks > 1:
                    raise TimeBudgetExhausted

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "input.jsonl"
            prompt_path = root / "prompt.txt"
            input_path.write_text('{"private":"payload"}\n', encoding="utf-8")
            prompt_path.write_text("frozen-template", encoding="utf-8")
            records = [
                PromptRecord("r1", "first private passage", "first", "one", {}),
                PromptRecord("r2", "second private passage", "second", "two", {}),
            ]
            config = RunConfig(
                experiment_id="B2-P1__gemma3-4b-it__nahw-passage__s3407__r01",
                protocol_id="B2-P1",
                model_slug="gemma3-4b-it",
                evaluation_slug="nahw-passage",
                seed=3407,
                replicate=1,
            )
            commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=ROOT,
                check=True,
                text=True,
                capture_output=True,
            ).stdout.strip()
            identity_args = {
                "model_id": FINAL_MODEL_ID,
                "model_revision": FINAL_MODEL_REVISION,
                "approved_protocol_commit": commit,
            }
            first_summary = execute_run(
                config,
                records,
                [],
                lambda prompt: "one",
                outputs_root=root / "segment-one",
                input_path=input_path,
                prompt_template_path=prompt_path,
                runtime_metadata={"backend": "synthetic"},
                allow_outside_private_output=True,
                budget=OneRecordBudget(),
                **identity_args,
            )
            first_dir = root / "segment-one" / config.experiment_id
            first_bytes = (first_dir / "predictions.jsonl").read_bytes()
            public_text = (first_dir / "summary.json").read_text(encoding="utf-8")
            progress = json.loads(
                (first_dir / "progress.json").read_text(encoding="utf-8")
            )
            self.assertEqual(first_summary["run_status"], "incomplete_time_budget")
            self.assertEqual(first_summary["completed_records"], 1)
            self.assertFalse(first_summary["metrics_reported"])
            self.assertNotIn("counts", first_summary)
            self.assertNotIn("number_correct", public_text)
            self.assertNotIn("private passage", public_text)
            self.assertEqual(progress["status"], "incomplete_time_budget")
            self.assertEqual(progress["completed_records"], 1)

            generated = []

            def finish(prompt):
                generated.append(prompt)
                return "two"

            final_summary = execute_run(
                config,
                records,
                [],
                finish,
                outputs_root=root / "segment-two",
                input_path=input_path,
                prompt_template_path=prompt_path,
                runtime_metadata={"backend": "synthetic"},
                allow_outside_private_output=True,
                resume_from=first_dir,
                **identity_args,
            )
            final_dir = root / "segment-two" / config.experiment_id
            self.assertEqual(final_summary["run_status"], "complete")
            self.assertEqual(len(generated), 1)
            self.assertIn("second private passage", generated[0])
            self.assertTrue(
                (final_dir / "predictions.jsonl").read_bytes().startswith(first_bytes)
            )
            self.assertEqual(final_summary["counts"]["number_of_records"], 2)

    def test_resume_rejects_tampered_private_prefix_before_new_directory(self):
        class ImmediateBudget:
            safe_stop_elapsed_seconds = 34_200

            def elapsed_seconds(self):
                return 34_200

            def require_next_record_budget(self):
                raise TimeBudgetExhausted

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "input.jsonl"
            prompt_path = root / "prompt.txt"
            input_path.write_text('{"private":"payload"}\n', encoding="utf-8")
            prompt_path.write_text("frozen-template", encoding="utf-8")
            records = [PromptRecord("r1", "private passage", "private", "fixed", {})]
            config = RunConfig(
                experiment_id="B2-P1__gemma3-4b-it__nahw-passage__s3407__r01",
                protocol_id="B2-P1",
                model_slug="gemma3-4b-it",
                evaluation_slug="nahw-passage",
                seed=3407,
                replicate=1,
            )
            commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=ROOT,
                check=True,
                text=True,
                capture_output=True,
            ).stdout.strip()
            identity_args = {
                "model_id": FINAL_MODEL_ID,
                "model_revision": FINAL_MODEL_REVISION,
                "approved_protocol_commit": commit,
            }
            execute_run(
                config,
                records,
                [],
                lambda prompt: "fixed",
                outputs_root=root / "source",
                input_path=input_path,
                prompt_template_path=prompt_path,
                allow_outside_private_output=True,
                budget=ImmediateBudget(),
                **identity_args,
            )
            source = root / "source" / config.experiment_id
            progress_path = source / "progress.json"
            progress = json.loads(progress_path.read_text(encoding="utf-8"))
            progress["identity"]["model_revision"] = "tampered"
            progress_path.write_text(json.dumps(progress), encoding="utf-8")

            destination = root / "destination"
            with self.assertRaisesRegex(RunSafetyError, "identity mismatch"):
                execute_run(
                    config,
                    records,
                    [],
                    lambda prompt: "fixed",
                    outputs_root=destination,
                    input_path=input_path,
                    prompt_template_path=prompt_path,
                    allow_outside_private_output=True,
                    resume_from=source,
                    **identity_args,
                )
            self.assertFalse((destination / config.experiment_id).exists())

            progress["identity"]["model_revision"] = FINAL_MODEL_REVISION
            progress_path.write_text(json.dumps(progress), encoding="utf-8")
            resumed = execute_run(
                config,
                records,
                [],
                lambda prompt: "fixed",
                outputs_root=root / "empty-prefix-resume",
                input_path=input_path,
                prompt_template_path=prompt_path,
                allow_outside_private_output=True,
                resume_from=source,
                **identity_args,
            )
            self.assertEqual(resumed["run_status"], "complete")
            self.assertEqual(resumed["counts"]["number_of_records"], 1)

    def test_resume_rejects_hash_schema_order_and_score_tampering(self):
        class TwoRecordBudget:
            safe_stop_elapsed_seconds = 34_200

            def __init__(self):
                self.checks = 0

            def elapsed_seconds(self):
                return 34_200 if self.checks > 2 else 100

            def require_next_record_budget(self):
                self.checks += 1
                if self.checks > 2:
                    raise TimeBudgetExhausted

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "input.jsonl"
            prompt_path = root / "prompt.txt"
            input_path.write_text('{"private":"payload"}\n', encoding="utf-8")
            prompt_path.write_text("frozen-template", encoding="utf-8")
            records = [
                PromptRecord("r1", "private one", "one", "fixed-1", {}),
                PromptRecord("r2", "private two", "two", "fixed-2", {}),
                PromptRecord("r3", "private three", "three", "fixed-3", {}),
            ]
            config = RunConfig(
                experiment_id="B2-P1__gemma3-4b-it__nahw-passage__s3407__r01",
                protocol_id="B2-P1",
                model_slug="gemma3-4b-it",
                evaluation_slug="nahw-passage",
                seed=3407,
                replicate=1,
            )
            commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=ROOT,
                check=True,
                text=True,
                capture_output=True,
            ).stdout.strip()
            identity_args = {
                "model_id": FINAL_MODEL_ID,
                "model_revision": FINAL_MODEL_REVISION,
                "approved_protocol_commit": commit,
            }
            responses = iter(("fixed-1", "fixed-2"))
            execute_run(
                config,
                records,
                [],
                lambda prompt: next(responses),
                outputs_root=root / "source-root",
                input_path=input_path,
                prompt_template_path=prompt_path,
                allow_outside_private_output=True,
                budget=TwoRecordBudget(),
                **identity_args,
            )
            source = root / "source-root" / config.experiment_id

            def synchronize_hashes(case_dir):
                prediction_hash = sha256_file(case_dir / "predictions.jsonl")
                for name in ("progress.json", "summary.json"):
                    path = case_dir / name
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    payload["prediction_sha256"] = prediction_hash
                    path.write_text(json.dumps(payload), encoding="utf-8")

            cases = {}
            for case_name in ("hash", "schema", "order", "score"):
                case_dir = root / f"case-{case_name}"
                shutil.copytree(source, case_dir)
                cases[case_name] = case_dir

            with (cases["hash"] / "predictions.jsonl").open(
                "a", encoding="utf-8"
            ) as stream:
                stream.write(" ")

            schema_rows = [
                json.loads(line)
                for line in (cases["schema"] / "predictions.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            schema_rows[0]["unexpected"] = True
            self.write_jsonl(cases["schema"] / "predictions.jsonl", schema_rows)
            synchronize_hashes(cases["schema"])

            order_rows = [
                json.loads(line)
                for line in (cases["order"] / "predictions.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            order_rows.reverse()
            self.write_jsonl(cases["order"] / "predictions.jsonl", order_rows)
            synchronize_hashes(cases["order"])

            score_rows = [
                json.loads(line)
                for line in (cases["score"] / "predictions.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            score_rows[0]["exact_match"] = False
            self.write_jsonl(cases["score"] / "predictions.jsonl", score_rows)
            synchronize_hashes(cases["score"])

            expected_messages = {
                "hash": "SHA-256 mismatch",
                "schema": "schema mismatch",
                "order": "record mismatch",
                "score": "score mismatch",
            }
            for case_name, case_dir in cases.items():
                destination = root / f"destination-{case_name}"
                with self.subTest(case=case_name), self.assertRaisesRegex(
                    RunSafetyError, expected_messages[case_name]
                ):
                    execute_run(
                        config,
                        records,
                        [],
                        lambda prompt: "fixed-3",
                        outputs_root=destination,
                        input_path=input_path,
                        prompt_template_path=prompt_path,
                        allow_outside_private_output=True,
                        resume_from=case_dir,
                        **identity_args,
                    )
                self.assertFalse((destination / config.experiment_id).exists())

    def test_final_authorization_requires_exact_frozen_identity(self):
        config = RunConfig(
            experiment_id="B2-P1__gemma3-4b-it__nahw-passage__s3407__r01",
            protocol_id="B2-P1",
            model_slug="gemma3-4b-it",
            evaluation_slug="nahw-passage",
            seed=3407,
            replicate=1,
        )
        commit = "a" * 40
        with (
            patch("scripts.run_prompt_baseline.git_commit_sha", return_value=commit),
            patch(
                "scripts.run_prompt_baseline.sha256_file",
                return_value="acb3cfd204b35d5415532fbd32a4a5231b553fae329ab8f48e8454609e10279b",
            ),
        ):
            require_final_execution_authorization(
                confirmation=FINAL_CONFIRMATION,
                approved_protocol_commit=commit,
                approval_reference=(
                    "https://github.com/ALBA7OOTH-Research-Lab/Musahhih/"
                    "issues/107#issuecomment-123"
                ),
                model_id=FINAL_MODEL_ID,
                model_revision=FINAL_MODEL_REVISION,
                max_new_tokens=32,
                config=config,
                input_path=Path("synthetic-private-input"),
                bundle_path=None,
                record_count=511,
            )
            with self.assertRaisesRegex(RunSafetyError, "confirmation"):
                require_final_execution_authorization(
                    confirmation="wrong",
                    approved_protocol_commit=commit,
                    approval_reference=(
                        "https://github.com/ALBA7OOTH-Research-Lab/Musahhih/"
                        "issues/107#issuecomment-123"
                    ),
                    model_id=FINAL_MODEL_ID,
                    model_revision=FINAL_MODEL_REVISION,
                    max_new_tokens=32,
                    config=config,
                    input_path=Path("synthetic-private-input"),
                    bundle_path=None,
                    record_count=511,
                )

    def test_cli_help_exposes_explicit_execution_controls_without_model_loading(self):
        result = subprocess.run(
            [sys.executable, "-m", "scripts.run_prompt_baseline", "--help"],
            check=True,
            text=True,
            capture_output=True,
        )
        self.assertIn("--execute", result.stdout)
        self.assertIn("--model-revision", result.stdout)
        self.assertIn("--allow-outside-private-output", result.stdout)
        self.assertIn("--kernel-start-epoch-seconds", result.stdout)
        self.assertIn("--resume-from", result.stdout)
        self.assertIn("--approved-protocol-commit", result.stdout)
        self.assertIn("--approval-reference", result.stdout)
        self.assertEqual(DEFAULT_MAX_NEW_TOKENS, 32)

    def test_cli_defaults_to_planned_scaffold(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "input.jsonl"
            prompt_path = root / "prompt.txt"
            output_root = root / "outputs"
            input_path.write_text('{"private":"payload"}\n', encoding="utf-8")
            prompt_path.write_text("frozen-template", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "scripts.run_prompt_baseline",
                    "--protocol-id",
                    "B2-P1",
                    "--evaluation-slug",
                    "qalb14-dev",
                    "--input",
                    str(input_path),
                    "--prompt-template",
                    str(prompt_path),
                    "--outputs-root",
                    str(output_root),
                    "--allow-outside-private-output",
                ],
                check=True,
                text=True,
                capture_output=True,
            )

            run_id = "B2-P1__gemma3-4b-it__qalb14-dev__s3407__r01"
            summary = json.loads(
                (output_root / run_id / "summary.json").read_text(encoding="utf-8")
            )
            self.assertEqual(summary["run_status"], "planned")
            self.assertIn('"run_status": "planned"', result.stdout)

    def test_cli_execution_contract_fails_before_model_loading(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "input.jsonl"
            prompt_path = root / "prompt.txt"
            bundle_path = root / "bundle.json"
            input_path.write_text(
                '{"record_id":"r1","passage":"alpha","error":"alpha"}\n',
                encoding="utf-8",
            )
            prompt_path.write_text("frozen-template", encoding="utf-8")
            bundle_path.write_text('{}\n', encoding="utf-8")
            base = [
                sys.executable,
                "-m",
                "scripts.run_prompt_baseline",
                "--evaluation-slug",
                "qalb14-dev",
                "--input",
                str(input_path),
                "--prompt-template",
                str(prompt_path),
                "--outputs-root",
                str(root / "outputs"),
                "--allow-outside-private-output",
                "--execute",
                "--model-revision",
                "fixed-revision",
            ]

            missing_bundle = subprocess.run(
                base + ["--protocol-id", "B1-P1"],
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(missing_bundle.returncode, 0)
            self.assertIn("requires --bundle", missing_bundle.stderr)

            unexpected_bundle = subprocess.run(
                base
                + [
                    "--protocol-id",
                    "B2-P1",
                    "--bundle",
                    str(bundle_path),
                ],
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(unexpected_bundle.returncode, 0)
            self.assertIn("does not accept --bundle", unexpected_bundle.stderr)

    def test_cli_rejects_unpinned_execution_and_unsafe_output_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "input.jsonl"
            prompt_path = root / "prompt.txt"
            input_path.write_text(
                '{"record_id":"r1","passage":"alpha","error":"alpha"}\n',
                encoding="utf-8",
            )
            prompt_path.write_text("frozen-template", encoding="utf-8")
            command = [
                sys.executable,
                "-m",
                "scripts.run_prompt_baseline",
                "--protocol-id",
                "B2-P1",
                "--evaluation-slug",
                "qalb14-dev",
                "--input",
                str(input_path),
                "--prompt-template",
                str(prompt_path),
                "--outputs-root",
                str(root / "outputs"),
            ]

            unsafe = subprocess.run(command, text=True, capture_output=True)
            self.assertNotEqual(unsafe.returncode, 0)
            self.assertIn("private outputs must stay under", unsafe.stderr)

            unpinned = subprocess.run(
                command + ["--allow-outside-private-output", "--execute"],
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(unpinned.returncode, 0)
            self.assertIn("--model-revision", unpinned.stderr)


if __name__ == "__main__":
    unittest.main()
