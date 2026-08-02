#!/usr/bin/env python3
"""Build one private F2/F3 diagnostic Kaggle kernel without executing it."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from scripts.f2_f3_safety_eval_utils import (
    ARM_SPECS,
    CONFIRMATION,
    EXPECTED_CAPABILITY_SHA256,
    EXPECTED_OVERCORRECTION_SHA256,
    REFERENCE_PREDICTION_SHA256,
    RUN_ID,
)


COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
APPROVAL_PATTERN = re.compile(
    r"https://github\.com/ALBA7OOTH-Research-Lab/Musahhih/"
    r"issues/200#issuecomment-[1-9][0-9]*"
)
SOURCE_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9-]*")
WRAPPER_FILENAME = "f2_f3_safety_diagnostics.py"
METADATA_FILENAME = "kernel-metadata.json"


class KernelPreparationError(ValueError):
    """Raised before creating an unsafe or ambiguous kernel package."""


def _validate_source(value: str, label: str) -> None:
    if not SOURCE_PATTERN.fullmatch(value):
        raise KernelPreparationError(f"{label} must be owner/slug")


def build_wrapper(
    *,
    approved_commit: str,
    approval_reference: str,
    replicate: int = 1,
    resume_summary_sha256: str | None = None,
) -> str:
    if not COMMIT_PATTERN.fullmatch(approved_commit):
        raise KernelPreparationError("approved commit must be 40 lowercase hex")
    if not APPROVAL_PATTERN.fullmatch(approval_reference):
        raise KernelPreparationError("approval must be an issue #200 comment URL")
    if not 1 <= replicate <= 99:
        raise KernelPreparationError("replicate must be between 1 and 99")
    if replicate == 1 and resume_summary_sha256 is not None:
        raise KernelPreparationError("replicate 1 cannot attach a resume summary")
    if replicate > 1 and (
        resume_summary_sha256 is None
        or not SHA256_PATTERN.fullmatch(resume_summary_sha256)
    ):
        raise KernelPreparationError("continuation requires an exact resume-summary SHA-256")
    run_id = RUN_ID.replace("__r01", f"__r{replicate:02d}")
    resume_literal = repr(resume_summary_sha256)
    return f'''import time

KERNEL_START_EPOCH_SECONDS = time.time()

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


APPROVED_COMMIT = "{approved_commit}"
APPROVAL_REFERENCE = "{approval_reference}"
RUN_ID = "{run_id}"
REPLICATE = {replicate}
RESUME_SUMMARY_SHA256 = {resume_literal}
EXPECTED_OVERCORRECTION_SHA256 = "{EXPECTED_OVERCORRECTION_SHA256}"
EXPECTED_CAPABILITY_SHA256 = "{EXPECTED_CAPABILITY_SHA256}"
EXPECTED_SELECTION_SHA256 = {{
    "F2-P1": "{ARM_SPECS['F2-P1'].checkpoint_selection_sha256}",
    "F3-P1": "{ARM_SPECS['F3-P1'].checkpoint_selection_sha256}",
}}
EXPECTED_CHECKPOINT = {{"F2-P1": "checkpoint-125", "F3-P1": "checkpoint-250"}}
REFERENCE_PREDICTION_SHA256 = {json.dumps(REFERENCE_PREDICTION_SHA256, sort_keys=True)}
REPOSITORY = "https://github.com/ALBA7OOTH-Research-Lab/Musahhih.git"
WORKING = Path("/kaggle/working")
REPO = WORKING / "Musahhih"


def run(command, *, cwd=None, env=None, timeout=None):
    return subprocess.run(command, cwd=cwd, env=env, check=True, timeout=timeout)


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if REPO.exists():
    raise RuntimeError("repository path exists; refusing mutable state")
run(["git", "clone", "--filter=blob:none", "--no-checkout", REPOSITORY, str(REPO)], timeout=120)
run(["git", "checkout", "--detach", APPROVED_COMMIT], cwd=REPO, timeout=60)
observed_commit = subprocess.run(
    ["git", "rev-parse", "HEAD"], cwd=REPO, check=True,
    capture_output=True, text=True, timeout=30,
).stdout.strip()
if observed_commit != APPROVED_COMMIT:
    raise RuntimeError("repository checkout differs from approved commit")
print({{"stage": "repository_gate", "git_commit": observed_commit, "passed": True}})


environment = dict(os.environ)
environment["UNSLOTH_COMPILE_DISABLE"] = "1"

# Restore the same P100-compatible runtime that completed the earlier F1/F2/F3 runs.
run(
    [sys.executable, "-m", "scripts.check_b1_b2_restored_p100"],
    cwd=REPO, env=environment, timeout=800,
)


INPUT_ROOT = Path("/kaggle/input")


def unique_hash(expected, label, filename=None):
    candidates = INPUT_ROOT.rglob(filename or "*")
    matches = [path for path in candidates if path.is_file() and sha256_file(path) == expected]
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one {{label}} artifact")
    return matches[0]


overcorrection_path = unique_hash(
    EXPECTED_OVERCORRECTION_SHA256, "overcorrection input", "overcorrection.jsonl"
)
capability_path = unique_hash(
    EXPECTED_CAPABILITY_SHA256, "capability input", "arabicmmlu.jsonl"
)
selection_paths = {{}}
for candidate in INPUT_ROOT.rglob("checkpoint_selection.json"):
    digest = sha256_file(candidate)
    for arm, expected in EXPECTED_SELECTION_SHA256.items():
        if digest == expected:
            if arm in selection_paths:
                raise RuntimeError(f"duplicate {{arm}} checkpoint selection")
            selection_paths[arm] = candidate
if set(selection_paths) != set(EXPECTED_SELECTION_SHA256):
    raise RuntimeError("expected exactly one frozen checkpoint selection per arm")
adapter_paths = {{}}
for arm, selection_path in selection_paths.items():
    adapter = selection_path.parent / EXPECTED_CHECKPOINT[arm]
    if not adapter.is_dir():
        raise RuntimeError(f"attached {{arm}} selected checkpoint is missing")
    adapter_paths[arm] = adapter
reference_paths = {{}}
for candidate in INPUT_ROOT.rglob("*_predictions.jsonl"):
    digest = sha256_file(candidate)
    for label, expected in REFERENCE_PREDICTION_SHA256.items():
        if digest == expected:
            if label in reference_paths:
                raise RuntimeError(f"duplicate {{label}} reference predictions")
            reference_paths[label] = candidate
if set(reference_paths) != set(REFERENCE_PREDICTION_SHA256):
    raise RuntimeError("expected all four immutable B0/F1 reference predictions")

resume_args = []
if RESUME_SUMMARY_SHA256 is not None:
    resume_candidates = [
        candidate
        for candidate in INPUT_ROOT.rglob("public_summary.json")
        if sha256_file(candidate) == RESUME_SUMMARY_SHA256
    ]
    if len(resume_candidates) != 1:
        raise RuntimeError("expected exactly one authorized resume summary")
    resume_summary_path = resume_candidates[0]
    resume_summary = json.loads(resume_summary_path.read_text(encoding="utf-8"))
    if (
        resume_summary.get("run_status") != "incomplete_time_budget"
        or resume_summary.get("git_commit") != APPROVED_COMMIT
        or resume_summary.get("metrics_reported") is not False
        or resume_summary.get("resume_requires_fresh_authorization") is not True
    ):
        raise RuntimeError("attached resume summary contract mismatch")
    resume_args = ["--resume-from", str(resume_summary_path.parent)]
print({{
    "stage": "private_input_gate",
    "overcorrection_hash_match": True,
    "capability_hash_match": True,
    "f2_checkpoint": adapter_paths["F2-P1"].name,
    "f3_checkpoint": adapter_paths["F3-P1"].name,
    "reference_hashes_match": True,
    "resume_summary_hash_match": RESUME_SUMMARY_SHA256 is not None,
    "passed": True,
}})


run([
    sys.executable, "-m", "scripts.run_f2_f3_safety_eval",
    "--f2-adapter", str(adapter_paths["F2-P1"]),
    "--f3-adapter", str(adapter_paths["F3-P1"]),
    "--overcorrection-input", str(overcorrection_path),
    "--capability-input", str(capability_path),
    "--b0-overcorrection-predictions", str(reference_paths["B0_overcorrection"]),
    "--f1-overcorrection-predictions", str(reference_paths["F1-P1_overcorrection"]),
    "--b0-capability-predictions", str(reference_paths["B0_capability"]),
    "--f1-capability-predictions", str(reference_paths["F1-P1_capability"]),
    "--outputs-root", str(REPO / "outputs"),
    "--replicate", str(REPLICATE),
    "--kernel-start-epoch-seconds", str(KERNEL_START_EPOCH_SECONDS),
    "--execute",
    "--confirmation", "{CONFIRMATION}",
    "--approved-protocol-commit", APPROVED_COMMIT,
    "--approval-reference", APPROVAL_REFERENCE,
] + resume_args, cwd=REPO, env=environment)

summary_path = REPO / "outputs" / RUN_ID / "public_summary.json"
summary = json.loads(summary_path.read_text(encoding="utf-8"))
if summary.get("run_status") not in {{"complete", "incomplete_time_budget"}}:
    raise RuntimeError("diagnostic evaluator did not produce an accepted terminal state")
if summary.get("run_status") == "incomplete_time_budget":
    if summary.get("metrics_reported") is not False:
        raise RuntimeError("timed handoff must not report a partial metric")
    if summary.get("resume_requires_fresh_authorization") is not True:
        raise RuntimeError("timed handoff must require a fresh continuation GO")
print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
'''


def build_metadata(
    *,
    kernel_id: str,
    safety_dataset_source: str,
    f1_safety_kernel_source: str,
    f2_kernel_source: str,
    f3_kernel_source: str,
    resume_kernel_source: str | None = None,
) -> dict:
    for label, value in (
        ("kernel id", kernel_id),
        ("safety dataset source", safety_dataset_source),
        ("F1 safety kernel source", f1_safety_kernel_source),
        ("F2 kernel source", f2_kernel_source),
        ("F3 kernel source", f3_kernel_source),
    ):
        _validate_source(value, label)
    if resume_kernel_source is not None:
        _validate_source(resume_kernel_source, "resume kernel source")
    kernel_sources = [f1_safety_kernel_source, f2_kernel_source, f3_kernel_source]
    if resume_kernel_source is not None:
        kernel_sources.append(resume_kernel_source)
    return {
        "id": kernel_id,
        "title": kernel_id.split("/", 1)[1].replace("-", " ").title(),
        "code_file": WRAPPER_FILENAME,
        "language": "python",
        "kernel_type": "script",
        "is_private": True,
        "enable_gpu": True,
        "enable_internet": True,
        "machine_shape": "NvidiaTeslaP100",
        "docker_image_pinning_type": "original",
        "dataset_sources": [safety_dataset_source],
        "kernel_sources": kernel_sources,
        "competition_sources": [],
        "model_sources": [],
    }


def write_package(output_dir: Path, wrapper: str, metadata: dict) -> tuple[Path, Path]:
    if output_dir.exists():
        raise KernelPreparationError("output directory exists; refusing overwrite")
    output_dir.mkdir(parents=True)
    wrapper_path = output_dir / WRAPPER_FILENAME
    metadata_path = output_dir / METADATA_FILENAME
    wrapper_path.write_text(wrapper, encoding="utf-8", newline="\n")
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8", newline="\n")
    return wrapper_path, metadata_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-commit", required=True)
    parser.add_argument("--approval-reference", required=True)
    parser.add_argument("--kernel-id", required=True)
    parser.add_argument("--safety-dataset-source", required=True)
    parser.add_argument("--f1-safety-kernel-source", required=True)
    parser.add_argument("--f2-kernel-source", required=True)
    parser.add_argument("--f3-kernel-source", required=True)
    parser.add_argument("--replicate", type=int, default=1)
    parser.add_argument("--resume-kernel-source")
    parser.add_argument("--resume-summary-sha256")
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    wrapper = build_wrapper(
        approved_commit=args.approved_commit,
        approval_reference=args.approval_reference,
        replicate=args.replicate,
        resume_summary_sha256=args.resume_summary_sha256,
    )
    metadata = build_metadata(
        kernel_id=args.kernel_id,
        safety_dataset_source=args.safety_dataset_source,
        f1_safety_kernel_source=args.f1_safety_kernel_source,
        f2_kernel_source=args.f2_kernel_source,
        f3_kernel_source=args.f3_kernel_source,
        resume_kernel_source=args.resume_kernel_source,
    )
    if (args.resume_kernel_source is None) != (args.resume_summary_sha256 is None):
        raise KernelPreparationError(
            "resume kernel source and resume-summary SHA-256 must be supplied together"
        )
    if args.replicate == 1 and args.resume_kernel_source is not None:
        raise KernelPreparationError("replicate 1 cannot attach a resume kernel")
    if args.replicate > 1 and args.resume_kernel_source is None:
        raise KernelPreparationError("continuation requires a resume kernel source")
    wrapper_path, metadata_path = write_package(args.output_dir, wrapper, metadata)
    print(json.dumps({
        "wrapper": str(wrapper_path),
        "metadata": str(metadata_path),
        "approved_commit": args.approved_commit,
        "contains_corpus_text": False,
        "executed": False,
    }, indent=2))


if __name__ == "__main__":
    main()
