#!/usr/bin/env python3
"""Generate, but never submit, reviewed issue #171 Nautilus manifests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from scripts.f1_eval_utils import (
    EXPECTED_TEST_RECORDS,
    EXPECTED_TEST_SHA256,
)
from scripts.f2_f3_multiseed_eval_utils import (
    AGGREGATE_CONFIRMATION,
    EVALUATION_CONFIRMATION,
    TEST_FILENAME,
    TEST_STAGING_CONFIRMATION,
    validate_activation,
)
from scripts.f2_f3_nautilus_utils import NAMESPACE, PVC_NAME, SEEDS, arm_order
from scripts.prepare_f2_f3_nautilus_jobs import (
    GIT_IMAGE,
    PYTORCH_IMAGE,
    REPOSITORY,
    validate_pinned_image,
)


ATTEMPT_PATTERN = re.compile(r"[1-9][0-9]*")


def _labels(stage: str, seed: int | None = None) -> dict:
    labels = {
        "app.kubernetes.io/name": "musahhih",
        "app.kubernetes.io/component": "f2-f3-multiseed-evaluation",
        "musahhih.openai/issue": "171",
        "musahhih.openai/stage": stage,
    }
    if seed is not None:
        labels["musahhih.openai/seed"] = str(seed)
    return labels


def _checkout(commit: str) -> dict:
    command = (
        'set -eu; git clone --filter=blob:none "$REPOSITORY" /repo; '
        'cd /repo; git checkout --detach "$MUSAHHIH_APPROVED_COMMIT"; '
        'test "$(git rev-parse HEAD)" = "$MUSAHHIH_APPROVED_COMMIT"; '
        'test -z "$(git status --porcelain)"'
    )
    return {
        "name": "immutable-checkout",
        "image": validate_pinned_image(GIT_IMAGE),
        "command": ["/bin/sh", "-c", command],
        "env": [
            {"name": "REPOSITORY", "value": REPOSITORY},
            {"name": "MUSAHHIH_APPROVED_COMMIT", "value": commit},
        ],
        "volumeMounts": [{"name": "repository", "mountPath": "/repo"}],
        "resources": {
            "requests": {"cpu": "100m", "memory": "128Mi"},
            "limits": {"cpu": "100m", "memory": "128Mi"},
        },
    }


def build_test_staging_pod(
    *, commit: str, approval_reference: str, confirmation: str
) -> dict:
    activation = validate_activation(
        stage="test-staging",
        seed=None,
        approved_commit=commit,
        actual_commit=commit,
        approval_reference=approval_reference,
        confirmation=confirmation,
    )
    attempt = activation["attempt_id"]
    upload = f"/private/staging-upload/issue-171/attempt-{attempt}"
    target = "/private/inputs/issue-171"
    command = f"""
set -eu
upload={json.dumps(upload)}
target={json.dumps(target)}
mkdir -p "$upload" /private/staging-upload/issue-171
test ! -e "$target"
test -z "$(ls -A "$upload")"
touch /tmp/staging-ready
while [ ! -f "$upload/READY" ]; do sleep 1; done
path="$upload/{TEST_FILENAME}"
test -f "$path"
test "$(sha256sum "$path" | awk '{{print $1}}')" = "{EXPECTED_TEST_SHA256}"
test "$(wc -l < "$path" | tr -d ' ')" = "{EXPECTED_TEST_RECORDS}"
test -z "$(find "$upload" -type f ! -name READY ! -name {TEST_FILENAME} -print -quit)"
mkdir "$target"
mv "$path" "$target/{TEST_FILENAME}"
rm "$upload/READY"
printf '%s\n' '{{"status":"complete","filename":"{TEST_FILENAME}","records":{EXPECTED_TEST_RECORDS},"sha256":"{EXPECTED_TEST_SHA256}","contains_corpus_text":false}}' > "$target/staging_manifest.json.tmp"
mv "$target/staging_manifest.json.tmp" "$target/staging_manifest.json"
sync
printf '%s\n' '{{"status":"complete","records":{EXPECTED_TEST_RECORDS},"contains_corpus_text":false}}'
""".strip()
    labels = _labels("test-staging")
    return {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": f"musahhih-f2-f3-eval-staging-a{attempt[-8:]}",
            "namespace": NAMESPACE,
            "labels": labels,
            "annotations": {
                "musahhih.openai/approved-commit": commit,
                "musahhih.openai/approval-reference": approval_reference,
                "musahhih.openai/attempt-id": attempt,
                "musahhih.openai/input-sha256": EXPECTED_TEST_SHA256,
            },
        },
        "spec": {
            "restartPolicy": "Never",
            "activeDeadlineSeconds": 86400,
            "containers": [
                {
                    "name": "test-staging",
                    "image": validate_pinned_image(GIT_IMAGE),
                    "command": ["/bin/sh", "-c", command],
                    "readinessProbe": {
                        "exec": {"command": ["test", "-f", "/tmp/staging-ready"]},
                        "periodSeconds": 1,
                    },
                    "resources": {
                        "requests": {"cpu": "100m", "memory": "128Mi"},
                        "limits": {"cpu": "100m", "memory": "128Mi"},
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


def _evaluation_command() -> str:
    return """
