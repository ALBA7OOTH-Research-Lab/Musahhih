#!/usr/bin/env python3
"""Generate, but never submit, the two issue #194 replacement Jobs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.f2_f3_fixed_checkpoint_repair_utils import (
    CONFIRMATION,
    FAILED_SEEDS,
    GPU_PRODUCT,
    JOB_DEADLINE_SECONDS,
    OUTPUT_ROOT,
    SOURCE_ATTEMPT_ID,
    SOURCE_COMMIT,
    SOURCE_JOBS,
    validate_activation,
)
from scripts.f2_f3_nautilus_utils import NAMESPACE, PVC_NAME
from scripts.prepare_f2_f3_nautilus_jobs import PYTORCH_IMAGE, validate_pinned_image
from scripts.prepare_f2_f3_nautilus_multiseed_eval import _checkout


def _command() -> str:
    return """
set -euo pipefail
kernel_start="$(date +%s)"
log_root="/private/logs/issue-194/seed-$MUSAHHIH_SEED"
log_path="$log_root/attempt-$MUSAHHIH_ATTEMPT_ID.log"
exit_path="$log_root/attempt-$MUSAHHIH_ATTEMPT_ID.exit.json"
mkdir -p "$log_root"
test ! -e "$log_path"
test ! -e "$exit_path"
set +e
(
  python -m pip install --quiet --progress-bar off --requirement requirements-nautilus-f2-f3.txt || exit "$?"
  python -m scripts.supervise_f2_f3_fixed_checkpoint_repair \
    --seed "$MUSAHHIH_SEED" \
    --training-root /private/outputs/issue-155 \
    --test-input-root /private/inputs/issue-171 \
    --output-root /private/evaluations/issue-194 \
    --kernel-start-epoch-seconds "$kernel_start" \
    --approved-commit "$MUSAHHIH_APPROVED_COMMIT" \
    --approval-reference "$MUSAHHIH_APPROVAL_REFERENCE" \
    --confirmation "$MUSAHHIH_CONFIRMATION"
) 2>&1 | tee "$log_path"
pipeline_status=("${PIPESTATUS[@]}")
status="${pipeline_status[0]}"
tee_status="${pipeline_status[1]}"
set -e
if [[ "$tee_status" -ne 0 ]]; then exit 90; fi
tmp="$exit_path.tmp.$$"
printf '{"exit_code":%s,"automatic_retry":false,"contains_corpus_text":false}\n' "$status" > "$tmp"
mv "$tmp" "$exit_path"
sync
exit "$status"
""".strip()


def build_job(*, seed: int, commit: str, approval_reference: str) -> dict:
    activation = validate_activation(
        seed=seed,
        approved_commit=commit,
        actual_commit=commit,
        approval_reference=approval_reference,
        confirmation=CONFIRMATION,
    )
    attempt = activation["attempt_id"]
    labels = {
        "app.kubernetes.io/name": "musahhih",
        "app.kubernetes.io/component": "f2-f3-fixed-checkpoint-repair",
        "musahhih.openai/issue": "194",
        "musahhih.openai/seed": str(seed),
    }
    values = {
        "MUSAHHIH_SEED": str(seed),
        "MUSAHHIH_APPROVED_COMMIT": commit,
        "MUSAHHIH_APPROVAL_REFERENCE": approval_reference,
        "MUSAHHIH_CONFIRMATION": CONFIRMATION,
        "MUSAHHIH_ATTEMPT_ID": attempt,
        "UNSLOTH_COMPILE_DISABLE": "1",
        "TOKENIZERS_PARALLELISM": "false",
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "HF_HOME": "/private/cache/huggingface",
        "PIP_CACHE_DIR": "/private/cache/pip",
    }
    env = [{"name": key, "value": value} for key, value in values.items()]
    env.append({
        "name": "HF_TOKEN",
        "valueFrom": {"secretKeyRef": {
            "name": "musahhih-hf-token", "key": "token", "optional": True,
        }},
    })
    resources = {
        "cpu": "4", "memory": "32Gi", "ephemeral-storage": "20Gi",
        "nvidia.com/gpu": "1",
    }
    return {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": f"musahhih-f2-f3-fixed-repair-s{seed}-a{attempt[-8:]}",
            "namespace": NAMESPACE,
            "labels": labels,
            "annotations": {
                "musahhih.openai/approved-commit": commit,
                "musahhih.openai/approval-reference": approval_reference,
                "musahhih.openai/attempt-id": attempt,
                "musahhih.openai/source-commit": SOURCE_COMMIT,
                "musahhih.openai/source-attempt-id": SOURCE_ATTEMPT_ID,
                "musahhih.openai/source-job": SOURCE_JOBS[seed],
                "musahhih.openai/fresh-from-record-zero": "true",
                "musahhih.openai/private-test-access": "true",
                "musahhih.openai/training": "false",
                "musahhih.openai/checkpoints": "unselected-retained-epoch-only",
            },
        },
        "spec": {
            "backoffLimit": 0,
            "activeDeadlineSeconds": JOB_DEADLINE_SECONDS,
            "template": {
                "metadata": {"labels": labels},
                "spec": {
                    "restartPolicy": "Never",
                    "affinity": {"nodeAffinity": {
                        "requiredDuringSchedulingIgnoredDuringExecution": {
                            "nodeSelectorTerms": [{"matchExpressions": [{
                                "key": "nvidia.com/gpu.product",
                                "operator": "In", "values": [GPU_PRODUCT],
                            }]}]
                        }
                    }},
                    "initContainers": [_checkout(commit)],
                    "containers": [{
                        "name": "fixed-checkpoint-repair",
                        "image": validate_pinned_image(PYTORCH_IMAGE),
                        "workingDir": "/repo",
                        "command": ["/bin/bash", "-lc", _command()],
                        "env": env,
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


def build_manifest(*, commit: str, approval_reference: str) -> dict:
    return {"apiVersion": "v1", "kind": "List", "items": [
        build_job(seed=seed, commit=commit, approval_reference=approval_reference)
        for seed in FAILED_SEEDS
    ]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-commit", required=True)
    parser.add_argument("--approval-reference", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    manifest = build_manifest(
        commit=args.approved_commit, approval_reference=args.approval_reference
    )
    if args.output.exists():
        raise RuntimeError("manifest exists; refusing overwrite")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "stage": "fixed-checkpoint-batch-stability-repair",
        "jobs": len(manifest["items"]),
        "seeds": list(FAILED_SEEDS),
        "training_executed": False,
        "output_root": OUTPUT_ROOT,
        "contains_corpus_text": False,
    }))


if __name__ == "__main__":
    main()
