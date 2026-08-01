#!/usr/bin/env python3
"""Generate, but never submit, issue #173 canary/continuation manifests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from scripts.f2_f3_eval_repair_utils import (
    CANARY_CONFIRMATION,
    CONTINUATION_CONFIRMATION,
    SOURCE_ATTEMPT_ID,
    SOURCE_EVALUATION_COMMIT,
    validate_repair_activation,
)
from scripts.f2_f3_nautilus_utils import NAMESPACE, PVC_NAME
from scripts.prepare_f2_f3_nautilus_jobs import PYTORCH_IMAGE, validate_pinned_image
from scripts.prepare_f2_f3_nautilus_multiseed_eval import _checkout


LANES = {"a": (3407, 3409, 3411), "b": (3408, 3410)}
ATTEMPT_PATTERN = re.compile(r"[1-9][0-9]*")


def _labels(stage: str, lane: str | None = None) -> dict:
    labels = {
        "app.kubernetes.io/name": "musahhih",
        "app.kubernetes.io/component": "f2-f3-evaluation-repair",
        "musahhih.openai/issue": "173",
        "musahhih.openai/stage": stage,
    }
    if lane is not None:
        labels["musahhih.openai/lane"] = lane
    return labels


def _secret_env(values: dict[str, str]) -> list[dict]:
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


def _resources() -> dict:
    values = {
        "cpu": "2",
        "memory": "64Gi",
        "ephemeral-storage": "40Gi",
        "nvidia.com/a100": "1",
    }
    return {"requests": dict(values), "limits": dict(values)}


def _pod_spec(*, commit: str, labels: dict, container: dict) -> dict:
    return {
        "metadata": {"labels": labels},
        "spec": {
            "restartPolicy": "Never",
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


def _mounts() -> list[dict]:
    return [
        {"name": "repository", "mountPath": "/repo"},
        {"name": "private", "mountPath": "/private"},
    ]


def build_canary_job(
    *, commit: str, approval_reference: str, confirmation: str
) -> dict:
    activation = validate_repair_activation(
        stage="utilization-canary",
        seed=None,
        approved_commit=commit,
        actual_commit=commit,
        approval_reference=approval_reference,
        confirmation=confirmation,
    )
    attempt = activation["attempt_id"]
    labels = _labels("utilization-canary")
    command = """
set -euo pipefail
log_root=/private/logs/issue-173/canary
log_path="$log_root/attempt-$MUSAHHIH_ATTEMPT_ID.log"
exit_path="$log_root/attempt-$MUSAHHIH_ATTEMPT_ID.exit.json"
mkdir -p "$log_root"
test ! -e "$log_path"
test ! -e "$exit_path"
set +e
(
  python -m pip install --quiet --progress-bar off --requirement requirements-nautilus-f2-f3.txt &&
  timeout --signal=TERM --kill-after=30s 4200s \
    python -m scripts.run_f2_f3_nautilus_eval_repair_canary \
      --training-root /private/outputs/issue-155 \
      --output-root /private/canaries/issue-173 \
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
    container = {
        "name": "utilization-canary",
        "image": validate_pinned_image(PYTORCH_IMAGE),
        "workingDir": "/repo",
        "command": ["/bin/bash", "-lc", command],
        "env": _secret_env(
            {
                "MUSAHHIH_APPROVED_COMMIT": commit,
                "MUSAHHIH_APPROVAL_REFERENCE": approval_reference,
                "MUSAHHIH_CONFIRMATION": confirmation,
                "MUSAHHIH_ATTEMPT_ID": attempt,
                "UNSLOTH_COMPILE_DISABLE": "1",
                "HF_HOME": "/private/cache/huggingface",
                "PIP_CACHE_DIR": "/private/cache/pip",
            }
        ),
        "resources": _resources(),
        "volumeMounts": _mounts(),
    }
    return {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": f"musahhih-f2-f3-eval-canary-a{attempt[-8:]}",
            "namespace": NAMESPACE,
            "labels": labels,
            "annotations": {
                "musahhih.openai/approved-commit": commit,
                "musahhih.openai/approval-reference": approval_reference,
                "musahhih.openai/attempt-id": attempt,
                "musahhih.openai/private-test-access": "false",
            },
        },
        "spec": {
            "backoffLimit": 0,
            "activeDeadlineSeconds": 4500,
            "template": _pod_spec(commit=commit, labels=labels, container=container),
        },
    }


