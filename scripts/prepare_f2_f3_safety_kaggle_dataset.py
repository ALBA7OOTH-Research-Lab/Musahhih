#!/usr/bin/env python3
"""Prepare one private Kaggle artifact dataset; never upload it."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from scripts.f2_f3_safety_eval_utils import (
    APPROVAL_PATTERN,
    ARM_SPECS,
    EXPECTED_CAPABILITY_SHA256,
    EXPECTED_OVERCORRECTION_SHA256,
    REFERENCE_PREDICTION_SHA256,
    EvaluationSafetyError,
    load_capability_records,
    load_overcorrection_records,
    sha256_file,
    validate_adapter_checkpoint,
)
from scripts.run_f2_f3_safety_eval import load_reference_predictions


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUTS = ROOT / "outputs"
CONFIRMATION = "PREPARE_PRIVATE_F2_F3_SAFETY_ARTIFACT_DATASET"
DATASET_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9-]*")


class DatasetPreparationError(ValueError):
    """Raised before uploading or overwriting any private artifact bundle."""


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def validate_output_dir(path: Path) -> Path:
    resolved = Path(path).expanduser().resolve()
    if not _is_relative_to(resolved, DEFAULT_OUTPUTS.resolve()):
        raise DatasetPreparationError(
            "private bundle must stay under the ignored outputs directory"
        )
    if resolved.exists():
        raise DatasetPreparationError("output directory exists; refusing overwrite")
    return resolved


def require_preparation_authorization(
    confirmation: str | None,
    approved_commit: str | None,
    approval_reference: str | None,
) -> None:
    if confirmation != CONFIRMATION:
        raise DatasetPreparationError("exact private-dataset confirmation required")
    if not approved_commit or not re.fullmatch(r"[0-9a-f]{40}", approved_commit):
        raise DatasetPreparationError("approved commit must be lowercase SHA-1")
    if not approval_reference or not APPROVAL_PATTERN.fullmatch(approval_reference):
        raise DatasetPreparationError("approval must be an issue #200 comment URL")
    try:
        observed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise DatasetPreparationError("unable to verify exact repository commit") from error
    if observed != approved_commit:
        raise DatasetPreparationError("checkout is not the exact approved commit")


def _copy_fsync(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Path(source).open("rb") as input_stream, destination.open("xb") as output_stream:
        shutil.copyfileobj(input_stream, output_stream, length=1024 * 1024)
        output_stream.flush()
        os.fsync(output_stream.fileno())


def write_dataset_bundle(
    *,
    output_dir: Path,
    dataset_id: str,
    sources: dict[str, Path],
) -> dict:
    """Copy an already validated minimal private bundle without overwriting."""

    if not DATASET_PATTERN.fullmatch(dataset_id):
        raise DatasetPreparationError("dataset id must be owner/slug")
    output_dir = validate_output_dir(output_dir)
    if not sources or len(sources) != len(set(sources)):
        raise DatasetPreparationError("bundle sources must be nonempty and unique")
    output_dir.mkdir(parents=True)
    manifest_files = {}
    try:
        for relative, source in sorted(sources.items()):
            relative_path = Path(relative)
            if relative_path.is_absolute() or ".." in relative_path.parts:
                raise DatasetPreparationError("unsafe bundle member path")
            if not Path(source).is_file():
                raise DatasetPreparationError("validated bundle source is missing")
            destination = output_dir / relative_path
            _copy_fsync(Path(source), destination)
            manifest_files[relative_path.as_posix()] = {
                "bytes": destination.stat().st_size,
                "sha256": sha256_file(destination),
            }
        metadata = {
            "title": dataset_id.split("/", 1)[1].replace("-", " ").title(),
            "id": dataset_id,
            "licenses": [{"name": "other"}],
        }
        (output_dir / "dataset-metadata.json").write_text(
            json.dumps(metadata, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        manifest = {
            "schema_version": 1,
            "dataset_id": dataset_id,
            "private_upload_required": True,
            "files": manifest_files,
            "contains_private_corpus_text": True,
            "contains_private_model_artifacts": True,
            "upload_executed": False,
        }
        (output_dir / "private_bundle_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return manifest
    except Exception:
        (output_dir / "INVALID_INCOMPLETE_BUNDLE").write_text(
            "invalid\n", encoding="utf-8", newline="\n"
        )
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--overcorrection-input", type=Path, required=True)
    parser.add_argument("--capability-input", type=Path, required=True)
    parser.add_argument("--f2-adapter", type=Path, required=True)
    parser.add_argument("--f3-adapter", type=Path, required=True)
    parser.add_argument("--b0-overcorrection-predictions", type=Path, required=True)
    parser.add_argument("--f1-overcorrection-predictions", type=Path, required=True)
    parser.add_argument("--b0-capability-predictions", type=Path, required=True)
    parser.add_argument("--f1-capability-predictions", type=Path, required=True)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--confirmation")
    parser.add_argument("--approved-commit")
    parser.add_argument("--approval-reference")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.prepare:
        print(json.dumps({
            "status": "disabled",
            "private_artifact_accessed": False,
            "bundle_created": False,
            "upload_executed": False,
        }, indent=2))
        return
    try:
        require_preparation_authorization(
            args.confirmation,
            args.approved_commit,
            args.approval_reference,
        )
        validate_output_dir(args.output_dir)
        overcorrection_records = load_overcorrection_records(args.overcorrection_input)
        capability_records = load_capability_records(args.capability_input)
        validate_adapter_checkpoint(args.f2_adapter, ARM_SPECS["F2-P1"])
        validate_adapter_checkpoint(args.f3_adapter, ARM_SPECS["F3-P1"])
        reference_paths = {
            "B0_overcorrection": args.b0_overcorrection_predictions,
            "F1-P1_overcorrection": args.f1_overcorrection_predictions,
            "B0_capability": args.b0_capability_predictions,
            "F1-P1_capability": args.f1_capability_predictions,
        }
        load_reference_predictions(
            reference_paths,
            overcorrection_records=overcorrection_records,
            capability_records=capability_records,
        )
        sources = {
            "inputs/overcorrection.jsonl": args.overcorrection_input,
            "inputs/arabicmmlu.jsonl": args.capability_input,
            "f2/checkpoint_selection.json": args.f2_adapter.parent / "checkpoint_selection.json",
            "f2/checkpoint-125/adapter_model.safetensors": args.f2_adapter / "adapter_model.safetensors",
            "f2/checkpoint-125/adapter_config.json": args.f2_adapter / "adapter_config.json",
            "f3/checkpoint_selection.json": args.f3_adapter.parent / "checkpoint_selection.json",
            "f3/checkpoint-250/adapter_model.safetensors": args.f3_adapter / "adapter_model.safetensors",
            "f3/checkpoint-250/adapter_config.json": args.f3_adapter / "adapter_config.json",
            "references/b0_overcorrection_predictions.jsonl": args.b0_overcorrection_predictions,
            "references/f1_p1_overcorrection_predictions.jsonl": args.f1_overcorrection_predictions,
            "references/b0_capability_predictions.jsonl": args.b0_capability_predictions,
            "references/f1_p1_capability_predictions.jsonl": args.f1_capability_predictions,
        }
        manifest = write_dataset_bundle(
            output_dir=args.output_dir,
            dataset_id=args.dataset_id,
            sources=sources,
        )
        expected = {
            "inputs/overcorrection.jsonl": EXPECTED_OVERCORRECTION_SHA256,
            "inputs/arabicmmlu.jsonl": EXPECTED_CAPABILITY_SHA256,
            "f2/checkpoint_selection.json": ARM_SPECS["F2-P1"].checkpoint_selection_sha256,
            "f2/checkpoint-125/adapter_model.safetensors": ARM_SPECS["F2-P1"].adapter_model_sha256,
            "f2/checkpoint-125/adapter_config.json": ARM_SPECS["F2-P1"].adapter_config_sha256,
            "f3/checkpoint_selection.json": ARM_SPECS["F3-P1"].checkpoint_selection_sha256,
            "f3/checkpoint-250/adapter_model.safetensors": ARM_SPECS["F3-P1"].adapter_model_sha256,
            "f3/checkpoint-250/adapter_config.json": ARM_SPECS["F3-P1"].adapter_config_sha256,
            "references/b0_overcorrection_predictions.jsonl": REFERENCE_PREDICTION_SHA256["B0_overcorrection"],
            "references/f1_p1_overcorrection_predictions.jsonl": REFERENCE_PREDICTION_SHA256["F1-P1_overcorrection"],
            "references/b0_capability_predictions.jsonl": REFERENCE_PREDICTION_SHA256["B0_capability"],
            "references/f1_p1_capability_predictions.jsonl": REFERENCE_PREDICTION_SHA256["F1-P1_capability"],
        }
        observed = {name: item["sha256"] for name, item in manifest["files"].items()}
        if observed != expected:
            raise EvaluationSafetyError("private bundle manifest identity mismatch")
        print(json.dumps({
            "status": "prepared",
            "dataset_id": args.dataset_id,
            "files": len(manifest["files"]),
            "total_bytes": sum(item["bytes"] for item in manifest["files"].values()),
            "contains_private_corpus_text": True,
            "contains_private_model_artifacts": True,
            "upload_executed": False,
        }, indent=2))
    except (DatasetPreparationError, EvaluationSafetyError, OSError) as error:
        raise SystemExit(f"ERROR: {error}") from error


if __name__ == "__main__":
    main()
