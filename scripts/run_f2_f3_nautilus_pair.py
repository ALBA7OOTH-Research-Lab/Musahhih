#!/usr/bin/env python3
"""Run one fail-closed A100 preflight or one paired F2/F3 seed training job."""

from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.metadata as metadata
import json
import os
import platform
import subprocess
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def actual_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


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
    import bitsandbytes  # noqa: F401
    import datasets  # noqa: F401
    import trl  # noqa: F401
    import unsloth  # noqa: F401

    return {
        "python": platform.python_version(),
        "cuda": torch_module.version.cuda,
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
    from datasets import load_dataset
    from trl import SFTConfig, SFTTrainer
    from unsloth import FastModel
    from unsloth.chat_templates import get_chat_template
    from unsloth.trainer import UnslothVisionDataCollator

    if output_dir.exists():
        raise RuntimeError(f"Output already exists for {arm} seed {seed}")

    model, processor = FastModel.from_pretrained(
        model_name=MODEL_ID,
        revision=MODEL_REVISION,
        max_seq_length=MAX_SEQUENCE_LENGTH,
        load_in_4bit=True,
    )
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
        save_strategy="epoch",
        save_total_limit=2,
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

    trainer.train()
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage", required=True, choices=("a100-preflight", "paired-training")
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
        "bf16": False,
        "tf32_matmul": False,
        "tf32_cudnn": False,
    }
    if args.stage == "a100-preflight":
        print(json.dumps({"activation": activation, "runtime": runtime}, indent=2))
        return

    if args.input_root is None or args.output_root is None:
        raise RuntimeError("Paired training requires private input/output roots")
    seed = args.seed
    assert seed is not None
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
    seed_root = args.output_root / f"seed-{seed}"
    seed_root.mkdir(parents=True, exist_ok=False)
    atomic_write_json(
        seed_root / "00_started.json",
        {
            "activation": activation,
            "runtime": runtime,
            "private_inputs": private_inputs,
            "contains_corpus_text": False,
        },
    )

    completed = []
    for position, arm in enumerate(arm_order(seed), 1):
        training_path = input_paths[
            "f2_train_records.jsonl" if arm == "F2-P1" else "f3_train_records.jsonl"
        ]
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
        atomic_write_json(
            seed_root / f"{position}0_{arm.lower()}_complete.json",
            {
                "arm": arm,
                "seed": seed,
                "selected_checkpoint": summary["selected_checkpoint"],
                "completed_arms": completed,
                "contains_corpus_text": False,
            },
        )

    atomic_write_json(
        seed_root / "99_pair_complete.json",
        {
            "seed": seed,
            "arm_order": list(arm_order(seed)),
            "completed_arms": completed,
            "workflow_commit": commit,
            "contains_corpus_text": False,
            "nahw_passage_used": False,
            "qalb_test_used": False,
        },
    )
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
