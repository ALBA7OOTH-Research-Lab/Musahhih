#!/usr/bin/env python3
"""Generate reviewed Nautilus Job manifests after an exact owner GO."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.f2_f3_nautilus_utils import (
    NAMESPACE,
    PVC_NAME,
    SEEDS,
    arm_order,
    validate_activation,
)


REPOSITORY = "https://github.com/ALBA7OOTH-Research-Lab/Musahhih.git"
PYTORCH_IMAGE = (
    "pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime@"
    "sha256:77f17f843507062875ce8be2a6f76aa6aa3df7f9ef1e31d9d7432f4b0f563dee"
)
GIT_IMAGE = (
    "alpine/git:2.47.2@"
    "sha256:062a01ad7a0eb17cff382bc5e26086b4d710e56dfdf001109a49b6d9bd378c"
)
PACKAGE_COMMAND = """
set -euo pipefail
python -m pip install --quiet --progress-bar off \
  --requirement requirements-nautilus-f2-f3.txt
runner_args=(
  --stage "$MUSAHHIH_STAGE"
  --approved-commit "$MUSAHHIH_APPROVED_COMMIT"
  --approval-reference "$MUSAHHIH_APPROVAL_REFERENCE"
  --confirmation "$MUSAHHIH_CONFIRMATION"
)
if [[ -n "$MUSAHHIH_SEED" ]]; then
  runner_args+=(--seed "$MUSAHHIH_SEED")
fi
if [[ -n "$MUSAHHIH_INPUT_ROOT" ]]; then
  runner_args+=(--input-root "$MUSAHHIH_INPUT_ROOT")
fi
if [[ -n "$MUSAHHIH_OUTPUT_ROOT" ]]; then
  runner_args+=(--output-root "$MUSAHHIH_OUTPUT_ROOT")
