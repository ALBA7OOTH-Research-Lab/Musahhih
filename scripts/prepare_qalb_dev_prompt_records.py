#!/usr/bin/env python3
"""Prepare private QALB-2014 development records for prompt validation."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from scripts.prepare_b1_prompt_bundle import parse_m2_edits
from scripts.prepare_qalb_manifests import (
    DEFAULT_ARCHIVE,
    DEFAULT_OUTPUT_DIR,
    RELEASE,
    SplitSpec,
    decode_member,
    open_hashed_zip,
    parse_sent,
    sha256_bytes,
    validate_archive_members,
)


DEFAULT_DEV_MANIFEST = DEFAULT_OUTPUT_DIR / "qalb_dev_selection.jsonl"
DEFAULT_OUTPUT = DEFAULT_OUTPUT_DIR / "qalb14_dev_prompt_records.jsonl"
PRIVATE_OUTPUT_ROOT = DEFAULT_OUTPUT_DIR.resolve()
TARGET_SPEC = SplitSpec(2014, "L1", "dev")


class DevInputError(ValueError):
    """Raised when private QALB development input fails closed."""


def _load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    try:
        with Path(path).open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise DevInputError(
                        f"Development manifest row {line_number} is not an object"
                    )
                rows.append(value)
    except (OSError, json.JSONDecodeError) as error:
        raise DevInputError("Cannot read private development manifest") from error
    return rows


def _load_archive_split(archive_path: Path) -> tuple[list[tuple[str, str]], list[str], str]:
    sent_member = f"{TARGET_SPEC.stem}.sent"
    m2_member = f"{TARGET_SPEC.stem}.m2"
    try:
        with open_hashed_zip(Path(archive_path)) as (archive, archive_sha256):
            validate_archive_members(archive)
            sent_text = decode_member(archive.read(sent_member), sent_member)
            m2_text = decode_member(archive.read(m2_member), m2_member)
    except (OSError, KeyError) as error:
        raise DevInputError("Cannot read required QALB-2014 development members") from error
    sent_rows = parse_sent(sent_text, sent_member)
    m2_blocks = [block for block in m2_text.split("\n\n") if block.strip()]
    if len(sent_rows) != len(m2_blocks):
        raise DevInputError("QALB development .sent and .m2 record counts differ")
    for index, ((_, source), block) in enumerate(zip(sent_rows, m2_blocks), 1):
        m2_source = next(
            (line[2:] for line in block.splitlines() if line.startswith("S ")),
            None,
        )
        if m2_source != source:
            raise DevInputError(f"QALB M2 source mismatch at development line {index}")
    return sent_rows, m2_blocks, archive_sha256


def build_prompt_records(
    archive_path: Path,
    dev_manifest_path: Path,
    *,
    limit: int = 25,
) -> tuple[list[dict], dict]:
    """Build deterministic single-token correction records without normalization."""

    if limit < 0:
        raise DevInputError("limit must be zero or positive")
    manifest_rows = _load_jsonl(dev_manifest_path)
    sent_rows, m2_blocks, archive_sha256 = _load_archive_split(archive_path)
    selected_rows = [
        row
        for row in manifest_rows
        if row.get("release") == RELEASE
        and row.get("year") == TARGET_SPEC.year
        and row.get("track") == TARGET_SPEC.track
        and row.get("split") == TARGET_SPEC.split
    ]
    if not selected_rows:
        raise DevInputError("No QALB-2014 L1 development rows in manifest")

    records: list[dict] = []
    skipped = Counter()
    seen_record_keys: set[str] = set()
    for row in selected_rows:
        required = {
            "record_key",
            "line_number",
            "document_id",
            "source_sha256",
            "eligible_for_development",
            "sent_member",
            "m2_member",
        }
        if not required.issubset(row):
            raise DevInputError("Development manifest row has an invalid schema")
        record_key = row["record_key"]
        if not isinstance(record_key, str) or record_key in seen_record_keys:
            raise DevInputError("Duplicate or invalid development record_key")
        seen_record_keys.add(record_key)
        if row["eligible_for_development"] is not True:
            raise DevInputError("Development manifest contains an ineligible target row")
        line_number = row["line_number"]
        if (
            not isinstance(line_number, int)
            or isinstance(line_number, bool)
            or line_number < 1
            or line_number > len(sent_rows)
        ):
            raise DevInputError("Invalid development manifest line number")
        expected_sent = f"{TARGET_SPEC.stem}.sent"
        expected_m2 = f"{TARGET_SPEC.stem}.m2"
        if row["sent_member"] != expected_sent or row["m2_member"] != expected_m2:
            raise DevInputError("Development manifest member mismatch")
        document_id, source = sent_rows[line_number - 1]
        if document_id != row["document_id"]:
            raise DevInputError("Development manifest document ID mismatch")
        if sha256_bytes(source.encode("utf-8")) != row["source_sha256"]:
            raise DevInputError("Development manifest source hash mismatch")

        edits = parse_m2_edits(m2_blocks[line_number - 1])
        span_counts = Counter((edit.start, edit.end) for edit in edits)
        source_tokens = source.split()
        for edit in edits:
            if span_counts[(edit.start, edit.end)] != 1:
                skipped["ambiguous_span"] += 1
                continue
            correction_tokens = edit.correction.split()
            if edit.end - edit.start != 1 or len(correction_tokens) != 1:
                skipped["not_single_token_replacement"] += 1
                continue
            if edit.start < 0 or edit.end > len(source_tokens):
                raise DevInputError("M2 edit span is outside the source sentence")
            error = source_tokens[edit.start]
            correction = correction_tokens[0]
            if not correction or correction == error:
                skipped["empty_or_unchanged"] += 1
                continue
            if source_tokens.count(error) != 1:
                skipped["non_unique_error_token"] += 1
                continue
            identity = f"{record_key}|{edit.start}:{edit.end}"
            records.append(
                {
                    "record_id": identity,
                    "passage": source,
                    "error": error,
                    "gold_correction": correction,
                    "metadata": {
                        "dataset": "QALB-2014",
                        "release": RELEASE,
                        "track": "L1",
                        "split": "dev",
                        "record_key": record_key,
                        "edit_start": edit.start,
                        "edit_end": edit.end,
                        "source_sha256": row["source_sha256"],
                    },
                }
            )
            if limit and len(records) == limit:
                break
        if limit and len(records) == limit:
            break

    if not records:
        raise DevInputError("No eligible single-token development corrections found")
    identity_sha256 = hashlib.sha256(
        "\n".join(record["record_id"] for record in records).encode("utf-8")
    ).hexdigest()
    summary = {
        "schema_version": 1,
        "dataset": "QALB-2014",
        "release": RELEASE,
        "track": "L1",
        "split": "dev",
        "archive_sha256": archive_sha256,
        "manifest_sha256": hashlib.sha256(Path(dev_manifest_path).read_bytes()).hexdigest(),
        "number_of_records": len(records),
        "record_identity_sha256": identity_sha256,
        "skipped_before_limit": dict(sorted(skipped.items())),
        "limit": limit,
    }
    return records, summary


def write_private_records(
    output_path: Path,
    records: list[dict],
    *,
    allow_outside_private_root: bool = False,
) -> str:
    output_path = Path(output_path)
    if not allow_outside_private_root:
        try:
            output_path.resolve().relative_to(PRIVATE_OUTPUT_ROOT)
        except ValueError as error:
            raise DevInputError(
                "Private QALB output must stay under data/processed/qalb/"
            ) from error
    if output_path.exists():
        raise DevInputError(f"Private output already exists: {output_path.name}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records
    )
    output_path.write_text(payload, encoding="utf-8", newline="\n")
    return hashlib.sha256(output_path.read_bytes()).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--dev-manifest", type=Path, default=DEFAULT_DEV_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument(
        "--write-private-output",
        action="store_true",
        help="Deliberately write text-bearing records under the ignored private path.",
    )
    parser.add_argument(
        "--allow-outside-private-output",
        action="store_true",
        help="Only for synthetic tests; never use for licensed corpus output.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records, summary = build_prompt_records(
        args.archive, args.dev_manifest, limit=args.limit
    )
    if args.write_private_output:
        summary["output_sha256"] = write_private_records(
            args.output,
            records,
            allow_outside_private_root=args.allow_outside_private_output,
        )
        summary["output_written"] = True
    else:
        summary["output_written"] = False
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
