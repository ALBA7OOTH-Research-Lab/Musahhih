#!/usr/bin/env python3
"""Build one private, timeout-safe B2-P1 Kaggle kernel without executing it."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_prompt_baseline import (  # noqa: E402
    APPROVAL_PATTERN,
    FINAL_CONFIRMATION,
    FINAL_INPUT_SHA256,
    FINAL_MODEL_ID,
    FINAL_MODEL_REVISION,
)


COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
SOURCE_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9-]*")
RUN_ID = "B2-P1__gemma3-4b-it__nahw-passage__s3407__r01"
PRIVATE_INPUT_FILENAME = "nahw_gec_test.jsonl"
WRAPPER_FILENAME = "b2_final_evaluation.py"
METADATA_FILENAME = "kernel-metadata.json"


class KernelPreparationError(ValueError):
    """Raised before creating an unsafe or ambiguous kernel package."""


def _validate_source(value: str, *, label: str) -> None:
    if not SOURCE_PATTERN.fullmatch(value):
        raise KernelPreparationError(f"{label} must be owner/slug")


def build_wrapper(
    *,
    approved_commit: str,
    approval_reference: str,
    dataset_source: str,
) -> str:
    """Render one corpus-text-free B2 wrapper after strict activation checks."""

    if not COMMIT_PATTERN.fullmatch(approved_commit):
        raise KernelPreparationError("approved commit must be 40 lowercase hex")
    if not APPROVAL_PATTERN.fullmatch(approval_reference):
        raise KernelPreparationError(
            "approval reference must be a Musahhih issue-comment URL"
        )
    _validate_source(dataset_source, label="dataset source")
    dataset_mount = dataset_source.split("/", 1)[1]
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
EXPECTED_INPUT_SHA256 = "{FINAL_INPUT_SHA256}"
MODEL_ID = "{FINAL_MODEL_ID}"
MODEL_REVISION = "{FINAL_MODEL_REVISION}"
RUN_ID = "{RUN_ID}"
REPOSITORY = "https://github.com/ALBA7OOTH-Research-Lab/Musahhih.git"
WORKING = Path("/kaggle/working")
REPO = WORKING / "Musahhih"


def run(command, *, cwd=None, env=None, timeout=None):
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=True,
        timeout=timeout,
    )


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if REPO.exists():
    raise RuntimeError("repository path exists; refusing mutable state")
run(
    ["git", "clone", "--filter=blob:none", "--no-checkout", REPOSITORY, str(REPO)],
    timeout=120,
)
run(["git", "checkout", "--detach", APPROVED_COMMIT], cwd=REPO, timeout=60)
observed_commit = subprocess.run(
    ["git", "rev-parse", "HEAD"],
    cwd=REPO,
    check=True,
    capture_output=True,
    text=True,
    timeout=30,
).stdout.strip()
if observed_commit != APPROVED_COMMIT:
    raise RuntimeError("repository checkout differs from approved commit")
print({{"stage": "repository_gate", "git_commit": observed_commit, "passed": True}})

environment = dict(os.environ)
environment["UNSLOTH_COMPILE_DISABLE"] = "1"
run(
    [sys.executable, "-m", "scripts.check_b1_b2_restored_p100"],
    cwd=REPO,
    env=environment,
    timeout=800,
)

# Access only the frozen test input after the restored runtime passes. B2 uses
# no demonstration bundle, even though the attached private dataset also
# contains the separately frozen B1 bundle.
input_path = (
    Path("/kaggle/input")
    / "{dataset_mount}"
    / "{PRIVATE_INPUT_FILENAME}"
)
if not input_path.is_file() or sha256_file(input_path) != EXPECTED_INPUT_SHA256:
    raise RuntimeError("exact frozen final input was not attached")
print({{"stage": "private_input_gate", "input_hash_match": True, "passed": True}})

run(
    [
        sys.executable,
        "-m",
        "scripts.run_prompt_baseline",
        "--protocol-id",
        "B2-P1",
        "--model-slug",
        "gemma3-4b-it",
        "--model",
        MODEL_ID,
        "--model-revision",
        MODEL_REVISION,
        "--evaluation-slug",
        "nahw-passage",
        "--seed",
        "3407",
        "--replicate",
        "1",
        "--input",
        str(input_path),
        "--prompt-template",
        str(REPO / "docs" / "prompt_baseline_protocol.md"),
        "--outputs-root",
        str(REPO / "outputs"),
        "--confirm-final-eval",
        "--execute",
        "--kernel-start-epoch-seconds",
        str(KERNEL_START_EPOCH_SECONDS),
        "--confirmation",
        "{FINAL_CONFIRMATION}",
        "--approved-protocol-commit",
        APPROVED_COMMIT,
        "--approval-reference",
        APPROVAL_REFERENCE,
    ],
    cwd=REPO,
    env=environment,
)

summary_path = REPO / "outputs" / RUN_ID / "summary.json"
summary = json.loads(summary_path.read_text(encoding="utf-8"))
status = summary.get("run_status")
if status not in {{"complete", "incomplete_time_budget"}}:
    raise RuntimeError("B2-P1 evaluator did not produce an accepted terminal state")
if status == "incomplete_time_budget":
    if summary.get("metrics_reported") is not False:
        raise RuntimeError("timed handoff must not report a partial metric")
    if summary.get("resume_requires_fresh_authorization") is not True:
        raise RuntimeError("timed handoff must require a fresh continuation GO")
    completed_records = summary.get("completed_records")
else:
    completed_records = summary.get("counts", {{}}).get("completed_records")
print(
    {{
        "stage": "terminal_gate",
        "run_status": status,
        "completed_records": completed_records,
        "expected_records": 511,
        "passed": True,
    }}
)
'''


def build_metadata(*, kernel_id: str, dataset_source: str) -> dict:
    """Return private P100 metadata with exactly one reviewed data source."""

    _validate_source(kernel_id, label="kernel id")
    _validate_source(dataset_source, label="dataset source")
    title = kernel_id.split("/", 1)[1].replace("-", " ").title()
    return {
        "id": kernel_id,
        "title": title,
        "code_file": WRAPPER_FILENAME,
        "language": "python",
        "kernel_type": "script",
        "is_private": True,
        "enable_gpu": True,
        "enable_internet": True,
        "machine_shape": "NvidiaTeslaP100",
        "docker_image_pinning_type": "original",
        "dataset_sources": [dataset_source],
        "kernel_sources": [],
        "competition_sources": [],
        "model_sources": [],
    }


def write_kernel_package(
    *,
    output_dir: Path,
    wrapper: str,
    metadata: dict,
) -> tuple[Path, Path]:
    """Write a new ignored package without overwriting an earlier attempt."""

    if output_dir.exists():
        raise KernelPreparationError("output directory exists; refusing overwrite")
    output_dir.mkdir(parents=True)
    wrapper_path = output_dir / WRAPPER_FILENAME
    metadata_path = output_dir / METADATA_FILENAME
    wrapper_path.write_text(wrapper, encoding="utf-8", newline="\n")
    metadata_path.write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return wrapper_path, metadata_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-commit", required=True)
    parser.add_argument("--approval-reference", required=True)
    parser.add_argument("--kernel-id", required=True)
    parser.add_argument("--dataset-source", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    wrapper = build_wrapper(
        approved_commit=args.approved_commit,
        approval_reference=args.approval_reference,
        dataset_source=args.dataset_source,
    )
    metadata = build_metadata(
        kernel_id=args.kernel_id,
        dataset_source=args.dataset_source,
    )
    wrapper_path, metadata_path = write_kernel_package(
        output_dir=args.output_dir,
        wrapper=wrapper,
        metadata=metadata,
    )
    print(
        json.dumps(
            {
                "wrapper": str(wrapper_path),
                "metadata": str(metadata_path),
                "approved_commit": args.approved_commit,
                "kernel_id": args.kernel_id,
                "contains_corpus_text": False,
                "executed": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
