#!/usr/bin/env python3
"""Prepare frozen private overcorrection and ArabicMMLU capability inputs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess

from scripts.baseline_prompts import render_b0_prompt


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QALB = (
    ROOT / "data" / "raw" / "qalb" / "QALB-0.9.1-Dec03-2021-SharedTasks"
    / "data" / "2015" / "dev" / "QALB-2015-L2-Dev.m2"
)
DEFAULT_ARABICMMLU = ROOT / "data" / "raw" / "arabicmmlu"
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "f1_safety_eval"
QALB_SHA256 = "026e2b2164cb8b9da16f40fefc77b582384f2b6c7db3e9a1673494d776b00c0f"
QALB_COR_SHA256 = "a1bf62ea4a14290d0a69cddebe793d2abe8d94bbceb59f294b76714547217f20"
ARABICMMLU_REVISION = "7aa530e2893ac420352b3f5c1a1310c010e9758b"
EXPECTED_OVERCORRECTION_PREPARED_SHA256 = (
    "fa0c3f7a5321ae0a97528aaaf8df0ac29fce0039d3fad9b1e3cf83de71ac2036"
)
EXPECTED_CAPABILITY_PREPARED_SHA256 = (
    "ff6d250150016a4a9d18248bd7af632d67c14a978c87ccb3e50cb2d28d4e9f9a"
)
EXPECTED_SOURCE_MANIFEST_SHA256 = (
    "bd4c4ea40f5871fbd8055284ae83f1af93f2416b15e7a2817a86388f9d5be65b"
)
EXPECTED_QALB_RECORDS = 154
EXPECTED_TASKS = 40
CAPABILITY_PER_TASK = 25
SEED = 3407
WRITE_CONFIRMATION = "I_CONFIRM_PRIVATE_LICENSED_DERIVATION"


class SafetyPreparationError(ValueError):
    """Raised when a frozen safety-input invariant fails."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _is_arabic_script_token(token: str) -> bool:
    ranges = (
        (0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF),
        (0xFB50, 0xFDFF), (0xFE70, 0xFEFF),
    )
    return any(any(low <= ord(char) <= high for low, high in ranges) for char in token)


def _apply_m2_edits(source: str, action_lines: list[str]) -> str:
    tokens = source.split()
    edits: list[tuple[int, int, list[str]]] = []
    for line in action_lines:
        fields = line[2:].split("|||")
        if len(fields) < 6 or fields[-1] != "0":
            raise SafetyPreparationError("M2 action must be valid annotator 0 input")
        try:
            start, end = (int(value) for value in fields[0].split())
        except (ValueError, TypeError) as error:
            raise SafetyPreparationError("invalid M2 span") from error
        if start == end == -1:
            continue
        if not (0 <= start <= end <= len(tokens)):
            raise SafetyPreparationError("M2 span is out of range")
        correction = [] if fields[2] in ("", "-NONE-") else fields[2].split()
        edits.append((start, end, correction))
    ordered = sorted(edits, key=lambda edit: (edit[0], edit[1]))
    for previous, current in zip(ordered, ordered[1:]):
        if current[0] < previous[1]:
            raise SafetyPreparationError("overlapping M2 edits are unsupported")
    for start, end, correction in reversed(ordered):
        tokens[start:end] = correction
    if not tokens:
        raise SafetyPreparationError("M2 correction produced an empty target")
    return " ".join(tokens)


