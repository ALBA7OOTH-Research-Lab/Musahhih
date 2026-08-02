#!/usr/bin/env python3
"""Generate, but never submit, the issue #185 CPU aggregate Job."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.f2_f3_nautilus_utils import NAMESPACE, PVC_NAME
from scripts.f2_f3_rtx3090_aggregate_utils import (
    CONFIRMATION,
    EVALUATION_COMMIT,
    EVALUATION_ROOT,
    OUTPUT_ROOT,
    SOURCE_ATTEMPT_ID,
    validate_activation,
)
from scripts.prepare_f2_f3_nautilus_jobs import PYTORCH_IMAGE, validate_pinned_image
from scripts.prepare_f2_f3_nautilus_multiseed_eval import _checkout


def build_job(*, commit: str, approval_reference: str, confirmation: str) -> dict:
    activation = validate_activation(
        approved_commit=commit,
        actual_commit=commit,
        approval_reference=approval_reference,
        confirmation=confirmation,
    )
    attempt = activation["attempt_id"]
    labels = {
        "app.kubernetes.io/name": "musahhih",
        "app.kubernetes.io/component": "f2-f3-rtx3090-aggregate",
        "musahhih.openai/issue": "185",
        "musahhih.openai/stage": "cpu-aggregate-audit",
    }
    command = f"""
set -euo pipefail
log_root=/private/logs/issue-185/aggregate
log_path="$log_root/attempt-{attempt}.log"
exit_path="$log_root/attempt-{attempt}.exit.json"
output_path={OUTPUT_ROOT}/aggregate/attempt-{attempt}.json
mkdir -p "$log_root"
test ! -e "$log_path"
test ! -e "$exit_path"
test ! -e "$output_path"
set +e
python -m scripts.aggregate_f2_f3_rtx3090_eval \
  --evaluation-root {EVALUATION_ROOT} \
  --output-root {OUTPUT_ROOT} \
  --approved-commit {commit} \
  --approval-reference {approval_reference} \
  --confirmation {CONFIRMATION} 2>&1 | tee "$log_path"
pipeline_status=("${{PIPESTATUS[@]}}")
workflow_status="${{pipeline_status[0]}}"
tee_status="${{pipeline_status[1]}}"
set -e
if [[ "$tee_status" -ne 0 ]]; then exit 90; fi
tmp="$exit_path.tmp.$$"
printf '{{"exit_code":%s,"automatic_retry":false,"contains_corpus_text":false}}\n' "$workflow_status" > "$tmp"
mv "$tmp" "$exit_path"
sync
exit "$workflow_status"
""".strip()
    resources = {"cpu": "1", "memory": "2Gi", "ephemeral-storage": "1Gi"}
    return {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": f"musahhih-f2-f3-rtx3090-aggregate-a{attempt[-8:]}",
            "namespace": NAMESPACE,
            "labels": labels,
            "annotations": {
                "musahhih.openai/approved-commit": commit,
                "musahhih.openai/approval-reference": approval_reference,
                "musahhih.openai/source-attempt-id": SOURCE_ATTEMPT_ID,
                "musahhih.openai/evaluation-commit": EVALUATION_COMMIT,
                "musahhih.openai/gpu-used": "false",
            },
        },
        "spec": {
            "backoffLimit": 0,
            "activeDeadlineSeconds": 3600,
            "template": {
                "metadata": {"labels": labels},
                "spec": {
                    "restartPolicy": "Never",
                    "initContainers": [_checkout(commit)],
                    "containers": [
                        {
                            "name": "aggregate-audit",
                            "image": validate_pinned_image(PYTORCH_IMAGE),
                            "workingDir": "/repo",
                            "command": ["/bin/bash", "-lc", command],
                            "resources": {
                                "requests": dict(resources),
                                "limits": dict(resources),
                            },
                            "volumeMounts": [
                                {"name": "repository", "mountPath": "/repo"},
                                {"name": "private", "mountPath": "/private"},
                            ],
                        }
                    ],
                    "volumes": [
                        {"name": "repository", "emptyDir": {}},
                        {
                            "name": "private",
                            "persistentVolumeClaim": {"claimName": PVC_NAME},
                        },
                    ],
                },
            },
        },
    }


def build_manifest(*, commit: str, approval_reference: str, confirmation: str) -> dict:
    return {
        "apiVersion": "v1",
        "kind": "List",
        "items": [
            build_job(
                commit=commit,
                approval_reference=approval_reference,
                confirmation=confirmation,
            )
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-commit", required=True)
    parser.add_argument("--approval-reference", required=True)
    parser.add_argument("--confirmation", required=True)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = build_manifest(
        commit=args.approved_commit,
        approval_reference=args.approval_reference,
        confirmation=args.confirmation,
    )
    if args.output.exists():
        raise RuntimeError("manifest exists; refusing overwrite")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "stage": "cpu-aggregate-audit",
                "jobs": 1,
                "gpu": False,
                "source_attempt_id": SOURCE_ATTEMPT_ID,
                "evaluation_commit": EVALUATION_COMMIT,
                "contains_corpus_text": False,
            }
        )
    )


if __name__ == "__main__":
    main()
