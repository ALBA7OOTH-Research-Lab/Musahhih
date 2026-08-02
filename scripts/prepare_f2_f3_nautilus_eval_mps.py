#!/usr/bin/env python3
"""Generate, but never submit, the issue #179 NVIDIA MPS canary Job."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.f2_f3_eval_mps_utils import validate_mps_activation
from scripts.f2_f3_nautilus_utils import NAMESPACE
from scripts.prepare_f2_f3_nautilus_eval_concurrency import (
    _container,
    _job,
    _labels as _old_labels,
)


def _labels() -> dict:
    labels = _old_labels("mps-canary")
    labels["musahhih.openai/issue"] = "179"
    return labels


def build_mps_canary_job(
    *, commit: str, approval_reference: str, confirmation: str
) -> dict:
    activation = validate_mps_activation(
        approved_commit=commit,
        actual_commit=commit,
        approval_reference=approval_reference,
        confirmation=confirmation,
    )
    attempt = activation["attempt_id"]
    command = """
set -euo pipefail
log_root=/private/logs/issue-179/canary
log_path="$log_root/attempt-$MUSAHHIH_ATTEMPT_ID.log"
exit_path="$log_root/attempt-$MUSAHHIH_ATTEMPT_ID.exit.json"
mkdir -p "$log_root"
test ! -e "$log_path"
test ! -e "$exit_path"
set +e
(
  python -m pip install --quiet --progress-bar off --requirement requirements-nautilus-f2-f3.txt || exit "$?"
  command -v nvidia-cuda-mps-control >/dev/null || exit 86
  mps_pipe="/tmp/musahhih-mps-$MUSAHHIH_ATTEMPT_ID"
  mps_log="/private/logs/issue-179/mps/attempt-$MUSAHHIH_ATTEMPT_ID"
  mkdir -p "$mps_pipe" "$mps_log"
  export CUDA_MPS_PIPE_DIRECTORY="$mps_pipe"
  export CUDA_MPS_LOG_DIRECTORY="$mps_log"
  unset CUDA_MPS_ACTIVE_THREAD_PERCENTAGE
  cleanup_mps() {
    echo quit | nvidia-cuda-mps-control >/dev/null 2>&1 || true
  }
  trap cleanup_mps EXIT
  nvidia-cuda-mps-control -d || exit 87
  ready=0
  for _ in $(seq 1 30); do
    if [[ -f "$mps_pipe/nvidia-cuda-mps-control.pid" ]]; then ready=1; break; fi
    sleep 1
  done
  [[ "$ready" -eq 1 ]] || exit 88
  export CUDA_MPS_ACTIVE_THREAD_PERCENTAGE=20
  timeout --signal=TERM --kill-after=30s 5400s \
    python -m scripts.run_f2_f3_nautilus_eval_concurrency_canary \
      --mps-canary \
      --training-root /private/outputs/issue-155 \
      --output-root /private/canaries/issue-179 \
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
    labels = _labels()
    container = _container(
        name="mps-canary",
        command=command,
        values={
            "MUSAHHIH_APPROVED_COMMIT": commit,
            "MUSAHHIH_APPROVAL_REFERENCE": approval_reference,
            "MUSAHHIH_CONFIRMATION": confirmation,
            "MUSAHHIH_ATTEMPT_ID": attempt,
        },
    )
    job = _job(
        name=f"musahhih-f2-f3-mps-canary-a{attempt[-8:]}",
        labels=labels,
        commit=commit,
        reference=approval_reference,
        attempt=attempt,
        container=container,
        deadline=6_000,
        private_test_access=False,
    )
    job["metadata"]["namespace"] = NAMESPACE
    job["metadata"]["annotations"]["musahhih.openai/mps-required"] = "true"
    return job


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-commit", required=True)
    parser.add_argument("--approval-reference", required=True)
    parser.add_argument("--confirmation", required=True)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = {
        "apiVersion": "v1",
        "kind": "List",
        "items": [
            build_mps_canary_job(
                commit=args.approved_commit,
                approval_reference=args.approval_reference,
                confirmation=args.confirmation,
            )
        ],
    }
    if args.output.exists():
        raise RuntimeError("manifest exists; refusing overwrite")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"stage": "mps-canary", "objects": 1, "contains_corpus_text": False}))


if __name__ == "__main__":
    main()