def build_overcorrection_records(path: Path) -> list[dict]:
    path = Path(path)
    if sha256_file(path) != QALB_SHA256:
        raise SafetyPreparationError("QALB-2015 L2 development SHA-256 mismatch")
    cor_path = path.with_suffix(".cor")
    if sha256_file(cor_path) != QALB_COR_SHA256:
        raise SafetyPreparationError("QALB-2015 L2 development COR SHA-256 mismatch")
    try:
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    except (OSError, UnicodeError) as error:
        raise SafetyPreparationError("unable to read UTF-8 QALB development M2") from error
    blocks = [block for block in text.split("\n\n") if block.strip()]
    if len(blocks) != EXPECTED_QALB_RECORDS:
        raise SafetyPreparationError("QALB development record count mismatch")
    try:
        cor_lines = cor_path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError) as error:
        raise SafetyPreparationError("unable to read UTF-8 QALB development COR") from error
    if len(cor_lines) != EXPECTED_QALB_RECORDS or any(
        not line.startswith("S ") for line in cor_lines
    ):
        raise SafetyPreparationError("QALB development COR structure mismatch")
    records = []
    for index, block in enumerate(blocks):
        lines = block.splitlines()
        sources = [line[2:] for line in lines if line.startswith("S ")]
        if len(sources) != 1:
            raise SafetyPreparationError("each M2 block must contain exactly one source")
        target = _apply_m2_edits(
            sources[0], [line for line in lines if line.startswith("A ")]
        )
        if target != cor_lines[index][2:]:
            raise SafetyPreparationError("M2 target differs from official COR target")
        tokens = target.split()
        eligible = [position for position, token in enumerate(tokens) if _is_arabic_script_token(token)]
        if not eligible:
            raise SafetyPreparationError("corrected target has no Arabic-script token")
        record_id = f"qalb15-l2-dev-{index:04d}"
        position = min(
            eligible,
            key=lambda item: _digest(f"F1-overcorrection|{SEED}|{record_id}|{item}"),
        )
        token = tokens[position]
        records.append({
            "record_id": record_id,
            "source": "QALB-2015-L2-Dev",
            "split": "dev",
            "passage": target,
            "selected_token_position": position,
            "selected_token": token,
            "gold_unchanged_token": token,
            "prompt": render_b0_prompt(target, token),
        })
    return records


def _git_revision(path: Path) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=path, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise SafetyPreparationError("unable to verify ArabicMMLU Git revision") from error


def render_arabicmmlu_prompt(row: dict[str, str]) -> tuple[str, list[str]]:
    levels = {
        "Primary": "primary school", "Middle": "middle school",
        "High": "high school", "Univ": "university", "Prof": "professional",
    }
    level = "" if not row["Level"] else " for " + levels[row["Level"]]
    country = "" if not row["Country"] else " in " + row["Country"]
    metadata = f"{row['Subject']} question{level}{country}"
    question = row["Question"] if not row["Context"] else (
        f"{row['Context']}\n\n{row['Question']}"
    )
    letters = ["A", "B", "C", "D", "E"]
    choices = [row[f"Option {index}"] for index in range(1, 6) if row[f"Option {index}"]]
    options = "\n".join(f"{letters[index]}. {choice}" for index, choice in enumerate(choices))
    prompt = f"This is a {metadata}. Select the correct answer!\n\nQuestion: {question}\n{options}\n\nAnswer:"
    return prompt, letters[: len(choices)]


def build_capability_records(root: Path) -> tuple[list[dict], list[dict]]:
    root = Path(root)
    if _git_revision(root) != ARABICMMLU_REVISION:
        raise SafetyPreparationError("ArabicMMLU revision mismatch")
    files = sorted(path for path in root.glob("*/test.csv") if path.parent.name != "All")
    if len(files) != EXPECTED_TASKS:
        raise SafetyPreparationError("ArabicMMLU task count mismatch")
    schema = [
        "ID", "Source", "Country", "Group", "Subject", "Level", "Question",
        "Context", "Answer Key", "Option 1", "Option 2", "Option 3", "Option 4",
        "Option 5", "is_few_shot",
    ]
    selected: list[dict] = []
    file_manifest: list[dict] = []
    seen: set[str] = set()
    for path in files:
        task = path.parent.name
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != schema:
                raise SafetyPreparationError("ArabicMMLU CSV schema mismatch")
            rows = list(reader)
        if len(rows) < CAPABILITY_PER_TASK:
            raise SafetyPreparationError("ArabicMMLU task has fewer than 25 test rows")
        ranked = sorted(
            rows,
            key=lambda row: _digest(f"F1-capability|{SEED}|{task}|{row['ID']}"),
        )[:CAPABILITY_PER_TASK]
        for row in ranked:
            identity = f"{task}|{row['ID']}"
            if identity in seen:
                raise SafetyPreparationError("duplicate ArabicMMLU selected identity")
            prompt, choices = render_arabicmmlu_prompt(row)
            if row["Answer Key"] not in choices:
                raise SafetyPreparationError("ArabicMMLU answer key is not an available choice")
            selected.append({
                "record_id": f"arabicmmlu-{_digest(identity)[:20]}",
                "task": task,
                "source_id": row["ID"],
                "source": "MBZUAI/ArabicMMLU",
                "split": "test",
                "prompt": prompt,
                "choices": choices,
                "gold_choice": row["Answer Key"],
            })
            seen.add(identity)
        file_manifest.append({
            "task": task,
            "path": path.relative_to(root).as_posix(),
            "records": len(rows),
            "sha256": sha256_file(path),
        })
    if len(selected) != EXPECTED_TASKS * CAPABILITY_PER_TASK:
        raise SafetyPreparationError("ArabicMMLU selected record count mismatch")
    return selected, file_manifest


