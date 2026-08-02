#!/usr/bin/env python3
"""Summarize frozen training token budgets without printing corpus text."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[1]
MODEL_ID = "unsloth/gemma-3-4b-it-unsloth-bnb-4bit"
MODEL_REVISION = "316726ca0bd24aa323bfaf86e8a379ee1176d1fe"
TRANSFORMERS_VERSION = "4.56.2"
EXPECTED_RECORDS = 2000
MAX_SEQUENCE_LENGTH = 1024
ARM_INPUTS = {
    "F1-P1": (
        ROOT / "data/processed/f1_natural_records/train_records.jsonl",
        "8e937bcae9b7870c37c0cf79c0a5870c67bdd4c72b7b851240c7ccada2512d6a",
        {"QALB-2014-L1": 2000},
    ),
    "F2-P1": (
        ROOT / "data/processed/f2_f3_training_records/f2_train_records.jsonl",
        "bbc48dcf78ddff1830661ad749fcc8f9fbfce8206f4f09cd9f4d6501823201d2",
        {"Tibyan-corpus": 2000},
    ),
    "F3-P1": (
        ROOT / "data/processed/f2_f3_training_records/f3_train_records.jsonl",
        "d16decebe559e9a25da41ef59f63ca95e339972e22b9659dfc763e071fbc1546",
        {"QALB-2014-L1": 1000, "Tibyan-corpus": 1000},
    ),
}


class TokenBudgetError(ValueError):
    """Raised when a frozen-input or corpus-privacy gate fails."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_arm(
    path: Path, expected_sha256: str, expected_sources: dict[str, int]
) -> list[dict]:
    if sha256_file(path) != expected_sha256:
        raise TokenBudgetError(f"Frozen input checksum mismatch: {path.name}")
    rows = []
    sources = {source: 0 for source in expected_sources}
    seen = set()
    try:
        with path.open(encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                row = json.loads(line)
                if set(row) != {
                    "record_id",
                    "prompt",
                    "completion",
                    "source",
                    "split",
                }:
                    raise TokenBudgetError(
                        f"Private schema mismatch at row {line_number}"
                    )
                if (
                    row["split"] != "train"
                    or row["source"] not in expected_sources
                    or not isinstance(row["record_id"], str)
                    or not row["record_id"]
                    or row["record_id"] in seen
                    or not isinstance(row["prompt"], list)
                    or len(row["prompt"]) != 1
                    or row["prompt"][0].get("role") != "user"
                    or not isinstance(row["prompt"][0].get("content"), str)
                    or not row["prompt"][0]["content"]
                    or not isinstance(row["completion"], list)
                    or len(row["completion"]) != 1
                    or row["completion"][0].get("role") != "assistant"
                    or not isinstance(row["completion"][0].get("content"), str)
                    or not row["completion"][0]["content"]
                ):
                    raise TokenBudgetError(
                        f"Private role mismatch at row {line_number}"
                    )
                seen.add(row["record_id"])
                sources[row["source"]] += 1
                rows.append(row)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise TokenBudgetError(f"Cannot read private input: {path.name}") from error
    if len(rows) != EXPECTED_RECORDS or sources != expected_sources:
        raise TokenBudgetError(f"Frozen composition mismatch: {path.name}")
    return rows


def percentile_nearest_rank(sorted_values: list[int], fraction: float) -> int:
    if not sorted_values or not 0 <= fraction <= 1:
        raise TokenBudgetError("Invalid percentile input")
    return sorted_values[int(fraction * (len(sorted_values) - 1))]


def summarize_arm(rows: list[dict], tokenizer) -> dict:
    measured = []
    source_totals: dict[str, dict[str, int]] = {}
    for row in rows:
        messages = row["prompt"] + row["completion"]
        rendered = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=False
        )
        input_ids = tokenizer(
            rendered, add_special_tokens=False, return_attention_mask=False
        )["input_ids"]
        if input_ids and isinstance(input_ids[0], (list, tuple)):
            raise TokenBudgetError("Tokenizer returned batched input IDs")
        length = len(input_ids)
        if length < 2 or length > MAX_SEQUENCE_LENGTH:
            raise TokenBudgetError("Frozen record violates formatted-length gate")
        measured.append((row["record_id"], row["source"], length))
        source = source_totals.setdefault(
            row["source"], {"records": 0, "formatted_tokens": 0}
        )
        source["records"] += 1
        source["formatted_tokens"] += length

    lengths = sorted(length for _, _, length in measured)
    manifest = "".join(
        json.dumps(
            {
                "formatted_tokens": length,
                "record_id": record_id,
                "source": source,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
        for record_id, source, length in measured
    ).encode()
    return {
        "records": len(measured),
        "formatted_tokens": sum(lengths),
        "mean": sum(lengths) / len(lengths),
        "median": statistics.median(lengths),
        "p95": percentile_nearest_rank(lengths, 0.95),
        "minimum": lengths[0],
        "maximum": lengths[-1],
        "over_1024": sum(length > MAX_SEQUENCE_LENGTH for length in lengths),
        "source_totals": dict(sorted(source_totals.items())),
        "length_manifest_sha256": hashlib.sha256(manifest).hexdigest(),
    }


def build_summary(tokenizer, transformers_version: str) -> dict:
    if transformers_version != TRANSFORMERS_VERSION:
        raise TokenBudgetError(
            f"Transformers must be exactly {TRANSFORMERS_VERSION}"
        )
    arms = {}
    for arm, (path, expected_sha256, expected_sources) in ARM_INPUTS.items():
        arms[arm] = summarize_arm(
            load_arm(path, expected_sha256, expected_sources), tokenizer
        )
        arms[arm]["input_sha256"] = expected_sha256
    return {
        "schema_version": 1,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "transformers": transformers_version,
        "tokenizer_class": type(tokenizer).__name__,
        "tokenizer_size": len(tokenizer),
        "arms": arms,
        "contains_corpus_text": False,
        "model_weights_loaded": False,
        "training_or_inference_executed": False,
    }


def write_idempotent(path: Path, summary: dict) -> None:
    payload = json.dumps(summary, indent=2, sort_keys=True).encode() + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise TokenBudgetError("Existing aggregate summary differs")
        return
    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists():
        raise TokenBudgetError("Stale aggregate-summary temporary file")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/training_token_budget_summary.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        from transformers import AutoTokenizer, __version__
    except ImportError as error:
        raise TokenBudgetError(
            "Install transformers==4.56.2, sentencepiece, and jinja2"
        ) from error
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID, revision=MODEL_REVISION, local_files_only=True
    )
    summary = build_summary(tokenizer, __version__)
    write_idempotent(args.output, summary)
    print(json.dumps(summary, sort_keys=True))
    print(
        "No corpus text was printed; no model weights, training, inference, "
        "predictions, or test records were used."
    )


if __name__ == "__main__":
    main()