set -euo pipefail
kernel_start="$(date +%s)"
args=(
  --seed "$MUSAHHIH_SEED"
  --training-root /private/outputs/issue-155
  --test-input-root /private/inputs/issue-171
  --output-root /private/evaluations/issue-171
  --kernel-start-epoch-seconds "$kernel_start"
  --approved-commit "$MUSAHHIH_APPROVED_COMMIT"
  --approval-reference "$MUSAHHIH_APPROVAL_REFERENCE"
  --confirmation "$MUSAHHIH_CONFIRMATION"
)
if [[ -n "$MUSAHHIH_RESUME_ATTEMPT_ID" ]]; then
  args+=(--resume-root "/private/evaluations/issue-171/seed-$MUSAHHIH_SEED/attempts/$MUSAHHIH_RESUME_ATTEMPT_ID")
fi
log_root="/private/logs/issue-171/seed-$MUSAHHIH_SEED"
log_path="$log_root/attempt-$MUSAHHIH_ATTEMPT_ID.log"
exit_path="$log_root/attempt-$MUSAHHIH_ATTEMPT_ID.exit.json"
mkdir -p "$log_root"
test ! -e "$log_path"
test ! -e "$exit_path"
run_workflow() {
  python -m pip install --quiet --progress-bar off --requirement requirements-nautilus-f2-f3.txt || return "$?"
  python -m scripts.run_f2_f3_nautilus_multiseed_eval "${args[@]}"
}
set +e
run_workflow 2>&1 | tee "$log_path"
pipeline_status=("${PIPESTATUS[@]}")
workflow_status="${pipeline_status[0]}"
tee_status="${pipeline_status[1]}"
set -e
if [[ "$tee_status" -ne 0 ]]; then exit 90; fi
tmp="$exit_path.tmp.$$"
printf '{"exit_code":%s,"automatic_retry":false,"contains_corpus_text":false}\n' "$workflow_status" > "$tmp"
mv "$tmp" "$exit_path"
sync
exit "$workflow_status"
""".strip()


def build_evaluation_job(
    *,
    seed: int,
    commit: str,
    approval_reference: str,
    confirmation: str,
    resume_attempt_id: str | None,
) -> dict:
    activation = validate_activation(
        stage="paired-evaluation",
        seed=seed,
        approved_commit=commit,
        actual_commit=commit,
        approval_reference=approval_reference,
        confirmation=confirmation,
    )
    if resume_attempt_id is not None and not ATTEMPT_PATTERN.fullmatch(
        resume_attempt_id
    ):
        raise ValueError("resume attempt ID must contain only nonzero-leading digits")
    attempt = activation["attempt_id"]
    labels = _labels("paired-evaluation", seed)
    env = {
        "MUSAHHIH_SEED": str(seed),
        "MUSAHHIH_APPROVED_COMMIT": commit,
        "MUSAHHIH_APPROVAL_REFERENCE": approval_reference,
        "MUSAHHIH_CONFIRMATION": confirmation,
        "MUSAHHIH_ATTEMPT_ID": attempt,
        "MUSAHHIH_RESUME_ATTEMPT_ID": resume_attempt_id or "",
        "UNSLOTH_COMPILE_DISABLE": "1",
        "HF_HOME": "/private/cache/huggingface",
        "PIP_CACHE_DIR": "/private/cache/pip",
    }
    container_env = [{"name": key, "value": value} for key, value in env.items()]
    container_env.append(
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
    return {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": f"musahhih-f2-f3-eval-s{seed}-a{attempt[-8:]}",
            "namespace": NAMESPACE,
            "labels": labels,
            "annotations": {
                "musahhih.openai/approved-commit": commit,
                "musahhih.openai/approval-reference": approval_reference,
                "musahhih.openai/attempt-id": attempt,
                "musahhih.openai/arm-order": ",".join(arm_order(seed)),
                "musahhih.openai/resume-attempt-id": resume_attempt_id or "none",
            },
        },
        "spec": {
            "backoffLimit": 0,
            "activeDeadlineSeconds": 86400,
            "template": {
                "metadata": {"labels": labels},
                "spec": {
                    "restartPolicy": "Never",
                    "initContainers": [_checkout(commit)],
                    "containers": [
                        {
                            "name": "paired-evaluation",
                            "image": validate_pinned_image(PYTORCH_IMAGE),
                            "workingDir": "/repo",
                            "command": ["/bin/bash", "-lc", _evaluation_command()],
                            "env": container_env,
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


def build_aggregate_job(
    *,
    commit: str,
    approval_reference: str,
    confirmation: str,
    source_attempt_id: str,
    evaluation_commit: str,
) -> dict:
    activation = validate_activation(
        stage="aggregate-evaluation",
        seed=None,
        approved_commit=commit,
        actual_commit=commit,
        approval_reference=approval_reference,
        confirmation=confirmation,
    )
    if not ATTEMPT_PATTERN.fullmatch(source_attempt_id):
        raise ValueError("source attempt ID must contain only nonzero-leading digits")
    if not re.fullmatch(r"[0-9a-f]{40}", evaluation_commit):
        raise ValueError("evaluation commit must be lowercase 40-hex")
    attempt = activation["attempt_id"]
    labels = _labels("aggregate-evaluation")
    aggregate_command = " ".join(
        (
            "python -m scripts.aggregate_f2_f3_nautilus_multiseed_eval",
            "--evaluation-root /private/evaluations/issue-171",
            f"--source-attempt-id {source_attempt_id}",
            f"--evaluation-commit {evaluation_commit}",
            "--output-root /private/evaluations/issue-171",
            f"--approved-commit {commit}",
            f"--approval-reference {approval_reference}",
            f"--confirmation {AGGREGATE_CONFIRMATION}",
        )
    )
    command = f"""
