#!/usr/bin/env python3
"""Validate the frozen Tibyan selection with the exact Gemma chat tokenizer."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics

from scripts.prepare_nahw_eval import PROMPT
from scripts.prepare_tibyan_f2_f3 import TibyanManifestError, file_sha256


ROOT = Path(__file__).resolve().parents[1]
MODEL_ID = "unsloth/gemma-3-4b-it-unsloth-bnb-4bit"
MODEL_REVISION = "316726ca0bd24aa323bfaf86e8a379ee1176d1fe"
EXPECTED_SELECTION_SHA256 = (
    "395d0554d8836c08727144ec44e1011cceeb19b6c7f90973655882047c6bdb0a"
)
EXPECTED_RECORDS = 2000
MAX_SEQUENCE_LENGTH = 1024


def load_private_selection(path: Path) -> list[dict]:
    if file_sha256(path) != EXPECTED_SELECTION_SHA256:
        raise TibyanManifestError("Tibyan training selection checksum mismatch")
    rows = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            try:
                row = json.loads(line)
                required = {
                    "record_id",
                    "passage",
                    "erroneous_word",
                    "gold_correction",
                }
                if not required.issubset(row) or any(
                    not isinstance(row[field], str) or not row[field]
                    for field in required
                ):
                    raise ValueError
            except (json.JSONDecodeError, TypeError, ValueError) as error:
                raise TibyanManifestError(
                    f"Invalid private selection row {line_number}"
                ) from error
            rows.append(row)
    if len(rows) != EXPECTED_RECORDS:
        raise TibyanManifestError("Tibyan training selection count mismatch")
    return rows


def measure_lengths(rows: list[dict], tokenizer, transformers_version: str) -> dict:
    measured = []
    for row in rows:
        messages = [
            {
                "role": "user",
                "content": PROMPT.format(
                    passage=row["passage"], error=row["erroneous_word"]
                ),
            },
            {"role": "assistant", "content": row["gold_correction"]},
        ]
        rendered = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=False
        )
        input_ids = tokenizer(
            rendered, add_special_tokens=False, return_attention_mask=False
        )["input_ids"]
        if input_ids and isinstance(input_ids[0], (list, tuple)):
            raise TibyanManifestError("Tokenizer returned batched input IDs")
        measured.append((row["record_id"], len(input_ids)))
    if not measured or min(length for _, length in measured) < 2:
        raise TibyanManifestError("Implausible formatted token length")
    lengths = sorted(length for _, length in measured)
    longest_record_id, maximum = max(measured, key=lambda item: item[1])
    length_payload = "".join(
        json.dumps(
            {"formatted_tokens": length, "record_id": record_id},
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
        for record_id, length in measured
    ).encode()
    return {
        "model_id": MODEL_ID,
        "requested_revision": MODEL_REVISION,
        "transformers": transformers_version,
        "tokenizer_class": type(tokenizer).__name__,
        "tokenizer_size": len(tokenizer),
        "records": len(measured),
        "minimum": lengths[0],
        "median": statistics.median(lengths),
        "p95": lengths[int(0.95 * (len(lengths) - 1))],
        "maximum": maximum,
        "over_1024": sum(length > MAX_SEQUENCE_LENGTH for length in lengths),
        "longest_record_id": longest_record_id,
        "length_manifest_sha256": hashlib.sha256(length_payload).hexdigest(),
        "contains_corpus_text": False,
        "model_weights_loaded": False,
        "training_or_inference_executed": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--selection",
        type=Path,
        default=ROOT
        / "data/processed/tibyan_f2_f3/tibyan_train_selection.jsonl",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data/processed/tibyan_f2_f3/tibyan_length_summary.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        from transformers import AutoTokenizer, __version__
    except ImportError as error:
        raise TibyanManifestError(
            "Install transformers==4.56.2, sentencepiece, and jinja2"
        ) from error
    if __version__ != "4.56.2":
        raise TibyanManifestError("Transformers version must be exactly 4.56.2")
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID, revision=MODEL_REVISION
    )
    summary = measure_lengths(load_private_selection(args.selection), tokenizer, __version__)
    if summary["over_1024"]:
        raise TibyanManifestError("Frozen 1,024-token limit exceeded")
    payload = json.dumps(summary, indent=2, sort_keys=True).encode() + b"\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists() and args.output.read_bytes() != payload:
        raise TibyanManifestError("Existing token-length summary differs")
    if not args.output.exists():
        temporary = args.output.with_name(f".{args.output.name}.tmp")
        if temporary.exists():
            raise TibyanManifestError("Stale token-length temporary output")
        temporary.write_bytes(payload)
        os.replace(temporary, args.output)
    print(json.dumps(summary, sort_keys=True))
    print("No corpus text was printed; no model weights or inference were used.")


if __name__ == "__main__":
    main()
