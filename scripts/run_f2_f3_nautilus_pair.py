#!/usr/bin/env python3
"""Run one fail-closed A100 preflight or one paired F2/F3 seed training job."""

from __future__ import annotations

import argparse
import gc
import hashlib
import importlib
import importlib.metadata as metadata
import json
import os
import platform
import re
import shutil
from pathlib import Path

from scripts.f1_training_utils import (
    LORA_TARGETS,
    MAX_SEQUENCE_LENGTH,
    MODEL_ID,
    MODEL_REVISION,
    TRAINING_CONFIG,
)
from scripts.f2_f3_nautilus_utils import (
    INPUT_FILENAMES,
    a100_preflight,
    arm_order,
    atomic_write_json,
    validate_activation,
)
from scripts.f2_f3_training_utils import validate_private_records


EXPECTED_STACK = {
    "torch": "2.6.0",
    "transformers": "4.56.2",
    "unsloth": "2026.7.3",
    "unsloth_zoo": "2026.7.3",
    "accelerate": "1.13.0",
    "peft": "0.19.1",
    "trl": "0.22.2",
    "datasets": "4.3.0",
    "bitsandbytes": "0.49.2",
    "xformers": "0.0.29.post3",
    "torchao": "0.16.0",
    "numpy": "2.0.2",
    "triton": "3.2.0",
}
REQUIRED_IMPORTS = ("unsloth", "bitsandbytes", "datasets", "trl")
FROZEN_PRECISION = "float16"
RESUME_SAVE_STEPS = 25
LEGACY_FAILED_WAVE_COMMIT = "b01e93d35bf134fc7b547b7dbc17bec185794faf"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def actual_commit(repository_root: Path | None = None) -> str:
    """Read the init container's detached checkout without requiring git."""
    root = Path.cwd() if repository_root is None else repository_root
    head_path = root / ".git" / "HEAD"
    try:
        commit = head_path.read_text(encoding="ascii").strip()
    except OSError as exc:
        raise RuntimeError(f"cannot read detached checkout HEAD: {head_path}") from exc
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise RuntimeError("checkout HEAD is not a detached lowercase 40-hex commit")
    return commit


def compiler_path() -> str:
    """Require a compiler before imports that initialize Triton."""
    for executable in ("cc", "gcc", "clang"):
        path = shutil.which(executable)
        if path:
            return path
    raise RuntimeError("Frozen Nautilus runtime requires a C compiler")


def runtime_summary(torch_module, gpu_summary: dict) -> dict:
    versions = {}
    mismatches = {}
    for package, expected in EXPECTED_STACK.items():
        try:
            observed = metadata.version(package)
        except metadata.PackageNotFoundError:
            observed = None
        versions[package] = observed
        comparable = (
            observed.split("+", 1)[0]
            if package == "torch" and isinstance(observed, str)
            else observed
        )
        if comparable != expected:
            mismatches[package] = {
                "expected": expected,
                "observed": observed,
            }
    if mismatches:
        raise RuntimeError(
            "Frozen Nautilus package stack mismatch: " + ", ".join(sorted(mismatches))
        )
    if torch_module.version.cuda != "12.4":
        raise RuntimeError("Frozen Nautilus runtime requires CUDA 12.4")
    compiler = compiler_path()
    for package in REQUIRED_IMPORTS:
        importlib.import_module(package)

    return {
        "python": platform.python_version(),
        "cuda": torch_module.version.cuda,
        "compiler": compiler,
        "packages": versions,
        "gpu": gpu_summary,
        "unsloth_compile_disabled": os.environ.get("UNSLOTH_COMPILE_DISABLE") == "1",
        "required_imports_passed": True,
        "contains_corpus_text": False,
    }


def checkpoint_identity(checkpoint: Path) -> dict:
    model = checkpoint / "adapter_model.safetensors"
    config = checkpoint / "adapter_config.json"
    if not model.is_file() or not config.is_file():
        raise RuntimeError(f"Incomplete adapter checkpoint: {checkpoint.name}")
    return {
        "checkpoint": checkpoint.name,
        "adapter_model_bytes": model.stat().st_size,
        "adapter_model_sha256": sha256_file(model),
        "adapter_config_sha256": sha256_file(config),
        "contains_corpus_text": False,
    }


def model_load_kwargs(torch_module) -> dict:
    """Force the original P100 FP16 contract when loading on BF16-capable A100s."""
    dtype = getattr(torch_module, "float16", None)
    if dtype is None:
        raise RuntimeError("PyTorch float16 dtype is unavailable")
    return {
        "model_name": MODEL_ID,
        "revision": MODEL_REVISION,
        "max_seq_length": MAX_SEQUENCE_LENGTH,
        "load_in_4bit": True,
        "dtype": dtype,
    }


