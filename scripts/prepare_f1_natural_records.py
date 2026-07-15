#!/usr/bin/env python3
"""Prepare private F1-P1 single-token QALB records without logging corpus text."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

try:
    from scripts.prepare_qalb_manifests import DEFAULT_ARCHIVE, ROOT, sha256_bytes
except ModuleNotFoundError:  # Support `python scripts/prepare_f1_natural_records.py`.
    from prepare_qalb_manifests import DEFAULT_ARCHIVE, ROOT, sha256_bytes


PROTOCOL_ID = "F1-P1"
SEED = 3407
DEFAULT_TRAIN_MANIFEST = ROOT / "data/processed/qalb/qalb_train_selection.jsonl"
DEFAULT_DEV_MANIFEST = ROOT / "data/processed/qalb/qalb_dev_selection.jsonl"
DEFAULT_MANIFEST_SUMMARY = ROOT / "data/processed/qalb/qalb_manifest_summary.json"
DEFAULT_OUTPUT_DIR = ROOT / "data/processed/qalb/f1_p1"
PROMPT = """صحح الكلمة الخاطئة المحددة في النص التالي.
أعد الكلمة المصححة فقط دون شرح أو علامات اقتباس.

النص:
{passage}

الكلمة الخاطئة:
{error}
"""


class AdapterError(ValueError):
    """Raised when a privacy, integrity, or protocol safeguard fails."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AdapterError(f"Cannot read JSON metadata: {path.name}") from error
    if not isinstance(value, dict):
        raise AdapterError(f"JSON metadata must be an object: {path.name}")
    return value


def load_manifest(path: Path, expected_split: str) -> list[dict]:
    rows = []
    try:
        with path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise AdapterError(f"Invalid manifest row: {path.name}:{line_number}")
                rows.append(row)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AdapterError(f"Cannot read manifest: {path.name}") from error

    required = {
        "record_key", "year", "track", "split", "line_number", "sent_member",
        "m2_member", "source_sha256", "correction_sha256",
        "duplicate_source_within_split", "exact_source_overlap_with_qalb_test",
        "exact_source_overlap_with_nahw", f"eligible_for_{'training' if expected_split == 'train' else 'development'}",
    }
    seen = set()
    for row in rows:
        if not required.issubset(row):
            raise AdapterError(f"Manifest schema mismatch: {path.name}")
        if row["split"] != expected_split:
            raise AdapterError(f"Unexpected split in {path.name}")
        if row["record_key"] in seen:
            raise AdapterError(f"Duplicate record key in {path.name}")
        seen.add(row["record_key"])
    return rows


def decode_member(archive: zipfile.ZipFile, member: str) -> str:
    try:
        return archive.read(member).decode("utf-8-sig")
    except (KeyError, UnicodeDecodeError) as error:
        raise AdapterError(f"Cannot decode required archive member: {member}") from error


def parse_sent(text: str, member: str) -> list[str]:
    sources = []
    for number, line in enumerate(text.splitlines(), 1):
        if " " not in line:
            raise AdapterError(f"Malformed sentence member at row {number}: {member}")
        _, source = line.split(" ", 1)
        if not source:
            raise AdapterError(f"Empty sentence at row {number}: {member}")
        sources.append(source)
    return sources


def parse_m2_blocks(text: str, member: str) -> list[tuple[str, list[str]]]:
    blocks = []
    for block_number, block in enumerate(text.strip().split("\n\n"), 1):
        lines = block.splitlines()
        if not lines or not lines[0].startswith("S "):
            raise AdapterError(f"Malformed M2 block {block_number}: {member}")
        blocks.append((lines[0][2:], [line for line in lines[1:] if line.startswith("A ")]))
    return blocks


def eligible_actions(source: str, actions: list[str], record_key: str) -> list[dict]:
    tokens = source.split()
    candidates = []
    for action in actions:
        fields = action[2:].split("|||")
        if len(fields) < 6:
            continue
        try:
            start, end = (int(value) for value in fields[0].split())
        except (ValueError, TypeError):
            continue
        correction = fields[2]
        annotator = fields[-1].strip()
        if annotator != "0" or end - start != 1 or not (0 <= start < end <= len(tokens)):
            continue
        if not correction or len(correction.split()) != 1 or correction == "-NONE-":
            continue
        error = tokens[start]
        if error == correction:
            continue
        correction_hash = sha256_bytes(correction.encode("utf-8"))
        edit_key = f"{record_key}:{start}:{end}:{correction_hash}"
        candidates.append({
            "edit_key": edit_key,
            "record_key": record_key,
            "passage": source,
            "error": error,
            "correction": correction,
            "start": start,
            "end": end,
        })
    return candidates


def hash_order(prefix: str, edit_key: str) -> str:
    return sha256_bytes(f"{prefix}|{SEED}|{edit_key}".encode("utf-8"))


