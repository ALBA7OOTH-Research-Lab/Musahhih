#!/usr/bin/env python3
"""LoRA SFT template for a text-only causal LM.

Expected JSONL fields:
- prompt: conversational user-message list
- completion: conversational assistant-message list

Keep the same base model across all data ablations.
"""

from pathlib import Path
import argparse

from datasets import load_dataset
from peft import LoraConfig, TaskType
from trl import SFTConfig, SFTTrainer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen3-4B")
    parser.add_argument("--train-file", type=Path, required=True)
    parser.add_argument("--eval-file", type=Path, default=None)
    parser.add_argument("--output-dir", default="outputs/qwen3-4b-arabic-gec-lora")
    parser.add_argument("--epochs", type=float, default=2.0)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation", type=int, default=16)
    parser.add_argument("--max-length", type=int, default=1024)
    args = parser.parse_args()

    files = {"train": str(args.train_file)}
    if args.eval_file:
        files["validation"] = str(args.eval_file)

    dataset = load_dataset("json", data_files=files)

    peft_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        target_modules="all-linear",
    )

    config = SFTConfig(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        learning_rate=args.learning_rate,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation,
        max_length=args.max_length,
        logging_steps=10,
        save_strategy="epoch",
        eval_strategy="epoch" if args.eval_file else "no",
        bf16=True,
        gradient_checkpointing=True,
        report_to="none",
    )

    trainer = SFTTrainer(
        model=args.model,
        args=config,
        train_dataset=dataset["train"],
        eval_dataset=dataset.get("validation"),
        peft_config=peft_config,
    )
    trainer.train()
    trainer.save_model(args.output_dir)


if __name__ == "__main__":
    main()