def require_fp16_model(model, torch_module) -> str:
    """Fail before trainer construction if model loading ignored the FP16 request."""
    observed = getattr(getattr(model, "config", None), "torch_dtype", None)
    if observed != torch_module.float16:
        raise RuntimeError(
            "Frozen precision mismatch: model must load with torch.float16"
        )
    return FROZEN_PRECISION


def latest_resumable_checkpoint(output_dir: Path) -> Path | None:
    """Return the newest durable Trainer checkpoint, rejecting malformed candidates."""
    if not output_dir.exists():
        return None
    checkpoints = []
    for candidate in output_dir.glob("checkpoint-*"):
        match = re.fullmatch(r"checkpoint-([1-9][0-9]*)", candidate.name)
        if not match or not candidate.is_dir():
            continue
        if not (candidate / "trainer_state.json").is_file():
            raise RuntimeError(f"Incomplete trainer checkpoint: {candidate.name}")
        checkpoints.append((int(match.group(1)), candidate))
    return max(checkpoints, default=(0, None))[1]


def failure_summary(
    *,
    activation: dict,
    phase: str,
    completed_arms: list[str],
    error: BaseException,
) -> dict:
    """Create a corpus-text-free durable failure record."""
    message_digest = hashlib.sha256(
        str(error).encode("utf-8", errors="replace")
    ).hexdigest()
    return {
        "status": "failed",
        "activation": activation,
        "phase": phase,
        "completed_arms": completed_arms,
        "error_type": type(error).__name__,
        "error_message_sha256": message_digest,
        "automatic_retry": False,
        "resume_requires_fresh_authorization": True,
        "contains_corpus_text": False,
        "nahw_passage_used": False,
        "qalb_test_used": False,
    }


def validate_staging_manifest(input_root: Path) -> dict:
    path = input_root / "staging_manifest.json"
    expected = {
        "status": "complete",
        "records": {"f2": 2000, "f3": 2000, "development": 975},
        "contains_corpus_text": False,
    }
    try:
        observed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Cannot read private staging manifest") from exc
    if observed != expected:
        raise RuntimeError("Private staging manifest contract mismatch")
    return observed


