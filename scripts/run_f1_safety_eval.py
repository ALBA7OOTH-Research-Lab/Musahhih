#!/usr/bin/env python3
"""Preflight or execute the matched F1 capability/overcorrection diagnostics."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import gc
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess

from scripts.f1_eval_utils import (
    BASE_MODEL_ID,
    BASE_MODEL_REVISION,
    EvaluationSafetyError,
    validate_adapter_checkpoint,
)
from scripts.f1_safety_eval_utils import (
    BOOTSTRAP_SAMPLES,
    CONFIRMATION,
    EXPECTED_CAPABILITY_SHA256,
    EXPECTED_OVERCORRECTION_SHA256,
    SEED,
    load_capability_records,
    load_overcorrection_records,
    paired_binary_comparison,
    require_execution_authorization,
    select_highest_logit,
    sha256_file,
)
from scripts.nahw_baseline_utils import parse_model_response


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUTS = ROOT / "data" / "processed" / "f1_safety_eval"
DEFAULT_OUTPUTS = ROOT / "outputs"
RUN_ID = "F1-P1__gemma3-4b-it__safety-diagnostics__s3407__r01"
MAX_SEQUENCE_LENGTH = 2048
MAX_NEW_TOKENS = 32
SYSTEMS = ("B0", "F1-P1")
EXPECTED_PYTHON = "3.12.13"
EXPECTED_CUDA = "12.4"
EXPECTED_PACKAGES = {
    "torch": "2.6.0+cu124",
    "transformers": "4.56.2",
    "unsloth": "2026.7.3",
    "accelerate": "1.13.0",
    "peft": "0.19.1",
    "trl": "0.22.2",
}


def _git_sha() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _versions() -> dict:
    packages = {}
    for name in ("torch", "transformers", "unsloth", "accelerate", "peft", "trl"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {"python": platform.python_version(), "packages": packages}


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def validate_outputs_root(path: Path) -> Path:
    resolved = Path(path).expanduser().resolve()
    if _is_relative_to(resolved, ROOT) and not _is_relative_to(
        resolved, DEFAULT_OUTPUTS.resolve()
    ):
        raise EvaluationSafetyError(
            "repository-local safety outputs must stay under ignored outputs/"
        )
    return resolved


class FrozenSystem:
    """A fresh pinned 4-bit base, optionally with the frozen private adapter."""

    def __init__(self, system_id: str, adapter_path: Path | None) -> None:
        if system_id not in SYSTEMS:
            raise EvaluationSafetyError("unknown safety-diagnostic system")
        self.system_id = system_id
        self.adapter_path = Path(adapter_path) if adapter_path else None
        self.model = None
        self.processor = None
        self.torch = None
        self.candidate_token_ids: dict[str, int] = {}

    def load(self) -> dict:
        try:
            import torch
            from peft import PeftModel
            from unsloth import FastModel
        except (ImportError, OSError) as error:
            raise EvaluationSafetyError("GPU inference dependencies are unavailable") from error
        if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
            raise EvaluationSafetyError("exactly one CUDA GPU is required")
        properties = torch.cuda.get_device_properties(0)
        if "P100" not in properties.name.upper():
            raise EvaluationSafetyError("the frozen matched runtime requires a Kaggle P100")
        versions = _versions()
        if versions["python"] != EXPECTED_PYTHON:
            raise EvaluationSafetyError("Python version differs from the frozen runtime")
        if versions["packages"] != EXPECTED_PACKAGES:
            raise EvaluationSafetyError("package versions differ from the frozen runtime")
        if torch.version.cuda != EXPECTED_CUDA:
            raise EvaluationSafetyError("CUDA version differs from the frozen runtime")
        torch.manual_seed(SEED)
        torch.cuda.manual_seed_all(SEED)
        try:
            base, self.processor = FastModel.from_pretrained(
                model_name=BASE_MODEL_ID,
                revision=BASE_MODEL_REVISION,
                max_seq_length=MAX_SEQUENCE_LENGTH,
                dtype=None,
                load_in_4bit=True,
                full_finetuning=False,
            )
            if self.adapter_path is None:
                self.model = base
            else:
                self.model = PeftModel.from_pretrained(
                    base, str(self.adapter_path), is_trainable=False
                )
            if hasattr(FastModel, "for_inference"):
                FastModel.for_inference(self.model)
            self.model.eval()
        except Exception as error:
            raise EvaluationSafetyError(
                f"unable to load pinned {self.system_id} system"
            ) from error
        tokenizer = getattr(self.processor, "tokenizer", None)
        if tokenizer is None:
            raise EvaluationSafetyError("pinned processor does not expose a tokenizer")
        for letter in "ABCDE":
            token_ids = tokenizer(letter, add_special_tokens=False)["input_ids"]
            if len(token_ids) != 1:
                raise EvaluationSafetyError(
                    "every ArabicMMLU answer letter must tokenize to one token"
                )
            self.candidate_token_ids[letter] = token_ids[0]
        if len(set(self.candidate_token_ids.values())) != 5:
            raise EvaluationSafetyError("ArabicMMLU answer token IDs must be distinct")
        self.torch = torch
        return {
            **versions,
            "cuda": torch.version.cuda,
            "gpu": properties.name,
            "gpu_total_memory_bytes": properties.total_memory,
            "dtype_argument": None,
            "load_in_4bit": True,
            "max_sequence_length": MAX_SEQUENCE_LENGTH,
            "candidate_token_ids": dict(self.candidate_token_ids),
        }

    def _chat_inputs(self, prompt: str):
        messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
        inputs = self.processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(self.model.device)
        if inputs["input_ids"].shape[-1] > MAX_SEQUENCE_LENGTH:
            raise EvaluationSafetyError("input exceeds the frozen sequence limit")
        return inputs

    def generate_correction(self, prompt: str) -> str:
        inputs = self._chat_inputs(prompt)
        input_length = inputs["input_ids"].shape[-1]
        with self.torch.inference_mode():
            output = self.model.generate(
                **inputs, do_sample=False, max_new_tokens=MAX_NEW_TOKENS
            )
        return self.processor.decode(output[0][input_length:], skip_special_tokens=True)

    def score_choices(self, prompt: str, choices: list[str]) -> tuple[str, dict[str, float]]:
        inputs = self._chat_inputs(prompt)
        with self.torch.inference_mode():
            next_logits = self.model(**inputs).logits[0, -1]
        scores = {
            choice: float(next_logits[self.candidate_token_ids[choice]].item())
            for choice in choices
        }
        prediction = select_highest_logit(choices, scores)
        return prediction, scores

    def close(self) -> None:
        self.model = None
        self.processor = None
        self.candidate_token_ids = {}
        gc.collect()
        if self.torch is not None and self.torch.cuda.is_available():
            self.torch.cuda.empty_cache()
        self.torch = None


def _run_system(
    system_id: str,
    adapter: Path | None,
    overcorrection_records: list[dict],
    capability_records: list[dict],
    run_dir: Path,
) -> tuple[list[dict], list[dict], dict]:
    slug = system_id.lower().replace("-", "_")
    over_path = run_dir / f"{slug}_overcorrection_predictions.jsonl"
    capability_path = run_dir / f"{slug}_capability_predictions.jsonl"
    model = FrozenSystem(system_id, adapter)
    runtime = model.load()
    over_rows: list[dict] = []
    capability_rows: list[dict] = []
    try:
        with over_path.open("x", encoding="utf-8", newline="\n") as stream:
            for record in overcorrection_records:
                raw = model.generate_correction(record["prompt"])
                parsed, warnings = parse_model_response(raw)
                suspicious = bool(set(warnings) - {"outer_formatting_removed"})
                unchanged = parsed == record["gold_unchanged_token"] and not suspicious
                row = {
                    **record,
                    "system_id": system_id,
                    "raw_model_response": raw,
                    "parsed_correction": parsed,
                    "parsing_warnings": warnings,
                    "unchanged_exact": unchanged,
                }
                stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                stream.flush()
                over_rows.append(row)
        with capability_path.open("x", encoding="utf-8", newline="\n") as stream:
            for record in capability_records:
                prediction, scores = model.score_choices(record["prompt"], record["choices"])
                row = {
                    **record,
                    "system_id": system_id,
                    "candidate_logits": scores,
                    "predicted_choice": prediction,
                    "exact_match": prediction == record["gold_choice"],
                }
                stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                stream.flush()
                capability_rows.append(row)
    finally:
        model.close()
    return over_rows, capability_rows, {
        "runtime": runtime,
        "overcorrection_predictions_sha256": sha256_file(over_path),
        "capability_predictions_sha256": sha256_file(capability_path),
        "overcorrection_counts": {
            "records": len(over_rows),
            "unchanged_exact": sum(row["unchanged_exact"] for row in over_rows),
            "unchanged_accuracy": sum(row["unchanged_exact"] for row in over_rows)
            / len(over_rows),
            "overcorrection_rate": 1.0
            - sum(row["unchanged_exact"] for row in over_rows) / len(over_rows),
            "empty_outputs": sum(not row["parsed_correction"] for row in over_rows),
            "suspicious_outputs": sum(
                bool(set(row["parsing_warnings"]) - {"outer_formatting_removed"})
                for row in over_rows
            ),
            "warning_counts": dict(sorted(Counter(
                warning for row in over_rows for warning in row["parsing_warnings"]
            ).items())),
        },
        "capability_counts": {
            "records": len(capability_rows),
            "correct": sum(row["exact_match"] for row in capability_rows),
            "accuracy": sum(row["exact_match"] for row in capability_rows)
            / len(capability_rows),
        },
    }


def execute(
    args: argparse.Namespace,
    overcorrection_records: list[dict],
    capability_records: list[dict],
    adapter_meta: dict,
) -> dict:
    run_id = RUN_ID.replace("__r01", f"__r{args.replicate:02d}")
    run_dir = validate_outputs_root(args.outputs_root) / run_id
    try:
        run_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise EvaluationSafetyError("run directory already exists; never overwrite it") from error
    summary_path = run_dir / "summary.json"
    system_outputs = {}
    completed_records = 0
    try:
        paired = {}
        for system_id in SYSTEMS:
            over_rows, capability_rows, metadata = _run_system(
                system_id,
                None if system_id == "B0" else Path(args.adapter),
                overcorrection_records,
                capability_records,
                run_dir,
            )
            completed_records += len(over_rows) + len(capability_rows)
            system_outputs[system_id] = {
                "overcorrection": over_rows,
                "capability": capability_rows,
                **metadata,
            }
        if system_outputs["B0"]["runtime"] != system_outputs["F1-P1"]["runtime"]:
            raise EvaluationSafetyError("B0 and F1-P1 runtime metadata do not match")
        paired["overcorrection_unchanged"] = paired_binary_comparison(
            system_outputs["B0"]["overcorrection"],
            system_outputs["F1-P1"]["overcorrection"],
            outcome_field="unchanged_exact",
            bootstrap_samples=BOOTSTRAP_SAMPLES,
            seed=SEED,
        )
        paired["arabicmmlu_accuracy"] = paired_binary_comparison(
            system_outputs["B0"]["capability"],
            system_outputs["F1-P1"]["capability"],
            outcome_field="exact_match",
            stratum_field="task",
            bootstrap_samples=BOOTSTRAP_SAMPLES,
            seed=SEED,
        )
        per_task = {}
        for task in sorted({row["task"] for row in capability_records}):
            per_task[task] = {}
            for system_id in SYSTEMS:
                rows = [
                    row for row in system_outputs[system_id]["capability"]
                    if row["task"] == task
                ]
                per_task[task][system_id] = sum(row["exact_match"] for row in rows) / len(rows)
        summary = {
            "schema_version": 1,
            "experiment_id": run_id,
            "run_status": "complete",
            "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "git_commit": _git_sha(),
            "approval": {
                "approved_protocol_commit": args.approved_protocol_commit,
                "approval_reference": args.approval_reference,
            },
            "model": {
                "base_model_id": BASE_MODEL_ID,
                "base_model_revision": BASE_MODEL_REVISION,
                "selected_checkpoint": "checkpoint-250",
                **adapter_meta,
            },
            "data": {
                "overcorrection": {
                    "name": "QALB-2015-L2-Dev corrected targets",
                    "split": "dev",
                    "records": len(overcorrection_records),
                    "input_sha256": EXPECTED_OVERCORRECTION_SHA256,
                },
                "capability": {
                    "name": "MBZUAI/ArabicMMLU balanced subset",
                    "split": "test",
                    "records": len(capability_records),
                    "input_sha256": EXPECTED_CAPABILITY_SHA256,
                },
            },
            "decoding": {
                "overcorrection": {
                    "do_sample": False,
                    "temperature_argument": None,
                    "max_new_tokens": MAX_NEW_TOKENS,
                    "seed": SEED,
                },
                "capability": {
                    "method": "single-token next-logit argmax over available A-E",
                    "sampling": False,
                    "tie_break": "earliest displayed option",
                },
            },
            "paired_comparisons": paired,
            "arabicmmlu_per_task_accuracy": per_task,
            "systems": {
                system_id: {
                    key: value for key, value in system_outputs[system_id].items()
                    if key not in {"overcorrection", "capability"}
                }
                for system_id in SYSTEMS
            },
            "safeguards": {
                "training": False,
                "checkpoint_selection": False,
                "nahw_passage_used": False,
                "qalb_test_used": False,
                "matched_single_kernel": True,
                "overwrite": False,
            },
        }
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        return summary
    except Exception as error:
        completed_records = 0
        for path in run_dir.glob("*_predictions.jsonl"):
            try:
                with path.open("r", encoding="utf-8") as stream:
                    completed_records += sum(bool(line.strip()) for line in stream)
            except (OSError, UnicodeError):
                pass
        failure = {
            "schema_version": 1,
            "experiment_id": run_id,
            "run_status": "invalid",
            "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "completed_records": completed_records,
            "error_type": type(error).__name__,
        }
        summary_path.write_text(json.dumps(failure, indent=2) + "\n", encoding="utf-8")
        raise EvaluationSafetyError(
            "matched safety diagnostics failed; invalid artifacts were preserved"
        ) from error


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument(
        "--overcorrection-input",
        type=Path,
        default=DEFAULT_INPUTS / "overcorrection.jsonl",
    )
    parser.add_argument(
        "--capability-input",
        type=Path,
        default=DEFAULT_INPUTS / "arabicmmlu.jsonl",
    )
    parser.add_argument("--outputs-root", type=Path, default=DEFAULT_OUTPUTS)
    parser.add_argument("--replicate", type=int, default=1)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirmation")
    parser.add_argument("--approved-protocol-commit")
    parser.add_argument("--approval-reference")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        if not 1 <= args.replicate <= 99:
            raise EvaluationSafetyError("replicate must be between 1 and 99")
        adapter_meta = validate_adapter_checkpoint(args.adapter)
        overcorrection_records = load_overcorrection_records(args.overcorrection_input)
        capability_records = load_capability_records(args.capability_input)
        validate_outputs_root(args.outputs_root)
        if not args.execute:
            print(json.dumps({
                "status": "preflight_passed",
                "inference_executed": False,
                "overcorrection_records": len(overcorrection_records),
                "capability_records": len(capability_records),
                "adapter": adapter_meta,
            }, indent=2))
            return
        require_execution_authorization(
            args.confirmation,
            args.approved_protocol_commit,
            args.approval_reference,
            repository=ROOT,
        )
        summary = execute(args, overcorrection_records, capability_records, adapter_meta)
        print(json.dumps({
            "experiment_id": summary["experiment_id"],
            "run_status": summary["run_status"],
        }, indent=2))
    except (EvaluationSafetyError, OSError) as error:
        raise SystemExit(f"ERROR: {error}") from error


if __name__ == "__main__":
    main()
