#!/usr/bin/env python3
"""Generate, but never submit, issue #177 canary/continuation Jobs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from scripts.f2_f3_eval_concurrency_utils import (
    validate_concurrency_activation,
)
from scripts.f2_f3_nautilus_utils import NAMESPACE, PVC_NAME
from scripts.prepare_f2_f3_nautilus_jobs import PYTORCH_IMAGE, validate_pinned_image
from scripts.prepare_f2_f3_nautilus_multiseed_eval import _checkout


ATTEMPT_PATTERN = re.compile(r"[1-9][0-9]*")
A100_80GB_PRODUCTS = ("NVIDIA-A100-SXM4-80GB", "NVIDIA-A100-80GB-PCIe")


def _resources() -> dict:
    values = {
        "cpu": "8",
        "memory": "96Gi",
        "ephemeral-storage": "40Gi",
        "nvidia.com/a100": "1",
    }
    return {"requests": dict(values), "limits": dict(values)}


def _labels(stage: str) -> dict:
    return {
        "app.kubernetes.io/name": "musahhih",
        "app.kubernetes.io/component": "f2-f3-evaluation-concurrency",
        "musahhih.openai/issue": "177",
        "musahhih.openai/stage": stage,
    }


def _env(values: dict[str, str]) -> list[dict]:
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


def _pod_spec(*, commit: str, labels: dict, container: dict) -> dict:
    return {
        "metadata": {"labels": labels},
        "spec": {
            "restartPolicy": "Never",
            "affinity": {
                "nodeAffinity": {
                    "requiredDuringSchedulingIgnoredDuringExecution": {
                        "nodeSelectorTerms": [
                            {
                                "matchExpressions": [
                                    {
                                        "key": "nvidia.com/gpu.product",
                                        "operator": "In",
                                        "values": list(A100_80GB_PRODUCTS),
                                    }
                                ]
                            }
                        ]
                    }
                }
            },
            "initContainers": [_checkout(commit)],
            "containers": [container],
            "volumes": [
                {"name": "repository", "emptyDir": {}},
                {
                    "name": "private",
                    "persistentVolumeClaim": {"claimName": PVC_NAME},
                },
            ],
        },
    }


def _container(*, name: str, command: str, values: dict[str, str]) -> dict:
    return {
        "name": name,
        "image": validate_pinned_image(PYTORCH_IMAGE),
        "workingDir": "/repo",
        "command": ["/bin/bash", "-lc", command],
        "env": _env(
            {
                **values,
                "UNSLOTH_COMPILE_DISABLE": "1",
                "TOKENIZERS_PARALLELISM": "false",
                "OMP_NUM_THREADS": "1",
                "MKL_NUM_THREADS": "1",
                "HF_HOME": "/private/cache/huggingface",
                "PIP_CACHE_DIR": "/private/cache/pip",
            }
        ),
        "resources": _resources(),
        "volumeMounts": [
            {"name": "repository", "mountPath": "/repo"},
            {"name": "private", "mountPath": "/private"},
        ],
    }


def _job(*, name: str, labels: dict, commit: str, reference: str, attempt: str,
         container: dict, deadline: int, private_test_access: bool) -> dict:
    return {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": name,
            "namespace": NAMESPACE,
            "labels": labels,
            "annotations": {
                "musahhih.openai/approved-commit": commit,
                "musahhih.openai/approval-reference": reference,
                "musahhih.openai/attempt-id": attempt,
                "musahhih.openai/private-test-access": str(private_test_access).lower(),
            },
        },
        "spec": {
            "backoffLimit": 0,
            "activeDeadlineSeconds": deadline,
            "template": _pod_spec(commit=commit, labels=labels, container=container),
        },
    }


def build_canary_job(*, commit: str, approval_reference: str, confirmation: str) -> dict:
    activation = validate_concurrency_activation(
        stage="concurrency-canary",
        seed=None,
        approved_commit=commit,
        actual_commit=commit,
        approval_reference=approval_reference,
        confirmation=confirmation,
    )
    attempt = activation["attempt_id"]
    command = """