def train_arm(
    *,
    arm: str,
    seed: int,
    train_path: Path,
    development_path: Path,
    output_dir: Path,
    workflow_commit: str,
    approval_reference: str,
    torch_module,
) -> dict:
    from unsloth import FastModel
    from unsloth.chat_templates import get_chat_template
    from unsloth.trainer import UnslothVisionDataCollator
    from datasets import load_dataset
    from trl import SFTConfig, SFTTrainer

    if (output_dir / "checkpoint_selection.json").exists():
        raise RuntimeError(f"Completed output must be validated before {arm} resumes")
    resume_checkpoint = latest_resumable_checkpoint(output_dir)

    model, processor = FastModel.from_pretrained(
        **model_load_kwargs(torch_module),
    )
    require_fp16_model(model, torch_module)
    processor = get_chat_template(processor, chat_template="gemma-3")
    model = FastModel.get_peft_model(
        model,
        r=16,
        lora_alpha=32,
        lora_dropout=0.0,
        bias="none",
        target_modules=list(LORA_TARGETS),
        use_gradient_checkpointing="unsloth",
        random_state=seed,
    )

    private_data = load_dataset(
        "json",
        data_files={
            "train": str(train_path),
            "validation": str(development_path),
        },
    )

    def format_row(row):
        return {"messages": row["prompt"] + row["completion"]}

    private_data = private_data.map(
        format_row, remove_columns=private_data["train"].column_names
    )
    text_tokenizer = getattr(processor, "tokenizer", processor)

    def rendered_token_count(
        messages, template_processor=processor, tokenizer=text_tokenizer
    ) -> int:
        rendered = template_processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=False
        )
        input_ids = tokenizer(
            rendered, add_special_tokens=False, return_attention_mask=False
        )["input_ids"]
        if input_ids and isinstance(input_ids[0], (list, tuple)):
            raise RuntimeError("Token-length guard received batched IDs")
        return len(input_ids)

    lengths = [
        rendered_token_count(messages) for messages in private_data["train"]["messages"]
    ]
    if not lengths or min(lengths) < 2 or max(lengths) > MAX_SEQUENCE_LENGTH:
        raise RuntimeError("Frozen sequence-length gate failed")

    args = SFTConfig(
        output_dir=str(output_dir),
        max_length=MAX_SEQUENCE_LENGTH,
        dataset_text_field="",
        dataset_kwargs={"skip_prepare_dataset": True},
        remove_unused_columns=False,
        completion_only_loss=True,
        eval_strategy="epoch",
        save_strategy="steps",
        save_steps=RESUME_SAVE_STEPS,
        save_total_limit=None,
        report_to="none",
        bf16=False,
        fp16=True,
        seed=seed,
        **TRAINING_CONFIG,
    )
    collator = UnslothVisionDataCollator(
        model,
        processor,
        max_seq_length=MAX_SEQUENCE_LENGTH,
        train_on_responses_only=True,
        instruction_part="<start_of_turn>user\n",
        response_part="<start_of_turn>model\n",
        completion_only_loss=True,
    )
    trainer = SFTTrainer(
        model=model,
        processing_class=processor,
        data_collator=collator,
        train_dataset=private_data["train"],
        eval_dataset=private_data["validation"],
        args=args,
    )
    first_labels = collator([private_data["train"][0]])["labels"][0]
    if not torch_module.any(first_labels != -100).item():
        raise RuntimeError("Completion masking produced no assistant tokens")

    trainer.train(
        resume_from_checkpoint=(
            None if resume_checkpoint is None else str(resume_checkpoint)
        )
    )
    evaluations = [
        item
        for item in trainer.state.log_history
        if "eval_loss" in item and "epoch" in item
    ]
    if len(evaluations) != 2:
        raise RuntimeError(
            f"Expected two epoch evaluations, observed {len(evaluations)}"
        )
    first, second = evaluations
    selected = first if first["eval_loss"] <= second["eval_loss"] + 1e-6 else second
    selected_checkpoint = output_dir / f"checkpoint-{int(selected['step'])}"
    epoch_checkpoints = [
        output_dir / f"checkpoint-{int(item['step'])}" for item in evaluations
    ]
    identities = [checkpoint_identity(path) for path in epoch_checkpoints]
    summary = {
        "arm": arm,
        "seed": seed,
        "workflow_commit": workflow_commit,
        "approval_reference": approval_reference,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "training_records": len(private_data["train"]),
        "development_records": len(private_data["validation"]),
        "minimum_tokens": min(lengths),
        "maximum_tokens": max(lengths),
        "rule": (
            "lowest common-development assistant-token loss; "
            "ties within 1e-6 choose epoch 1"
        ),
        "evaluations": evaluations,
        "selected_checkpoint": selected_checkpoint.name,
        "checkpoints": identities,
        "precision": FROZEN_PRECISION,
        "resumed_from_checkpoint": (
            None if resume_checkpoint is None else resume_checkpoint.name
        ),
        "contains_corpus_text": False,
        "nahw_passage_used": False,
        "qalb_test_used": False,
    }
    atomic_write_json(output_dir / "checkpoint_selection.json", summary)

    del trainer, collator, private_data, model, processor
    gc.collect()
    torch_module.cuda.empty_cache()
    torch_module.cuda.synchronize()
    return summary


def run_fp16_trainer_smoke(*, torch_module) -> dict:
    """Load the exact model and construct the exact trainer without training or data."""
    from unsloth import FastModel
    from unsloth.chat_templates import get_chat_template
    from unsloth.trainer import UnslothVisionDataCollator
    from datasets import Dataset
    from trl import SFTConfig, SFTTrainer

    seed = 3407
    model, processor = FastModel.from_pretrained(**model_load_kwargs(torch_module))
    require_fp16_model(model, torch_module)
    processor = get_chat_template(processor, chat_template="gemma-3")
    model = FastModel.get_peft_model(
        model,
        r=16,
        lora_alpha=32,
        lora_dropout=0.0,
        bias="none",
        target_modules=list(LORA_TARGETS),
        use_gradient_checkpointing="unsloth",
        random_state=seed,
    )
    smoke_data = Dataset.from_list(
        [
            {
                "messages": [
                    {"role": "user", "content": "Input token."},
                    {"role": "assistant", "content": "Output token."},
                ]
            }
        ]
    )
    args = SFTConfig(
        output_dir="/tmp/musahhih-fp16-trainer-smoke",
        max_length=MAX_SEQUENCE_LENGTH,
        dataset_text_field="",
        dataset_kwargs={"skip_prepare_dataset": True},
        remove_unused_columns=False,
        completion_only_loss=True,
        eval_strategy="no",
        save_strategy="no",
        report_to="none",
        bf16=False,
        fp16=True,
        seed=seed,
        **TRAINING_CONFIG,
    )
    collator = UnslothVisionDataCollator(
        model,
        processor,
        max_seq_length=MAX_SEQUENCE_LENGTH,
        train_on_responses_only=True,
        instruction_part="<start_of_turn>user\n",
        response_part="<start_of_turn>model\n",
        completion_only_loss=True,
    )
    trainer = SFTTrainer(
        model=model,
        processing_class=processor,
        data_collator=collator,
        train_dataset=smoke_data,
        args=args,
    )
    labels = collator([smoke_data[0]])["labels"][0]
    if not torch_module.any(labels != -100).item():
        raise RuntimeError("FP16 trainer smoke produced no assistant tokens")
    result = {
        "status": "passed",
        "model_loaded": True,
        "model_dtype": FROZEN_PRECISION,
        "peft_constructed": True,
        "trainer_constructed": True,
        "optimizer_steps": 0,
        "datasets_mounted": 0,
        "private_records_used": 0,
        "contains_corpus_text": False,
    }
    del trainer, collator, smoke_data, model, processor
    gc.collect()
    torch_module.cuda.empty_cache()
    torch_module.cuda.synchronize()
    return result