set -euo pipefail
log_root=/private/logs/issue-171/aggregate
log_path="$log_root/attempt-{attempt}.log"
exit_path="$log_root/attempt-{attempt}.exit.json"
mkdir -p "$log_root"
test ! -e "$log_path"
test ! -e "$exit_path"
set +e
{aggregate_command} 2>&1 | tee "$log_path"
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
    return {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": f"musahhih-f2-f3-eval-aggregate-a{attempt[-8:]}",
            "namespace": NAMESPACE,
            "labels": labels,
            "annotations": {
                "musahhih.openai/approved-commit": commit,
                "musahhih.openai/approval-reference": approval_reference,
                "musahhih.openai/source-attempt-id": source_attempt_id,
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
                            "name": "aggregate-evaluation",
                            "image": validate_pinned_image(PYTORCH_IMAGE),
                            "workingDir": "/repo",
                            "command": ["/bin/bash", "-lc", command],
                            "resources": {
                                "requests": {"cpu": "1", "memory": "2Gi"},
                                "limits": {"cpu": "1", "memory": "2Gi"},
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


def build_manifest(
    *,
    stage: str,
    commit: str,
    approval_reference: str,
    confirmation: str,
    resume_attempt_id: str | None = None,
    source_attempt_id: str | None = None,
    evaluation_commit: str | None = None,
) -> dict:
    if stage == "test-staging":
        items = [
            build_test_staging_pod(
                commit=commit,
                approval_reference=approval_reference,
                confirmation=confirmation,
            )
        ]
    elif stage == "paired-evaluation":
        items = [
            build_evaluation_job(
                seed=seed,
                commit=commit,
                approval_reference=approval_reference,
                confirmation=confirmation,
                resume_attempt_id=resume_attempt_id,
            )
            for seed in SEEDS
        ]
    elif stage == "aggregate-evaluation":
        if source_attempt_id is None or evaluation_commit is None:
            raise ValueError("aggregate stage requires source attempt and commit")
        items = [
            build_aggregate_job(
                commit=commit,
                approval_reference=approval_reference,
                confirmation=confirmation,
                source_attempt_id=source_attempt_id,
                evaluation_commit=evaluation_commit,
            )
        ]
    else:
        raise ValueError("unsupported evaluation stage")
    return {"apiVersion": "v1", "kind": "List", "items": items}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage",
        required=True,
        choices=("test-staging", "paired-evaluation", "aggregate-evaluation"),
    )
    parser.add_argument("--approved-commit", required=True)
    parser.add_argument("--approval-reference", required=True)
    parser.add_argument("--confirmation", required=True)
    parser.add_argument("--resume-attempt-id")
    parser.add_argument("--source-attempt-id")
    parser.add_argument("--evaluation-commit")
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = build_manifest(
        stage=args.stage,
        commit=args.approved_commit,
        approval_reference=args.approval_reference,
        confirmation=args.confirmation,
        resume_attempt_id=args.resume_attempt_id,
        source_attempt_id=args.source_attempt_id,
        evaluation_commit=args.evaluation_commit,
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