fi
python -m scripts.run_f2_f3_nautilus_pair "${runner_args[@]}"
""".strip()


def environment(
    *,
    stage: str,
    commit: str,
    approval_reference: str,
    confirmation: str,
    seed: int | None,
) -> list[dict]:
    values = {
        "MUSAHHIH_STAGE": stage,
        "MUSAHHIH_APPROVED_COMMIT": commit,
        "MUSAHHIH_APPROVAL_REFERENCE": approval_reference,
        "MUSAHHIH_CONFIRMATION": confirmation,
        "MUSAHHIH_SEED": "" if seed is None else str(seed),
        "MUSAHHIH_INPUT_ROOT": ("" if seed is None else "/private/inputs/f2-f3"),
        "MUSAHHIH_OUTPUT_ROOT": ("" if seed is None else "/private/outputs/issue-155"),
        "UNSLOTH_COMPILE_DISABLE": "1",
        "HF_HOME": (
            "/tmp/huggingface" if seed is None else "/private/cache/huggingface"
        ),
        "PIP_CACHE_DIR": ("/tmp/pip-cache" if seed is None else "/private/cache/pip"),
    }
    result = [{"name": key, "value": value} for key, value in values.items()]
    result.append(
        {
            "name": "HF_TOKEN",
            "valueFrom": {
                "secretKeyRef": {
                    "name": "musahhih-hf-token",
                    "key": "token",
                    "optional": True,
                }
            },
        }
    )
    return result


def build_job(
    *,
    stage: str,
    commit: str,
    approval_reference: str,
    confirmation: str,
    seed: int | None,
) -> dict:
    validate_activation(
        stage=stage,
        seed=seed,
        approved_commit=commit,
        actual_commit=commit,
        approval_reference=approval_reference,
        confirmation=confirmation,
    )
    suffix = "preflight" if seed is None else f"s{seed}"
    name = f"musahhih-f2-f3-{suffix}"
    labels = {
        "app.kubernetes.io/name": "musahhih",
        "app.kubernetes.io/component": "f2-f3-replication",
        "musahhih.openai/issue": "155",
        "musahhih.openai/stage": stage,
    }
    if seed is not None:
        labels["musahhih.openai/seed"] = str(seed)

    volumes = [{"name": "repository", "emptyDir": {}}]
    volume_mounts = [{"name": "repository", "mountPath": "/repo"}]
    if seed is not None:
        volumes.append(
            {
                "name": "private",
                "persistentVolumeClaim": {"claimName": PVC_NAME},
            }
        )
        volume_mounts.append({"name": "private", "mountPath": "/private"})

    clone_command = (
        'set -eu; git clone --filter=blob:none "$REPOSITORY" /repo; '
        'cd /repo; git checkout --detach "$MUSAHHIH_APPROVED_COMMIT"; '
        'test "$(git rev-parse HEAD)" = "$MUSAHHIH_APPROVED_COMMIT"; '
        'test -z "$(git status --porcelain)"'
    )
    pod_spec = {
        "restartPolicy": "Never",
        "initContainers": [
            {
                "name": "immutable-checkout",
                "image": GIT_IMAGE,
                "command": ["/bin/sh", "-c", clone_command],
                "env": [
                    {"name": "REPOSITORY", "value": REPOSITORY},
                    {"name": "MUSAHHIH_APPROVED_COMMIT", "value": commit},
                ],
                "volumeMounts": [{"name": "repository", "mountPath": "/repo"}],
                "resources": {
                    "requests": {
                        "cpu": "100m",
                        "memory": "128Mi",
                        "ephemeral-storage": "1Gi",
                    },
                    "limits": {
                        "cpu": "100m",
                        "memory": "128Mi",
                        "ephemeral-storage": "1Gi",
                    },
                },
            }
        ],
        "containers": [
            {
                "name": "paired-training",
                "image": PYTORCH_IMAGE,
                "imagePullPolicy": "IfNotPresent",
                "workingDir": "/repo",
                "command": ["/bin/bash", "-lc", PACKAGE_COMMAND],
                "env": environment(
                    stage=stage,
                    commit=commit,
                    approval_reference=approval_reference,
                    confirmation=confirmation,
                    seed=seed,
                ),
                "resources": {
                    "requests": {
                        "cpu": "8",
                        "memory": "32Gi",
                        "ephemeral-storage": "40Gi",
                        "nvidia.com/a100": "1",
                    },
                    "limits": {
                        "cpu": "8",
                        "memory": "32Gi",
                        "ephemeral-storage": "40Gi",
                        "nvidia.com/a100": "1",
                    },
                },
                "volumeMounts": volume_mounts,
            }
        ],
        "volumes": volumes,
    }
    return {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": name,
            "namespace": NAMESPACE,
            "labels": labels,
            "annotations": {
                "musahhih.openai/approved-commit": commit,
                "musahhih.openai/approval-reference": approval_reference,
                "musahhih.openai/arm-order": (
                    "none" if seed is None else ",".join(arm_order(seed))
                ),
            },
        },
        "spec": {
            "backoffLimit": 0,
            "activeDeadlineSeconds": 86400,
            "template": {"metadata": {"labels": labels}, "spec": pod_spec},
        },
    }


def build_pvc() -> dict:
    return {
        "apiVersion": "v1",
        "kind": "PersistentVolumeClaim",
        "metadata": {"name": PVC_NAME, "namespace": NAMESPACE},
        "spec": {
            "accessModes": ["ReadWriteMany"],
            "resources": {"requests": {"storage": "100Gi"}},
            "storageClassName": "cephfs",
        },
    }


def build_manifest(
    *,
    stage: str,
    commit: str,
    approval_reference: str,
    confirmation: str,
) -> dict:
    seeds = (None,) if stage == "a100-preflight" else SEEDS
    items = []
    if stage == "paired-training":
        items.append(build_pvc())
    items.extend(
        build_job(
            stage=stage,
            commit=commit,
            approval_reference=approval_reference,
            confirmation=confirmation,
            seed=seed,
        )
        for seed in seeds
    )
    return {"apiVersion": "v1", "kind": "List", "items": items}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage", required=True, choices=("a100-preflight", "paired-training")
    )
    parser.add_argument("--approved-commit", required=True)
    parser.add_argument("--approval-reference", required=True)
    parser.add_argument("--confirmation", required=True)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = build_manifest(
        stage=args.stage,
        commit=args.approved_commit,
        approval_reference=args.approval_reference,
        confirmation=args.confirmation,
    )
    if args.output.exists():
        raise RuntimeError("Manifest already exists; refusing to overwrite it")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "stage": args.stage,
                "objects": len(manifest["items"]),
                "contains_corpus_text": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