def read_json_object(path: Path, label: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot read {label}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} must be a JSON object")
    return value


def validate_completed_arm(
    *,
    seed_root: Path,
    position: int,
    arm: str,
    seed: int,
    workflow_commit: str,
) -> dict | None:
    """Reuse only a fully hashed arm completed under the exact executable commit."""
    marker = seed_root / f"{position}0_{arm.lower()}_complete.json"
    output_dir = seed_root / arm.lower()
    selection_path = output_dir / "checkpoint_selection.json"
    if not marker.exists() and not selection_path.exists():
        return None
    selection = read_json_object(selection_path, f"{arm} checkpoint selection")
    if (
        selection.get("arm") != arm
        or selection.get("seed") != seed
        or selection.get("workflow_commit") != workflow_commit
        or selection.get("precision") != FROZEN_PRECISION
        or selection.get("contains_corpus_text") is not False
    ):
        raise RuntimeError(f"{arm} checkpoint-selection contract mismatch")
    identities = selection.get("checkpoints")
    if not isinstance(identities, list) or len(identities) != 2:
        raise RuntimeError(f"{arm} must preserve two checkpoint identities")
    for expected in identities:
        checkpoint = output_dir / str(expected.get("checkpoint"))
        if checkpoint_identity(checkpoint) != expected:
            raise RuntimeError(f"{arm} checkpoint identity mismatch")
    if marker.exists():
        observed = read_json_object(marker, f"{arm} completion marker")
        if (
            observed.get("arm") != arm
            or observed.get("seed") != seed
            or observed.get("contains_corpus_text") is not False
            or observed.get("selected_checkpoint")
            != selection.get("selected_checkpoint")
        ):
            raise RuntimeError(f"{arm} completion marker contract mismatch")
    return selection


