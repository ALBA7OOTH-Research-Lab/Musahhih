# F2/F3 Nautilus concurrent evaluation repair audit

## Outcome

Issue #177 replaces the failed batch-64 strategy with concurrent isolated
batch-16 workers. This is repository-only preparation. No Kubernetes object,
GPU, model, private test input, inference, prediction, metric, training, retry,
or continuation was produced.

The repair follows official NRP policy rather than bypassing it: finite
Kubernetes Jobs, equal requests/limits, measured resource gates, an 80 GB A100
selected through advertised node labels, private durable state on the retained
RWX PVC, and no automatic retry. The cluster and namespace were inspected
read-only; the namespace had zero of five A100 requests in use.

## Preserved terminal state

The single issue #175 Job
`musahhih-f2-f3-eval-canary-a52098938` at
`ff18bc5212d564aae5a110cd2636461f343a6428` reached `Failed` after 1,951
seconds. Its Pod exited one with zero restarts because synthetic batch-64 and
single-record outputs differed. The persisted corpus-free error-message digest
was `72ee79b90538f1c6899916c5c5b83310e5eb15f43489750fd7025b0a22bae406`.
It stopped before the soak and accessed no test corpus or metric. It was not
retried.

## Prepared controls

- five isolated batch-16 processes on one 80 GB A100;
- one unfinished arm per seed, all running concurrently;
- exact reuse of all 3,739 source outputs;
- synthetic five-worker equivalence/utilization/memory canary;
- eight CPUs, 96 GiB RAM, and equal requests/limits;
- per-row `fsync`, atomic progress, private logs, and write-once attempts;
- global memory, per-seed no-progress, child-exit, and wall-clock guards; and
- separate exact-commit GOs for canary and continuation.

## Validation

- `python -m compileall -q scripts tests`: passed.
- focused issue-#177/repair/evaluation suite: 21 tests passed.
- complete repository suite: 286 tests passed.
- one generated canary Job and one generated continuation Job parsed and
  passed Kubernetes client dry-run.
- the same two Jobs passed Kubernetes server dry-run, including the 80 GB A100
  node affinity and equal resource requests/limits.
- a post-dry-run label query returned zero persisted issue-#177 Jobs.