def build_split(archive: zipfile.ZipFile, rows: list[dict], split: str) -> tuple[list[dict], dict]:
    eligible_field = "eligible_for_training" if split == "train" else "eligible_for_development"
    by_members: dict[tuple[str, str], list[dict]] = {}
    exclusions = {"document_filter": 0, "no_eligible_action": 0}
    for row in rows:
        allowed = (
            row["year"] == 2014 and row["track"] == "L1" and row[eligible_field] is True
            and row["duplicate_source_within_split"] is False
            and row["exact_source_overlap_with_qalb_test"] is False
            and row["exact_source_overlap_with_nahw"] is False
            and row["source_sha256"] != row["correction_sha256"]
        )
        if not allowed:
            exclusions["document_filter"] += 1
            continue
        member_marker = f"/data/2014/{split}/QALB-2014-L1-{'Train' if split == 'train' else 'Dev'}."
        if member_marker not in row["sent_member"] or member_marker not in row["m2_member"]:
            raise AdapterError(f"Manifest member violates frozen split: {row['record_key']}")
        by_members.setdefault((row["sent_member"], row["m2_member"]), []).append(row)

    selected = []
    for (sent_member, m2_member), group in by_members.items():
        sources = parse_sent(decode_member(archive, sent_member), sent_member)
        blocks = parse_m2_blocks(decode_member(archive, m2_member), m2_member)
        if len(sources) != len(blocks):
            raise AdapterError(f"Parallel member count mismatch: {sent_member}")
        for row in group:
            index = row["line_number"] - 1
            if not 0 <= index < len(sources):
                raise AdapterError(f"Manifest line out of range: {row['record_key']}")
            source = sources[index]
            m2_source, actions = blocks[index]
            if source != m2_source or sha256_bytes(source.encode("utf-8")) != row["source_sha256"]:
                raise AdapterError(f"Source integrity mismatch: {row['record_key']}")
            candidates = eligible_actions(source, actions, row["record_key"])
            if not candidates:
                exclusions["no_eligible_action"] += 1
                continue
            selected.append(min(candidates, key=lambda item: hash_order("F1-P1-edit", item["edit_key"])))
    return selected, exclusions


def private_record(edit: dict, split: str) -> dict:
    return {
        "record_id": edit["edit_key"],
        "prompt": [{"role": "user", "content": PROMPT.format(passage=edit["passage"], error=edit["error"])}],
        "completion": [{"role": "assistant", "content": edit["correction"]}],
        "source": "QALB-2014-L1",
        "split": split,
    }


def render_jsonl(rows: list[dict]) -> bytes:
    return "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows).encode("utf-8")


def prepare(archive_path: Path, train_manifest: Path, dev_manifest: Path, summary_path: Path, train_limit: int) -> tuple[list[dict], list[dict], dict]:
    summary = load_json(summary_path)
    archive_hash = file_sha256(archive_path)
    expected_hash = summary.get("inputs", {}).get("archive_sha256") or summary.get("archive_sha256")
    if not isinstance(expected_hash, str):
        raise AdapterError("Manifest summary does not contain an archive checksum")
    if archive_hash != expected_hash:
        raise AdapterError("QALB archive checksum does not match manifest summary")
    output_hashes = summary.get("output_sha256", {})
    for path in (train_manifest, dev_manifest):
        expected_manifest_hash = output_hashes.get(path.name)
        if not isinstance(expected_manifest_hash, str) or file_sha256(path) != expected_manifest_hash:
            raise AdapterError(f"Manifest checksum does not match summary: {path.name}")
    train_rows = load_manifest(train_manifest, "train")
    dev_rows = load_manifest(dev_manifest, "dev")
    with zipfile.ZipFile(archive_path) as archive:
        train_edits, train_exclusions = build_split(archive, train_rows, "train")
        dev_edits, dev_exclusions = build_split(archive, dev_rows, "dev")
    train_edits.sort(key=lambda item: hash_order("F1-P1", item["edit_key"]))
    dev_edits.sort(key=lambda item: hash_order("F1-P1-dev", item["edit_key"]))
    if len(train_edits) < train_limit:
        raise AdapterError(f"Insufficient eligible training edits: observed={len(train_edits)} required={train_limit}")
    train_edits = train_edits[:train_limit]
    train_private = [private_record(edit, "train") for edit in train_edits]
    dev_private = [private_record(edit, "development") for edit in dev_edits]
    metadata = {
        "protocol_id": PROTOCOL_ID,
        "seed": SEED,
        "archive_sha256": archive_hash,
        "train_manifest_sha256": file_sha256(train_manifest),
        "dev_manifest_sha256": file_sha256(dev_manifest),
        "train_records": len(train_private),
        "development_records": len(dev_private),
        "train_exclusions": train_exclusions,
        "development_exclusions": dev_exclusions,
        "train_selection_sha256": sha256_bytes(render_jsonl([{"record_id": row["record_id"]} for row in train_private])),
        "development_selection_sha256": sha256_bytes(render_jsonl([{"record_id": row["record_id"]} for row in dev_private])),
        "contains_corpus_text": False,
    }
    return train_private, dev_private, metadata


def safe_output_dir(path: Path) -> Path:
    resolved = path.resolve()
    private_root = (ROOT / "data/processed").resolve()
    if resolved != private_root and private_root not in resolved.parents:
        raise AdapterError("Private output directory must stay under data/processed")
    return resolved


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--train-manifest", type=Path, default=DEFAULT_TRAIN_MANIFEST)
    parser.add_argument("--dev-manifest", type=Path, default=DEFAULT_DEV_MANIFEST)
    parser.add_argument("--manifest-summary", type=Path, default=DEFAULT_MANIFEST_SUMMARY)
    parser.add_argument("--train-limit", type=int, default=2000, help=argparse.SUPPRESS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--write-private-records", action="store_true")
    parser.add_argument("--confirm-license-guidance", action="store_true")
    args = parser.parse_args()
    if args.train_limit != 2000:
        raise AdapterError("F1-P1 train limit is frozen at 2000")
    train, dev, summary = prepare(args.archive, args.train_manifest, args.dev_manifest, args.manifest_summary, args.train_limit)
    if args.write_private_records:
        if not args.confirm_license_guidance:
            raise AdapterError("Writing private records requires --confirm-license-guidance")
        output_dir = safe_output_dir(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "train_records.jsonl").write_bytes(render_jsonl(train))
        (output_dir / "dev_records.jsonl").write_bytes(render_jsonl(dev))
        (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    print("No corpus text was printed. QALB test and Nahw-Passage remain evaluation-only.")


if __name__ == "__main__":
    main()
