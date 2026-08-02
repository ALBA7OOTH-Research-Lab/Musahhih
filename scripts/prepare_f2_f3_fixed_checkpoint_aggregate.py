#!/usr/bin/env python3
"""Generate, but never submit, the issue #196 CPU aggregate Job."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.f2_f3_fixed_checkpoint_aggregate_utils import (
    CONFIRMATION,
    OUTPUT_ROOT,
    SELECTED_ATTEMPT_ID,
    SELECTED_COMMIT,
    SELECTED_ROOT,
    TRAINING_ROOT,
    validate_activation,
)
from scripts.f2_f3_nautilus_utils import NAMESPACE, PVC_NAME
from scripts.prepare_f2_f3_nautilus_jobs import PYTORCH_IMAGE, validate_pinned_image
from scripts.prepare_f2_f3_nautilus_multiseed_eval import _checkout


ISSUE_192_ROOT = "/private/evaluations/issue-192"
ISSUE_194_ROOT = "/private/evaluations/issue-194"


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
        "app.kubernetes.io/component": "f2-f3-fixed-checkpoint-aggregate",
        "musahhih.openai/issue": "196",
        "musahhih.openai/stage": "cpu-aggregate-audit",
    }
    command = f"""
set -euo pipefail
log_root=/private/logs/issue-196/aggregate
log_path="$log_root/attempt-{attempt}.log"
exit_path="$log_root/attempt-{attempt}.exit.json"
output_path={OUTPUT_ROOT}/aggregate/attempt-{attempt}.json
mkdir -p "$log_root"
test ! -e "$log_path"
test ! -e "$exit_path"
test ! -e "$output_path"
set +e
python -m scripts.aggregate_f2_f3_fixed_checkpoint_eval \
  --selected-root {SELECTED_ROOT} \
  --issue-192-root {ISSUE_192_ROOT} \
  --issue-194-root {ISSUE_194_ROOT} \
  --training-root {TRAINING_ROOT} \
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
            "name": f"musahhih-f2-f3-fixed-aggregate-a{attempt[-8:]}",
            "namespace": NAMESPACE,
            "labels": labels,
            "annotations": {
                "musahhih.openai/approved-commit": commit,
                "musahhih.openai/approval-reference": approval_reference,
                "musahhih.openai/selected-attempt-id": SELECTED_ATTEMPT_ID,
                "musahhih.openai/selected-evaluation-commit": SELECTED_COMMIT,
                "musahhih.openai/unselected-attempt-ids": "5157509573,5158062318",
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
                    "containers": [{
                        "name": "aggregate-audit",
                        "image": validate_pinned_image(PYTORCH_IMAGE),
                        "workingDir": "/repo",
                        "command": ["/bin/bash", "-lc", command],
                        "resources": {"requests": dict(resources), "limits": dict(resources)},
                        "volumeMounts": [
                            {"name": "repository", "mountPath": "/repo"},
                            {"name": "private", "mountPath": "/private"},
                        ],
                    }],
                    "volumes": [
                        {"name": "repository", "emptyDir": {}},
                        {"name": "private", "persistentVolumeClaim": {"claimName": PVC_NAME}},
                    ],
                },
            },
        },
    }


def build_manifest(*, commit: str, approval_reference: str, confirmation: str) -> dict:
    return {"apiVersion": "v1", "kind": "List", "items": [build_job(
        commit=commit,
        approval_reference=approval_reference,
        confirmation=confirmation,
    )]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-commit", required=True)
    parser.add_argument("--approval-reference", required=True)
    parser.add_argument("--confirmation", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    manifest = build_manifest(
        commit=args.approved_commit,
        approval_reference=args.approval_reference,
        confirmation=args.confirmation,
    )
    if args.output.exists():
        raise RuntimeError("manifest exists; refusing overwrite")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "stage": "cpu-aggregate-audit",
        "jobs": 1,
        "gpu": False,
        "unique_private_prediction_files": 20,
        "contains_corpus_text": False,
    }))


if __name__ == "__main__":
    main()
