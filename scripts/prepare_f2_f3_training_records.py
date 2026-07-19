#!/usr/bin/env python3
"""Assemble frozen private F2/F3 conversations without printing corpus text."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Iterable

try:
    from scripts.prepare_f1_natural_records import PROMPT
except ModuleNotFoundError:  # Support direct `python scripts/...py` execution.
    from prepare_f1_natural_records import PROMPT


ROOT = Path(__file__).resolve().parents[1]
SEED = 3407
F2_RECORDS = 2000
F3_HALF_RECORDS = 1000
EXPECTED_TIBYAN_SELECTION_SHA256 = (
    "395d0554d8836c08727144ec44e1011cceeb19b6c7f90973655882047c6bdb0a"
)
EXPECTED_TIBYAN_RECORD_IDS_SHA256 = (
    "f56b749b19b1fbf0427a9f8af14011a19c6107fc82ef39a8e16399f45d3018be"
)
EXPECTED_TIBYAN_PREFIX_IDS_SHA256 = (
    "1e5ad4dca40667197461ac589df25fd1c239f04bb4d093661235b41b8d03ae8f"
)
EXPECTED_F1_TRAIN_SHA256 = (
    "8e937bcae9b7870c37c0cf79c0a5870c67bdd4c72b7b851240c7ccada2512d6a"
)
EXPECTED_F1_DEV_SHA256 = (
    "adfdeb0c2e5730357226ce4e5156c300679629142ea0576d32dea9ac3050a950"
)
EXPECTED_F1_SELECTION_SHA256 = (
    "03588f135e82575f8de9030b948d6b59cd14e3ca9c218207b0f33885d1f8e2d1"
)
EXPECTED_F1_PREFIX_IDS_SHA256 = (
    "7a21b02232163752188d7a9cd0f8e9c11f4e3bbbd26d3d3cd6f70df0d7ba7fd2"
)
OUTPUT_NAMES = (
    "f2_train_records.jsonl",
    "f3_train_records.jsonl",
    "common_dev_records.jsonl",
    "f2_f3_training_records_summary.json",
)


class F2F3AdapterError(ValueError):
    """Raised when a frozen composition, privacy, or integrity gate fails."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    try:
        with path.open(encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise F2F3AdapterError(
                        f"Invalid private JSONL row {path.name}:{line_number}"
                    )
                rows.append(row)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise F2F3AdapterError(f"Cannot read private JSONL: {path.name}") from error
    return rows


def record_id_digest(rows: Iterable[dict]) -> str:
    return sha256_bytes(
        (
            "\n".join(row["record_id"] for row in rows)
            + "\n"
        ).encode("utf-8")
    )


def validate_conversation(row: dict, split: str, sources: set[str]) -> None:
    required = {"record_id", "prompt", "completion", "source", "split"}
    if set(row) != required:
        raise F2F3AdapterError("Private conversation schema mismatch")
    if (
        not isinstance(row["record_id"], str)
        or not row["record_id"]
        or row["split"] != split
        or row["source"] not in sources
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
        raise F2F3AdapterError("Private conversation role mismatch")


def tibyan_conversation(row: dict) -> dict:
    required = {
        "record_id",
        "source_dataset",
        "source_release",
        "source_line_number",
        "passage",
        "erroneous_word",
        "gold_correction",
        "project_split",
        "is_group_representative",
        "selection_rank",
        "exact_overlap_qalb_test",
        "exact_overlap_qalb_train_development",
        "exact_overlap_nahw",
    }
    if not required.issubset(row):
        raise F2F3AdapterError("Tibyan selection schema mismatch")
    if (
        row["source_dataset"] != "Tibyan-corpus"
        or row["source_release"] != "Zenodo-14623621"
        or row["project_split"] != "train"
        or row["is_group_representative"] is not True
        or any(
            row[field] is not False
            for field in (
                "exact_overlap_qalb_test",
                "exact_overlap_qalb_train_development",
                "exact_overlap_nahw",
            )
        )
        or not all(
            isinstance(row[field], str) and row[field]
            for field in ("record_id", "passage", "erroneous_word", "gold_correction")
        )
    ):
        raise F2F3AdapterError("Tibyan selection role or privacy gate mismatch")
    return {
        "record_id": row["record_id"],
        "prompt": [
            {
                "role": "user",
                "content": PROMPT.format(
                    passage=row["passage"], error=row["erroneous_word"]
                ),
            }
        ],
        "completion": [
            {"role": "assistant", "content": row["gold_correction"]}
        ],
        "source": "Tibyan-corpus",
        "split": "train",
    }


def mixture_order(row: dict) -> str:
    return sha256_text(
        f"F3-P1-order|{SEED}|{row['source']}|{row['record_id']}"
    )


def render_jsonl(rows: Iterable[dict]) -> bytes:
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows
    ).encode("utf-8")


def build_records(
    tibyan_rows: list[dict],
    f1_train_rows: list[dict],
    f1_dev_rows: list[dict],
) -> tuple[dict[str, bytes], dict]:
    if len(tibyan_rows) != F2_RECORDS:
        raise F2F3AdapterError("F2 Tibyan selection count mismatch")
    if [row.get("selection_rank") for row in tibyan_rows] != list(
        range(1, F2_RECORDS + 1)
    ):
        raise F2F3AdapterError("F2 Tibyan selection ranks are not canonical")
    if len(f1_train_rows) != F2_RECORDS:
        raise F2F3AdapterError("F1 natural selection count mismatch")
    if not f1_dev_rows:
        raise F2F3AdapterError("Common development view is empty")

    f2_train = [tibyan_conversation(row) for row in tibyan_rows]
    for row in f1_train_rows:
        validate_conversation(row, "train", {"QALB-2014-L1"})
    for row in f1_dev_rows:
        validate_conversation(row, "development", {"QALB-2014-L1"})

    if record_id_digest(tibyan_rows) != EXPECTED_TIBYAN_RECORD_IDS_SHA256:
        raise F2F3AdapterError("F2 Tibyan record-ID digest mismatch")
    if (
        record_id_digest(tibyan_rows[:F3_HALF_RECORDS])
        != EXPECTED_TIBYAN_PREFIX_IDS_SHA256
    ):
        raise F2F3AdapterError("F3 synthetic prefix digest mismatch")
    if (
        record_id_digest(f1_train_rows[:F3_HALF_RECORDS])
        != EXPECTED_F1_PREFIX_IDS_SHA256
    ):
        raise F2F3AdapterError("F3 natural prefix digest mismatch")

    f3_train = [
        *f1_train_rows[:F3_HALF_RECORDS],
        *f2_train[:F3_HALF_RECORDS],
    ]
    f3_train.sort(key=mixture_order)
    if len({row["record_id"] for row in f2_train}) != F2_RECORDS:
        raise F2F3AdapterError("Duplicate F2 record ID")
    if len({(row["source"], row["record_id"]) for row in f3_train}) != F2_RECORDS:
        raise F2F3AdapterError("Duplicate F3 source/record identity")
    for row in f2_train:
        validate_conversation(row, "train", {"Tibyan-corpus"})
    for row in f3_train:
        validate_conversation(row, "train", {"Tibyan-corpus", "QALB-2014-L1"})

    f2_payload = render_jsonl(f2_train)
    f3_payload = render_jsonl(f3_train)
    development_payload = render_jsonl(f1_dev_rows)
    payloads = {
        OUTPUT_NAMES[0]: f2_payload,
        OUTPUT_NAMES[1]: f3_payload,
        OUTPUT_NAMES[2]: development_payload,
    }
    summary = {
        "schema_version": 1,
        "protocol_commit": "8ca3014e6b3659e2e8c3ffc519b0255e9af6b7a6",
        "approval_reference": (
            "https://github.com/ALBA7OOTH-Research-Lab/Musahhih/"
            "issues/67#issuecomment-5016107399"
        ),
        "seed": SEED,
        "prompt_template_sha256": sha256_text(PROMPT),
        "f2": {
            "records": len(f2_train),
            "tibyan_records": len(f2_train),
            "record_id_sha256": record_id_digest(f2_train),
        },
        "f3": {
            "records": len(f3_train),
            "natural_records": sum(
                row["source"] == "QALB-2014-L1" for row in f3_train
            ),
            "synthetic_records": sum(
                row["source"] == "Tibyan-corpus" for row in f3_train
            ),
            "ordered_source_record_id_sha256": sha256_bytes(
                (
                    "\n".join(
                        f"{row['source']}|{row['record_id']}" for row in f3_train
                    )
                    + "\n"
                ).encode("utf-8")
            ),
            "natural_prefix_record_id_sha256": record_id_digest(
                f1_train_rows[:F3_HALF_RECORDS]
            ),
            "synthetic_prefix_record_id_sha256": record_id_digest(
                f2_train[:F3_HALF_RECORDS]
            ),
        },
        "common_development": {
            "records": len(f1_dev_rows),
            "source": "QALB-2014-L1",
            "record_id_sha256": record_id_digest(f1_dev_rows),
        },
        "private_output_sha256": {
            name: sha256_bytes(payload) for name, payload in payloads.items()
        },
        "contains_corpus_text": False,
        "nahw_passage_used": False,
        "qalb_test_used": False,
        "training_executed": False,
        "inference_executed": False,
    }
    payloads[OUTPUT_NAMES[3]] = (
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True).encode(
            "utf-8"
        )
        + b"\n"
    )
    return payloads, summary


