# F2/F3 Nautilus MPS canary repair audit

## Outcome

Issue #179 prepares an NVIDIA MPS version of the synthetic five-worker
batch-16 canary. No Kubernetes object, GPU, model, private input, inference,
prediction, metric, training, retry, or continuation was produced.

The prior issue #177 canary is preserved as terminal: 11.762% mean A100
utilization across 974 valid samples, zero sampler failures, 52.6697% peak GPU
memory, 32.2968% peak host memory, exit one, and zero restarts. Its
authorization is consumed.

## Prepared changes

- one same-UID NVIDIA MPS controller/server inside the existing exclusive
  80 GB A100 container;
- five batch-16 clients capped at 20% active threads each;
- exact one-server/five-client control-plane validation;
- unchanged synthetic output equivalence and durability gates;
- persistent private MPS logs and unconditional daemon shutdown;
- issue-#179-only exact-commit activation; and
- the existing utilization, host/GPU-memory, timeout, privacy, and no-retry
  controls.

## Validation

The repository preparation passed:

- all 290 unit tests;
- focused Ruff checks for all issue-#179 Python files;
- `python -m compileall -q scripts`;
- `git diff --check`;
- JSON parsing of both changed result summaries;
- Kubernetes client dry-run for exactly one Job;
- Kubernetes server dry-run for the same Job, including the 80 GB A100 node
  affinity, equal requests/limits, and `backoffLimit: 0`; and
- a post-dry-run label query returning zero persisted issue-#179 Jobs.

The local host has no Docker executable, so the pinned image could not be
inspected locally for the MPS control binary. The generated Job therefore
checks `nvidia-cuda-mps-control` before adapter validation and exits 86 if the
binary is absent. Repository-wide Ruff also reports 18 unrelated pre-existing
violations; the four files changed or added for issue #179 pass.