def _records_sha256(records: list[dict]) -> str:
    payload = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def prepare(
    qalb_path: Path,
    arabicmmlu_root: Path,
    output_dir: Path,
    *,
    write_private_records: bool,
    confirmation: str | None,
) -> dict:
    overcorrection = build_overcorrection_records(qalb_path)
    capability, file_manifest = build_capability_records(arabicmmlu_root)
    overcorrection_sha256 = _records_sha256(overcorrection)
    capability_sha256 = _records_sha256(capability)
    source_manifest_sha256 = _canonical_sha256(file_manifest)
    if overcorrection_sha256 != EXPECTED_OVERCORRECTION_PREPARED_SHA256:
        raise SafetyPreparationError("frozen overcorrection selection SHA-256 mismatch")
    if capability_sha256 != EXPECTED_CAPABILITY_PREPARED_SHA256:
        raise SafetyPreparationError("frozen capability selection SHA-256 mismatch")
    if source_manifest_sha256 != EXPECTED_SOURCE_MANIFEST_SHA256:
        raise SafetyPreparationError("frozen ArabicMMLU source manifest SHA-256 mismatch")
    summary = {
        "schema_version": 1,
        "seed": SEED,
        "overcorrection": {
            "source": "QALB-2015-L2-Dev",
            "source_sha256": QALB_SHA256,
            "official_corrected_source_sha256": QALB_COR_SHA256,
            "records": len(overcorrection),
            "prepared_records_sha256": overcorrection_sha256,
        },
        "capability": {
            "source": "MBZUAI/ArabicMMLU",
            "license": "CC BY-NC 4.0",
            "revision": ARABICMMLU_REVISION,
            "tasks": EXPECTED_TASKS,
            "records_per_task": CAPABILITY_PER_TASK,
            "records": len(capability),
            "prepared_records_sha256": capability_sha256,
            "source_manifest_sha256": source_manifest_sha256,
            "choice_count_distribution": {
                str(size): sum(len(row["choices"]) == size for row in capability)
                for size in range(2, 6)
            },
            "source_files": file_manifest,
        },
        "contains_corpus_text": False,
        "nahw_passage_used": False,
        "qalb_test_used": False,
        "model_inference_executed": False,
    }
    if not write_private_records:
        return summary
    if confirmation != WRITE_CONFIRMATION:
        raise SafetyPreparationError("exact private derivation confirmation is required")
    output_dir = Path(output_dir).expanduser().resolve()
    allowed = (ROOT / "data" / "processed").resolve()
    try:
        output_dir.relative_to(allowed)
    except ValueError as error:
        raise SafetyPreparationError("private outputs must stay under data/processed") from error
    if output_dir.exists():
        raise SafetyPreparationError("private output directory already exists")
    output_dir.mkdir(parents=True)
    for name, rows in (("overcorrection.jsonl", overcorrection), ("arabicmmlu.jsonl", capability)):
        with (output_dir / name).open("x", encoding="utf-8", newline="\n") as stream:
            for row in rows:
                stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    (output_dir / "selection_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qalb-m2", type=Path, default=DEFAULT_QALB)
    parser.add_argument("--arabicmmlu-root", type=Path, default=DEFAULT_ARABICMMLU)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write-private-records", action="store_true")
    parser.add_argument("--confirm-license-guidance")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        summary = prepare(
            args.qalb_m2, args.arabicmmlu_root, args.output_dir,
            write_private_records=args.write_private_records,
            confirmation=args.confirm_license_guidance,
        )
    except (OSError, SafetyPreparationError) as error:
        raise SystemExit(f"ERROR: {error}") from error
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
