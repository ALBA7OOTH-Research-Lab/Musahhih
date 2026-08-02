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

## Terminal canary and issue-#181 audit

The single authorized issue-#179 canary ran at exact commit
`6072c331170cf6dd29504031a60de9e5866320dc`. One MPS server and all five
20%-thread clients attached on an `NVIDIA A100 80GB PCIe`. Every worker then
failed the same frozen exception, `batch-16 output changed during soak`. The
five worker summaries shared error digest
`670e0a0783f1e56d40c37bb7b3b45eeb227134e8180968c5e0e73ddb027171ab`;
their logs were byte-identical with SHA-256
`5081779dd0b59ca7a782e240055978dbf9df7a6dbcb0637b5c2f8715f4147acf`.

The parent preserved 631 valid GPU samples with zero sampler failures,
27.748% mean utilization, 0.503723 peak GPU-memory fraction, and 0.305003 peak
host-memory fraction. Because all workers failed equivalence first, the final
durability and utilization acceptance gates were not reached. The MPS server
and controller shut down with exit status zero. The Job ended failed with
container exit one, zero restarts, and no automatic retry.

Issue #181 authorized one CPU-only Pod that mounted the PVC read-only and read
only the exact issue-#179 public/worker summaries and error/MPS logs. It did not
open prompts, generated outputs, durability rows, adapters, checkpoints,
Nahw-Passage, QALB, predictions, or metrics. The audit Pod was deleted; the
retained artifacts remain unchanged.

MPS is rejected for this frozen evaluation because it violated the required
repeated-output equivalence in all five workers and did not clear the
utilization threshold. No further pre-submission canary or continuation is
planned, and no partial multi-seed result may be reported.