set -euo pipefail
log_root=/private/logs/issue-177/canary
log_path="$log_root/attempt-$MUSAHHIH_ATTEMPT_ID.log"
exit_path="$log_root/attempt-$MUSAHHIH_ATTEMPT_ID.exit.json"
mkdir -p "$log_root"
test ! -e "$log_path"
test ! -e "$exit_path"
set +e
(
  python -m pip install --quiet --progress-bar off --requirement requirements-nautilus-f2-f3.txt &&
  timeout --signal=TERM --kill-after=30s 5400s \
    python -m scripts.run_f2_f3_nautilus_eval_concurrency_canary \
      --training-root /private/outputs/issue-155 \
      --output-root /private/canaries/issue-177 \
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
    labels = _labels("concurrency-canary")
    container = _container(
        name="concurrency-canary",
        command=command,
        values={
            "MUSAHHIH_APPROVED_COMMIT": commit,
            "MUSAHHIH_APPROVAL_REFERENCE": approval_reference,
            "MUSAHHIH_CONFIRMATION": confirmation,
            "MUSAHHIH_ATTEMPT_ID": attempt,
        },
    )
    return _job(
        name=f"musahhih-f2-f3-concurrency-canary-a{attempt[-8:]}",
        labels=labels,
        commit=commit,
        reference=approval_reference,
        attempt=attempt,
        container=container,
        deadline=6_000,
        private_test_access=False,
    )


def build_continuation_job(
    *, commit: str, approval_reference: str, confirmation: str,
    canary_attempt_id: str
) -> dict:
    activation = validate_concurrency_activation(
        stage="continuation",
        seed=3407,
        approved_commit=commit,
        actual_commit=commit,
        approval_reference=approval_reference,
        confirmation=confirmation,
    )
    if not ATTEMPT_PATTERN.fullmatch(canary_attempt_id):
        raise ValueError("canary attempt ID must contain nonzero-leading digits")
    attempt = activation["attempt_id"]
    command = """
set -euo pipefail
log_root=/private/logs/issue-177/continuation
log_path="$log_root/attempt-$MUSAHHIH_ATTEMPT_ID.log"
exit_path="$log_root/attempt-$MUSAHHIH_ATTEMPT_ID.exit.json"
mkdir -p "$log_root"
test ! -e "$log_path"
test ! -e "$exit_path"
set +e
(
  python -m pip install --quiet --progress-bar off --requirement requirements-nautilus-f2-f3.txt &&
  timeout --signal=TERM --kill-after=30s 23400s \
    python -m scripts.supervise_f2_f3_nautilus_eval_concurrency \
      --training-root /private/outputs/issue-155 \
      --test-input-root /private/inputs/issue-171 \
      --output-root /private/evaluations/issue-171 \
      --coordinator-root /private/evaluations/issue-177 \
      --canary-root "/private/canaries/issue-177/attempt-$MUSAHHIH_CANARY_ATTEMPT_ID" \
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
    labels = _labels("continuation")
    container = _container(
        name="continuation",
        command=command,
        values={
            "MUSAHHIH_APPROVED_COMMIT": commit,
            "MUSAHHIH_APPROVAL_REFERENCE": approval_reference,
            "MUSAHHIH_CONFIRMATION": confirmation,
            "MUSAHHIH_ATTEMPT_ID": attempt,
            "MUSAHHIH_CANARY_ATTEMPT_ID": canary_attempt_id,
        },
    )
    return _job(
        name=f"musahhih-f2-f3-eval-resume-a{attempt[-8:]}",
        labels=labels,
        commit=commit,
        reference=approval_reference,
        attempt=attempt,
        container=container,
        deadline=25_200,
        private_test_access=True,
    )


def build_manifest(
    *, stage: str, commit: str, approval_reference: str, confirmation: str,
    canary_attempt_id: str | None = None
) -> dict:
    if stage == "concurrency-canary":
        item = build_canary_job(
            commit=commit,
            approval_reference=approval_reference,
            confirmation=confirmation,
        )
    elif stage == "continuation":
        if canary_attempt_id is None:
            raise ValueError("continuation requires the passing canary attempt")
        item = build_continuation_job(
            commit=commit,
            approval_reference=approval_reference,
            confirmation=confirmation,
            canary_attempt_id=canary_attempt_id,
        )
    else:
        raise ValueError("unsupported concurrency stage")
    return {"apiVersion": "v1", "kind": "List", "items": [item]}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage", required=True, choices=("concurrency-canary", "continuation")
    )
    parser.add_argument("--approved-commit", required=True)
    parser.add_argument("--approval-reference", required=True)
    parser.add_argument("--confirmation", required=True)
    parser.add_argument("--canary-attempt-id")
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = build_manifest(
        stage=args.stage,
        commit=args.approved_commit,
        approval_reference=args.approval_reference,
        confirmation=args.confirmation,
        canary_attempt_id=args.canary_attempt_id,
    )
    if args.output.exists():
        raise RuntimeError("manifest exists; refusing overwrite")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"stage": args.stage, "objects": 1, "contains_corpus_text": False}))


if __name__ == "__main__":
    main()