def safe_private_output(path: Path) -> Path:
    resolved = path.resolve()
    private_root = (ROOT / "data/processed").resolve()
    if resolved != private_root and private_root not in resolved.parents:
        raise F2F3AdapterError(
            "Private output directory must stay under data/processed"
        )
    return resolved


def write_idempotent(output_dir: Path, payloads: dict[str, bytes]) -> None:
    output_dir = safe_private_output(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stale = sorted(path.name for path in output_dir.glob(".*.tmp"))
    if stale:
        raise F2F3AdapterError(
            "Stale temporary output(s): " + ", ".join(stale)
        )
    for name, payload in payloads.items():
        destination = output_dir / name
        if destination.exists():
            if destination.read_bytes() != payload:
                raise F2F3AdapterError(
                    f"Existing private output differs: {name}"
                )
            continue
        temporary = output_dir / f".{name}.tmp"
        temporary.write_bytes(payload)
        os.replace(temporary, destination)


def validate_input_hashes(
    tibyan_path: Path, f1_train_path: Path, f1_dev_path: Path
) -> None:
    expected = {
        tibyan_path: EXPECTED_TIBYAN_SELECTION_SHA256,
        f1_train_path: EXPECTED_F1_TRAIN_SHA256,
        f1_dev_path: EXPECTED_F1_DEV_SHA256,
    }
    for path, digest in expected.items():
        if file_sha256(path) != digest:
            raise F2F3AdapterError(f"Frozen private input hash mismatch: {path.name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tibyan-selection",
        type=Path,
        default=ROOT
        / "data/processed/tibyan_f2_f3/tibyan_train_selection.jsonl",
    )
    parser.add_argument(
        "--f1-train",
        type=Path,
        default=ROOT / "data/processed/f1_natural_records/train_records.jsonl",
    )
    parser.add_argument(
        "--f1-dev",
        type=Path,
        default=ROOT / "data/processed/f1_natural_records/dev_records.jsonl",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "data/processed/f2_f3_training_records",
    )
    parser.add_argument("--write-private-records", action="store_true")
    parser.add_argument("--confirm-private-data-authorization", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    validate_input_hashes(args.tibyan_selection, args.f1_train, args.f1_dev)
    payloads, summary = build_records(
        load_jsonl(args.tibyan_selection),
        load_jsonl(args.f1_train),
        load_jsonl(args.f1_dev),
    )
    if args.write_private_records:
        if not args.confirm_private_data_authorization:
            raise F2F3AdapterError(
                "Writing private outputs requires "
                "--confirm-private-data-authorization"
            )
        write_idempotent(args.output_dir, payloads)
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(
        "No corpus text was printed. No training or inference occurred; "
        "QALB test and Nahw-Passage remain evaluation-only."
    )


if __name__ == "__main__":
    main()
