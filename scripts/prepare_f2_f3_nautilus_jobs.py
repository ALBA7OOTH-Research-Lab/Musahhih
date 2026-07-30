#!/usr/bin/env python3
"""Generate reviewed Nautilus Job manifests after an exact owner GO."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from scripts.f2_f3_nautilus_utils import (
    INPUT_FILENAMES,
    NAMESPACE,
    PVC_NAME,
    SEEDS,
    arm_order,
    validate_activation,
)


REPOSITORY = "https://github.com/ALBA7OOTH-Research-Lab/Musahhih.git"
PYTORCH_IMAGE = (
    "pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel@"
    "sha256:0cf3402e946b7c384ba943ee05c90b4c5a4a05227923921f2b0918c011cfaf56"
)
GIT_IMAGE = (
    "alpine/git:2.47.2@"
    "sha256:0d9a3a551058dba37ea77757955d3e834442ccf8540783671cc25c0d97957894"
)
PINNED_IMAGE_PATTERN = re.compile(r"^[^@\s]+@sha256:[0-9a-f]{64}$")
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


def validate_pinned_image(image: str) -> str:
    """Reject tags and malformed digests before emitting a cluster manifest."""
    if not PINNED_IMAGE_PATTERN.fullmatch(image):
        raise ValueError(f"image must use a full lowercase sha256 pin: {image!r}")
    return image


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
    validate_pinned_image(GIT_IMAGE)
    validate_pinned_image(PYTORCH_IMAGE)
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


def build_staging_pod(
    *,
    commit: str,
    approval_reference: str,
    confirmation: str,
) -> dict:
    validate_pinned_image(GIT_IMAGE)
    validate_activation(
        stage="private-staging",
        seed=None,
        approved_commit=commit,
        actual_commit=commit,
        approval_reference=approval_reference,
        confirmation=confirmation,
    )
    expected = {
        "f2_train_records.jsonl": (
            "bbc48dcf78ddff1830661ad749fcc8f9fbfce8206f4f09cd9f4d6501823201d2",
            2000,
        ),
        "f3_train_records.jsonl": (
            "d16decebe559e9a25da41ef59f63ca95e339972e22b9659dfc763e071fbc1546",
            2000,
        ),
        "common_dev_records.jsonl": (
            "adfdeb0c2e5730357226ce4e5156c300679629142ea0576d32dea9ac3050a950",
            975,
        ),
    }
    verification_lines = []
    for name, (digest, count) in expected.items():
        verification_lines.extend(
            (
                f'verify "/private/staging-upload/{name}" "{digest}" "{count}"',
                f'mv "/private/staging-upload/{name}" '
                f'"/private/inputs/f2-f3/{name}"',
            )
        )
    verification = "\n".join(verification_lines)
    command = f"""
set -eu
mkdir -p /private/staging-upload /private/inputs/f2-f3
mkdir -p /private/outputs/issue-155 /private/cache/huggingface /private/cache/pip
test -z "$(ls -A /private/staging-upload)"
test -z "$(ls -A /private/inputs/f2-f3)"
touch /tmp/staging-ready
while [ ! -f /private/staging-upload/READY ]; do sleep 1; done
verify() {{
  path="$1"
  expected_hash="$2"
  expected_count="$3"
  test -f "$path"
  actual_hash="$(sha256sum "$path" | awk '{{print $1}}')"
  actual_count="$(wc -l < "$path" | tr -d ' ')"
  test "$actual_hash" = "$expected_hash"
  test "$actual_count" = "$expected_count"
}}
{verification}
test -z "$(find /private/staging-upload -type f ! -name READY -print -quit)"
rm /private/staging-upload/READY
printf '%s\n' '{{"status":"complete","records":{{"f2":2000,"f3":2000,"development":975}},"contains_corpus_text":false}}' > /private/inputs/f2-f3/staging_manifest.json.tmp
mv /private/inputs/f2-f3/staging_manifest.json.tmp /private/inputs/f2-f3/staging_manifest.json
sync
printf '%s\n' '{{"status":"complete","contains_corpus_text":false}}'
""".strip()
    labels = {
        "app.kubernetes.io/name": "musahhih",
        "app.kubernetes.io/component": "f2-f3-private-staging",
        "musahhih.openai/issue": "163",
        "musahhih.openai/stage": "private-staging",
    }
    return {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": "musahhih-f2-f3-staging",
            "namespace": NAMESPACE,
            "labels": labels,
            "annotations": {
                "musahhih.openai/approved-commit": commit,
                "musahhih.openai/approval-reference": approval_reference,
                "musahhih.openai/input-filenames": ",".join(INPUT_FILENAMES),
            },
        },
        "spec": {
            "restartPolicy": "Never",
            "activeDeadlineSeconds": 86400,
            "containers": [
                {
                    "name": "private-staging",
                    "image": GIT_IMAGE,
                    "command": ["/bin/sh", "-c", command],
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
                    "readinessProbe": {
                        "exec": {"command": ["test", "-f", "/tmp/staging-ready"]},
                        "periodSeconds": 1,
                    },
                    "volumeMounts": [{"name": "private", "mountPath": "/private"}],
                }
            ],
            "volumes": [
                {
                    "name": "private",
                    "persistentVolumeClaim": {"claimName": PVC_NAME},
                }
            ],
        },
    }


def build_manifest(
    *,
    stage: str,
    commit: str,
    approval_reference: str,
    confirmation: str,
) -> dict:
    if stage == "private-staging":
        return {
            "apiVersion": "v1",
            "kind": "List",
            "items": [
                build_pvc(),
                build_staging_pod(
                    commit=commit,
                    approval_reference=approval_reference,
                    confirmation=confirmation,
                ),
            ],
        }
    seeds = (None,) if stage == "a100-preflight" else SEEDS
    items = list(
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
        "--stage",
        required=True,
        choices=("a100-preflight", "private-staging", "paired-training"),
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
