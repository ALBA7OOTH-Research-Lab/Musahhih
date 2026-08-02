# F2/F3 RTX 3090 recovery gate audit

## Outcome

Issue #183 prepares five clean, independent, record-zero evaluation Jobs on
uniform RTX 3090 hardware. No Kubernetes object, private input, model, test
record, inference, prediction, metric, training, retry, or continuation was
created during preparation.

The recovery intentionally excludes all A100 partial prefixes. It preserves
the frozen model, selected adapters, prompts, parser, greedy decoding, test
hash, balanced arm order, and record-level durability. The hardware change is
post-hoc and must be disclosed.

## Safety net

- exact 24 GB-class RTX 3090 identity plus executable CUDA operation;
- inline synthetic single/batch-16/repeated-batch equivalence before test;
- one Job per seed, both arms from record zero;
- equal requests and limits, exact node affinity, and `backoffLimit: 0`;
- per-row `fsync`, atomic progress, 11-hour safe stop, 12-hour Job deadline;
- 20-minute external no-progress termination with corpus-free summary; and
- private logs, predictions, responses, adapters, and metrics.

## Validation

The repository preparation passed:

- all 295 unit tests;
- focused Ruff checks for all issue-#183 Python files and the modified runner;
- `python -m compileall -q scripts`;
- `git diff --check` and JSON parsing;
- Kubernetes client dry-run for exactly five Jobs;
- Kubernetes server dry-run for the same five Jobs, including exact RTX 3090
  affinity, equal requests/limits, generic one-GPU requests, 12-hour deadlines,
  and `backoffLimit: 0`; and
- a post-dry-run query returning zero persisted issue-#183 Jobs.