def initialize_attempt(
    *,
    output_root: Path,
    seed: int,
    activation: dict,
    runtime: dict,
    private_inputs: dict,
) -> tuple[Path, Path]:
    """Create a write-once attempt while retaining compatible prior seed state."""
    seed_root = output_root / f"seed-{seed}"
    seed_root.mkdir(parents=True, exist_ok=True)
    original_start = seed_root / "00_started.json"
    if original_start.exists():
        observed = read_json_object(original_start, "seed start marker")
        prior_activation = observed.get("activation", {})
        if (
            prior_activation.get("seed") != seed
            or prior_activation.get("approved_commit")
            not in (activation["approved_commit"], LEGACY_FAILED_WAVE_COMMIT)
            or observed.get("private_inputs") != private_inputs
            or observed.get("contains_corpus_text") is not False
        ):
            raise RuntimeError("Existing seed output is incompatible with continuation")
    else:
        atomic_write_json(
            original_start,
            {
                "activation": activation,
                "runtime": runtime,
                "private_inputs": private_inputs,
                "contains_corpus_text": False,
            },
        )
    attempt_root = seed_root / "attempts" / activation["attempt_id"]
    attempt_root.mkdir(parents=True, exist_ok=False)
    atomic_write_json(
        attempt_root / "00_started.json",
        {
            "activation": activation,
            "runtime": runtime,
            "private_inputs": private_inputs,
            "automatic_retry": False,
            "contains_corpus_text": False,
        },
    )
    return seed_root, attempt_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage",
        required=True,
        choices=("a100-preflight", "fp16-trainer-smoke", "paired-training"),
    )
    parser.add_argument("--seed", type=int)
    parser.add_argument("--approved-commit", required=True)
    parser.add_argument("--approval-reference", required=True)
    parser.add_argument("--confirmation", required=True)
    parser.add_argument("--input-root", type=Path)
    parser.add_argument("--output-root", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    commit = actual_commit()
    activation = validate_activation(
        stage=args.stage,
        seed=args.seed,
        approved_commit=args.approved_commit,
        actual_commit=commit,
        approval_reference=args.approval_reference,
        confirmation=args.confirmation,
    )

    os.environ["UNSLOTH_COMPILE_DISABLE"] = "1"
    import torch

    gpu = a100_preflight(torch)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    runtime = runtime_summary(torch, gpu)
    runtime["precision"] = {
        "training": "fp16",
        "model_load_dtype": FROZEN_PRECISION,
        "bf16": False,
        "tf32_matmul": False,
        "tf32_cudnn": False,
    }
    if args.stage == "a100-preflight":
        print(json.dumps({"activation": activation, "runtime": runtime}, indent=2))
        return
    if args.stage == "fp16-trainer-smoke":
        smoke = run_fp16_trainer_smoke(torch_module=torch)
        print(
            json.dumps(
                {"activation": activation, "runtime": runtime, "smoke": smoke},
                indent=2,
            )
        )
        return

    if args.input_root is None or args.output_root is None:
        raise RuntimeError("Paired training requires private input/output roots")
    seed = args.seed
    assert seed is not None
    validate_staging_manifest(args.input_root)
    input_paths = {name: args.input_root / name for name in INPUT_FILENAMES}
    if any(not path.is_file() for path in input_paths.values()):
        raise RuntimeError("Expected private input files are missing")

    private_inputs = {
        "F2-P1": validate_private_records(
            input_paths["f2_train_records.jsonl"], "F2-P1"
        ),
        "F3-P1": validate_private_records(
            input_paths["f3_train_records.jsonl"], "F3-P1"
        ),
        "development": validate_private_records(
            input_paths["common_dev_records.jsonl"], "development"
        ),
    }
    seed_root, attempt_root = initialize_attempt(
        output_root=args.output_root,
        seed=seed,
        activation=activation,
        runtime=runtime,
        private_inputs=private_inputs,
    )

    phase = "attempt_initialized"
    completed: list[str] = []
    try:
        if (seed_root / "99_pair_complete.json").exists():
            raise RuntimeError("Seed pair is already complete; refusing duplicate training")
        for position, arm in enumerate(arm_order(seed), 1):
            phase = f"{arm}:validate_existing"
            summary = validate_completed_arm(
                seed_root=seed_root,
                position=position,
                arm=arm,
                seed=seed,
                workflow_commit=commit,
            )
            if summary is None:
                training_path = input_paths[
                    (
                        "f2_train_records.jsonl"
                        if arm == "F2-P1"
                        else "f3_train_records.jsonl"
                    )
                ]
                phase = f"{arm}:trainer"
                summary = train_arm(
                    arm=arm,
                    seed=seed,
                    train_path=training_path,
                    development_path=input_paths["common_dev_records.jsonl"],
                    output_dir=seed_root / arm.lower(),
                    workflow_commit=commit,
                    approval_reference=args.approval_reference,
                    torch_module=torch,
                )
            completed.append(arm)
            marker = seed_root / f"{position}0_{arm.lower()}_complete.json"
            if not marker.exists():
                atomic_write_json(
                    marker,
                    {
                        "arm": arm,
                        "seed": seed,
                        "selected_checkpoint": summary["selected_checkpoint"],
                        "completed_arms": completed,
                        "contains_corpus_text": False,
                    },
                )
            phase = f"{arm}:complete"

        atomic_write_json(
            seed_root / "99_pair_complete.json",
            {
                "seed": seed,
                "arm_order": list(arm_order(seed)),
                "completed_arms": completed,
                "workflow_commit": commit,
                "attempt_id": activation["attempt_id"],
                "contains_corpus_text": False,
                "nahw_passage_used": False,
                "qalb_test_used": False,
            },
        )
        atomic_write_json(
            attempt_root / "99_complete.json",
            {
                "status": "complete",
                "seed": seed,
                "completed_arms": completed,
                "automatic_retry": False,
                "contains_corpus_text": False,
            },
        )
    except BaseException as error:
        atomic_write_json(
            attempt_root / "98_failed.json",
            failure_summary(
                activation=activation,
                phase=phase,
                completed_arms=completed,
                error=error,
            ),
        )
        raise
    print(
        json.dumps(
            {
                "status": "complete",
                "seed": seed,
                "completed_arms": completed,
                "contains_corpus_text": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