def build_continuation_job(
    *,
    lane: str,
    commit: str,
    approval_reference: str,
    confirmation: str,
    canary_attempt_id: str,
) -> dict:
    activation = validate_repair_activation(
        stage="continuation",
        seed=LANES[lane][0],
        approved_commit=commit,
        actual_commit=commit,
        approval_reference=approval_reference,
        confirmation=confirmation,
    )
    if not ATTEMPT_PATTERN.fullmatch(canary_attempt_id):
        raise ValueError("canary attempt ID must contain nonzero-leading digits")
    attempt = activation["attempt_id"]
    labels = _labels("continuation", lane)
    command = """
set -euo pipefail
log_root="/private/logs/issue-173/continuation/lane-$MUSAHHIH_LANE"
log_path="$log_root/attempt-$MUSAHHIH_ATTEMPT_ID.log"
exit_path="$log_root/attempt-$MUSAHHIH_ATTEMPT_ID.exit.json"
mkdir -p "$log_root"
test ! -e "$log_path"
test ! -e "$exit_path"
set +e
(
  python -m pip install --quiet --progress-bar off --requirement requirements-nautilus-f2-f3.txt || exit "$?"
  for seed in $MUSAHHIH_SEEDS; do
    python -m scripts.supervise_f2_f3_nautilus_eval_repair \
      --seed "$seed" \
      --training-root /private/outputs/issue-155 \
      --test-input-root /private/inputs/issue-171 \
      --output-root /private/evaluations/issue-171 \
      --canary-root "/private/canaries/issue-173/attempt-$MUSAHHIH_CANARY_ATTEMPT_ID" \
      --source-attempt-id "$MUSAHHIH_SOURCE_ATTEMPT_ID" \
      --source-commit "$MUSAHHIH_SOURCE_COMMIT" \
      --approved-commit "$MUSAHHIH_APPROVED_COMMIT" \
      --approval-reference "$MUSAHHIH_APPROVAL_REFERENCE" \
      --confirmation "$MUSAHHIH_CONFIRMATION" || exit "$?"
  done
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
    container = {
        "name": "continuation",
        "image": validate_pinned_image(PYTORCH_IMAGE),
        "workingDir": "/repo",
        "command": ["/bin/bash", "-lc", command],
        "env": _secret_env(
            {
                "MUSAHHIH_LANE": lane,
                "MUSAHHIH_SEEDS": " ".join(str(seed) for seed in LANES[lane]),
                "MUSAHHIH_APPROVED_COMMIT": commit,
                "MUSAHHIH_APPROVAL_REFERENCE": approval_reference,
                "MUSAHHIH_CONFIRMATION": confirmation,
                "MUSAHHIH_ATTEMPT_ID": attempt,
                "MUSAHHIH_CANARY_ATTEMPT_ID": canary_attempt_id,
                "MUSAHHIH_SOURCE_ATTEMPT_ID": SOURCE_ATTEMPT_ID,
                "MUSAHHIH_SOURCE_COMMIT": SOURCE_EVALUATION_COMMIT,
                "UNSLOTH_COMPILE_DISABLE": "1",
                "HF_HOME": "/private/cache/huggingface",
                "PIP_CACHE_DIR": "/private/cache/pip",
            }
        ),
        "resources": _resources(),
        "volumeMounts": _mounts(),
    }
    return {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": f"musahhih-f2-f3-eval-resume-{lane}-a{attempt[-8:]}",
            "namespace": NAMESPACE,
            "labels": labels,
            "annotations": {
                "musahhih.openai/approved-commit": commit,
                "musahhih.openai/approval-reference": approval_reference,
                "musahhih.openai/attempt-id": attempt,
                "musahhih.openai/source-attempt-id": SOURCE_ATTEMPT_ID,
                "musahhih.openai/canary-attempt-id": canary_attempt_id,
                "musahhih.openai/seeds": ",".join(str(seed) for seed in LANES[lane]),
            },
        },
        "spec": {
            "backoffLimit": 0,
            "activeDeadlineSeconds": 75_600,
            "template": _pod_spec(commit=commit, labels=labels, container=container),
        },
    }


def build_manifest(
    *,
    stage: str,
    commit: str,
    approval_reference: str,
    confirmation: str,
    canary_attempt_id: str | None = None,
) -> dict:
    if stage == "utilization-canary":
        items = [
            build_canary_job(
                commit=commit,
                approval_reference=approval_reference,
                confirmation=confirmation,
            )
        ]
    elif stage == "continuation":
        if canary_attempt_id is None:
            raise ValueError("continuation requires the passing canary attempt")
        items = [
            build_continuation_job(
                lane=lane,
                commit=commit,
                approval_reference=approval_reference,
                confirmation=confirmation,
                canary_attempt_id=canary_attempt_id,
            )
            for lane in LANES
        ]
    else:
        raise ValueError("unsupported repair stage")
    return {"apiVersion": "v1", "kind": "List", "items": items}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage", required=True, choices=("utilization-canary", "continuation")
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
    print(
        json.dumps(
            {
                "stage": args.stage,
                "objects": len(manifest["items"]),
                "output": str(args.output),
                "contains_corpus_text": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
