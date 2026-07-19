#!/usr/bin/env python3
"""Build private, leakage-guarded Tibyan F2/F3 manifests without logging text."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ARCHIVE_SHA256 = (
    "a7f318d9c64d7d2c214a5f44ee515b70c7d1ee930178b4b6b00cf5c733b0dfda"
)
EXPECTED_CORRECTED_SHA256 = (
    "5f8fde9319df89419ade12114f14466301cafb181ce807df896fb5de2361c4e4"
)
EXPECTED_ERRONEOUS_SHA256 = (
    "e3b72a45abffbf2a63da07912adc0fa0b29a41c495d609aa2b917fc4d58956a6"
)
EXPECTED_LINES = 6192
SEED = 3407
TRAIN_LIMIT = 2000
OUTPUT_NAMES = (
    "tibyan_registry.jsonl",
    "tibyan_train_selection.jsonl",
    "tibyan_dev_selection.jsonl",
    "tibyan_manifest_summary.json",
)


class TibyanManifestError(ValueError):
    """Raised when an input or derived manifest violates the frozen contract."""


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


def hashed_order(prefix: str, value: str) -> str:
    return sha256_text(f"{prefix}|{SEED}|{value}")


def distance_matrix(source: list[str], target: list[str]) -> list[list[int]]:
    matrix = [[0] * (len(target) + 1) for _ in range(len(source) + 1)]
    for source_index in range(len(source) + 1):
        matrix[source_index][0] = source_index
    for target_index in range(len(target) + 1):
        matrix[0][target_index] = target_index
    for source_index, source_token in enumerate(source, 1):
        row = matrix[source_index]
        previous = matrix[source_index - 1]
        for target_index, target_token in enumerate(target, 1):
            row[target_index] = min(
                previous[target_index] + 1,
                row[target_index - 1] + 1,
                previous[target_index - 1] + (source_token != target_token),
            )
    return matrix


def forced_substitutions(
    source: list[str], target: list[str]
) -> tuple[int, list[tuple[int, int, str, str]]]:
    """Return substitutions traversed by every minimum-cost token alignment."""
    forward = distance_matrix(source, target)
    reverse = distance_matrix(list(reversed(source)), list(reversed(target)))
    source_size, target_size = len(source), len(target)
    minimum_distance = forward[source_size][target_size]

    def backward(source_index: int, target_index: int) -> int:
        return reverse[source_size - source_index][target_size - target_index]

    active_by_layer: Counter[int] = Counter()
    optimal_substitutions: list[tuple[int, int, str, str, int]] = []
    for source_index in range(source_size + 1):
        for target_index in range(target_size + 1):
            if (
                forward[source_index][target_index]
                + backward(source_index, target_index)
                == minimum_distance
            ):
                active_by_layer[source_index + target_index] += 1
            if source_index == source_size or target_index == target_size:
                continue
            is_substitution = source[source_index] != target[target_index]
            if (
                forward[source_index][target_index]
                + int(is_substitution)
                + backward(source_index + 1, target_index + 1)
                == minimum_distance
            ):
                virtual_layer = source_index + target_index + 1
                active_by_layer[virtual_layer] += 1
                if is_substitution:
                    optimal_substitutions.append(
                        (
                            source_index,
                            target_index,
                            source[source_index],
                            target[target_index],
                            virtual_layer,
                        )
                    )

    forced = [
        substitution[:4]
        for substitution in optimal_substitutions
        if active_by_layer[substitution[4]] == 1
    ]
    return minimum_distance, forced


def derive_candidates(
    erroneous_lines: list[str], corrected_lines: list[str]
) -> tuple[list[dict], dict]:
    if len(erroneous_lines) != len(corrected_lines):
        raise TibyanManifestError("Tibyan final files have different line counts")
    candidates: list[dict] = []
    counts: Counter[str] = Counter()
    whole_pair_counts: Counter[str] = Counter()
    distances: list[int] = []
    for line_number, (erroneous, corrected) in enumerate(
        zip(erroneous_lines, corrected_lines), 1
    ):
        if not erroneous or not corrected:
            raise TibyanManifestError(f"Empty Tibyan final line at {line_number}")
        error_tokens = erroneous.split()
        correction_tokens = corrected.split()
        if erroneous == corrected:
            whole_pair_counts["identical"] += 1
        elif len(error_tokens) != len(correction_tokens):
            whole_pair_counts["token_count_mismatch"] += 1
        elif sum(
            error_token != correction_token
            for error_token, correction_token in zip(
                error_tokens, correction_tokens
            )
        ) == 1:
            whole_pair_counts["eligible_single_substitution"] += 1
        else:
            whole_pair_counts["multiple_token_differences"] += 1
        distance, substitutions = forced_substitutions(
            error_tokens, correction_tokens
        )
        distances.append(distance)
        counts["forced_substitution_edges"] += len(substitutions)
        counts["pairs_with_forced_substitution"] += bool(substitutions)
        eligible = [
            substitution
            for substitution in substitutions
            if error_tokens.count(substitution[2]) == 1
        ]
        counts["unique_error_forced_substitution_edges"] += len(eligible)
        counts["pairs_with_unique_error_forced_substitution"] += bool(eligible)
        if not eligible:
            continue
        selected = min(
            eligible,
            key=lambda item: sha256_text(
                "|".join(
                    (
                        "Tibyan-edit",
                        str(SEED),
                        str(line_number),
                        str(item[0]),
                        str(item[1]),
                        sha256_text(item[3]),
                    )
                )
            ),
        )
        source_index, target_index, error_token, correction_token = selected
        erroneous_hash = sha256_text(erroneous)
        corrected_hash = sha256_text(corrected)
        error_token_hash = sha256_text(error_token)
        correction_token_hash = sha256_text(correction_token)
        identity = "|".join(
            (
                "Tibyan-record",
                "14623621",
                str(line_number),
                erroneous_hash,
                corrected_hash,
                str(source_index),
                str(target_index),
                error_token_hash,
                correction_token_hash,
            )
        )
        candidates.append(
            {
                "record_id": f"tibyan-14623621-{sha256_text(identity)}",
                "source_dataset": "Tibyan-corpus",
                "source_release": "Zenodo-14623621",
                "source_line_number": line_number,
                "erroneous_sha256": erroneous_hash,
                "corrected_sha256": corrected_hash,
                "error_token_sha256": error_token_hash,
                "correction_token_sha256": correction_token_hash,
                "error_token_index": source_index,
                "correction_token_index": target_index,
                "minimum_token_edit_distance": distance,
                "passage": erroneous,
                "erroneous_word": error_token,
                "gold_correction": correction_token,
            }
        )
    if len({row["record_id"] for row in candidates}) != len(candidates):
        raise TibyanManifestError("Derived Tibyan record IDs are not unique")
    distance_summary = {
        "minimum": min(distances) if distances else None,
        "median": sorted(distances)[len(distances) // 2] if distances else None,
        "maximum": max(distances) if distances else None,
    }
    return candidates, {
        **dict(counts),
        "token_edit_distance": distance_summary,
        "whole_pair_classification": dict(sorted(whole_pair_counts.items())),
    }


def assign_source_groups(records: list[dict]) -> dict[str, list[int]]:
    parent = list(range(len(records)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    seen: dict[str, int] = {}
    for index, record in enumerate(records):
        for digest in (record["erroneous_sha256"], record["corrected_sha256"]):
            if digest in seen:
                union(index, seen[digest])
            else:
                seen[digest] = index
    components: defaultdict[int, list[int]] = defaultdict(list)
    for index in range(len(records)):
        components[find(index)].append(index)
    groups: dict[str, list[int]] = {}
    for indexes in components.values():
        group_id = sha256_text(
            "Tibyan-group|"
            + "|".join(sorted(records[index]["record_id"] for index in indexes))
        )
        groups[group_id] = indexes
        for index in indexes:
            records[index]["source_group_id"] = group_id
    return groups


def load_qalb_hashes(path: Path) -> dict[str, set[str]]:
    roles = {"train_development": set(), "test": set()}
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            try:
                row = json.loads(line)
                role = "test" if row["split"] == "test" else "train_development"
                roles[role].update((row["source_sha256"], row["correction_sha256"]))
            except (json.JSONDecodeError, KeyError, TypeError) as error:
                raise TibyanManifestError(
                    f"Invalid QALB hash registry row {line_number}"
                ) from error
    return roles


def load_nahw_hashes(path: Path) -> set[str]:
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise TibyanManifestError("Invalid Nahw hash source") from error
    if not isinstance(rows, list):
        raise TibyanManifestError("Invalid Nahw hash source schema")
    hashes = set()
    for row in rows:
        if not isinstance(row, dict):
            raise TibyanManifestError("Invalid Nahw hash source row")
        for field in ("passage", "error", "correction", "explanation"):
            value = row.get(field)
            if isinstance(value, str):
                hashes.add(sha256_text(value))
    return hashes


def apply_overlap_and_split(
    records: list[dict],
    groups: dict[str, list[int]],
    qalb_hashes: dict[str, set[str]],
    nahw_hashes: set[str],
) -> tuple[list[dict], list[dict], dict]:
    representatives: list[dict] = []
    overlap_counts: Counter[str] = Counter()
    for group_id, indexes in groups.items():
        full_side_hashes = {
            digest
            for index in indexes
            for digest in (
                records[index]["erroneous_sha256"],
                records[index]["corrected_sha256"],
            )
        }
        flags = {
            "exact_overlap_qalb_test": bool(full_side_hashes & qalb_hashes["test"]),
            "exact_overlap_qalb_train_development": bool(
                full_side_hashes & qalb_hashes["train_development"]
            ),
            "exact_overlap_nahw": bool(full_side_hashes & nahw_hashes),
        }
        excluded = any(flags.values())
        bucket = int(
            sha256_text(f"Tibyan-project-split|{SEED}|{group_id}")[:16], 16
        ) % 100
        project_split = "excluded" if excluded else ("train" if bucket < 80 else "dev")
        for index in indexes:
            records[index].update(flags)
            records[index]["project_split"] = project_split
            for name, value in flags.items():
                overlap_counts[name] += bool(value)
        if excluded:
            continue
        representative_index = min(
            indexes,
            key=lambda index: hashed_order(
                "Tibyan-group-record", records[index]["record_id"]
            ),
        )
        representative = records[representative_index]
        representative["is_group_representative"] = True
        representatives.append(representative)
    for record in records:
        record.setdefault("is_group_representative", False)
    train = [row for row in representatives if row["project_split"] == "train"]
    development = [row for row in representatives if row["project_split"] == "dev"]
    train.sort(key=lambda row: hashed_order("F2-P1", row["record_id"]))
    development.sort(key=lambda row: hashed_order("F2-P1-dev", row["record_id"]))
    return train, development, dict(overlap_counts)


def private_record(record: dict, selection_rank: int | None = None) -> dict:
    output = dict(record)
    if selection_rank is not None:
        output["selection_rank"] = selection_rank
    return output


def render_jsonl(rows: Iterable[dict]) -> bytes:
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
        for row in rows
    ).encode("utf-8")


def prepare_manifest(
    erroneous_lines: list[str],
    corrected_lines: list[str],
    qalb_hashes: dict[str, set[str]],
    nahw_hashes: set[str],
    train_limit: int = TRAIN_LIMIT,
    registry_input_hashes: dict[str, str] | None = None,
) -> tuple[dict[str, bytes], dict]:
    candidates, alignment = derive_candidates(erroneous_lines, corrected_lines)
    groups = assign_source_groups(candidates)
    train_pool, development, overlap = apply_overlap_and_split(
        candidates, groups, qalb_hashes, nahw_hashes
    )
    if len(train_pool) < train_limit:
        raise TibyanManifestError(
            f"Only {len(train_pool)} Tibyan training groups; need {train_limit}"
        )
    selected_train = train_pool[:train_limit]
    registry_payload = render_jsonl(private_record(row) for row in candidates)
    train_payload = render_jsonl(
        private_record(row, rank)
        for rank, row in enumerate(selected_train, 1)
    )
    development_payload = render_jsonl(
        private_record(row, rank)
        for rank, row in enumerate(development, 1)
    )
    group_sizes = [len(indexes) for indexes in groups.values()]
    summary = {
        "schema_version": 1,
        "source": "Tibyan-corpus",
        "source_record": "Zenodo-14623621",
        "license": "CC-BY-4.0",
        "seed": SEED,
        "inputs": {
            "archive_sha256": EXPECTED_ARCHIVE_SHA256,
            "corrected_final_sha256": EXPECTED_CORRECTED_SHA256,
            "erroneous_final_sha256": EXPECTED_ERRONEOUS_SHA256,
            **(registry_input_hashes or {}),
        },
        "input_line_pairs": len(erroneous_lines),
        "alignment": alignment,
        "candidate_records": len(candidates),
        "connected_groups": len(groups),
        "groups_with_multiple_records": sum(size > 1 for size in group_sizes),
        "largest_group": max(group_sizes) if group_sizes else 0,
        "overlap_excluded_records": overlap,
        "project_split": {
            "training_records_before_group_representative": sum(
                row["project_split"] == "train" for row in candidates
            ),
            "development_records_before_group_representative": sum(
                row["project_split"] == "dev" for row in candidates
            ),
            "training_group_representatives": len(train_pool),
            "development_group_representatives": len(development),
        },
        "f2_train_records": len(selected_train),
        "f3_synthetic_nested_records": train_limit // 2,
        "f2_selection_record_id_sha256": sha256_bytes(
            ("\n".join(row["record_id"] for row in selected_train) + "\n").encode()
        ),
        "f3_synthetic_selection_record_id_sha256": sha256_bytes(
            (
                "\n".join(
                    row["record_id"] for row in selected_train[: train_limit // 2]
                )
                + "\n"
            ).encode()
        ),
        "contains_corpus_text": False,
        "nahw_passage_role": "hash-only leakage check; test-only",
        "qalb_test_role": "hash-only leakage check; test-only",
        "training_or_inference_executed": False,
    }
    payloads = {
        OUTPUT_NAMES[0]: registry_payload,
        OUTPUT_NAMES[1]: train_payload,
        OUTPUT_NAMES[2]: development_payload,
    }
    summary["private_output_sha256"] = {
        name: sha256_bytes(payload) for name, payload in payloads.items()
    }
    payloads[OUTPUT_NAMES[3]] = json.dumps(
        summary, ensure_ascii=False, indent=2, sort_keys=True
    ).encode("utf-8") + b"\n"
    return payloads, summary


def write_idempotent(output_dir: Path, payloads: dict[str, bytes]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    stale = [path.name for path in output_dir.glob(".*.tmp")]
    if stale:
        raise TibyanManifestError(
            "Stale temporary output(s): " + ", ".join(sorted(stale))
        )
    for name, payload in payloads.items():
        destination = output_dir / name
        if destination.exists():
            if destination.read_bytes() != payload:
                raise TibyanManifestError(
                    f"Existing output differs; refusing overwrite: {name}"
                )
            continue
        temporary = output_dir / f".{name}.tmp"
        temporary.write_bytes(payload)
        os.replace(temporary, destination)


def read_canonical_lines(path: Path, expected_sha256: str) -> list[str]:
    if file_sha256(path) != expected_sha256:
        raise TibyanManifestError(f"Input checksum mismatch: {path.name}")
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except UnicodeError as error:
        raise TibyanManifestError(f"Input is not UTF-8: {path.name}") from error
    if len(lines) != EXPECTED_LINES:
        raise TibyanManifestError(f"Unexpected line count: {path.name}")
    return lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--corrected", type=Path, required=True)
    parser.add_argument("--erroneous", type=Path, required=True)
    parser.add_argument(
        "--qalb-registry",
        type=Path,
        default=ROOT / "data/processed/qalb/qalb_registry.jsonl",
    )
    parser.add_argument(
        "--nahw",
        type=Path,
        default=ROOT / "data/raw/nahw/Nahw-Passage.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "data/processed/tibyan_f2_f3",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if file_sha256(args.archive) != EXPECTED_ARCHIVE_SHA256:
        raise TibyanManifestError("Tibyan archive checksum mismatch")
    erroneous = read_canonical_lines(args.erroneous, EXPECTED_ERRONEOUS_SHA256)
    corrected = read_canonical_lines(args.corrected, EXPECTED_CORRECTED_SHA256)
    payloads, summary = prepare_manifest(
        erroneous,
        corrected,
        load_qalb_hashes(args.qalb_registry),
        load_nahw_hashes(args.nahw),
        registry_input_hashes={
            "qalb_registry_sha256": file_sha256(args.qalb_registry),
            "nahw_sha256": file_sha256(args.nahw),
        },
    )
    write_idempotent(args.output_dir, payloads)
    print(
        json.dumps(
            {
                "status": "complete",
                "candidate_records": summary["candidate_records"],
                "training_group_representatives": summary["project_split"][
                    "training_group_representatives"
                ],
                "development_group_representatives": summary["project_split"][
                    "development_group_representatives"
                ],
                "f2_train_records": summary["f2_train_records"],
                "f2_selection_record_id_sha256": summary[
                    "f2_selection_record_id_sha256"
                ],
                "training_or_inference_executed": False,
                "corpus_text_printed": False,
            },
            sort_keys=True,
        )
    )
    print("Nahw-Passage and QALB test remained hash-only, evaluation-only inputs.")


if __name__ == "__main__":
    main()
