# F2/F3 Nautilus evaluation repair preparation audit

## Outcome

Issue #173 prepares a fail-closed repair for the preserved issue #171 attempt.
No cluster object, GPU, model, private input, inference, prediction, metric,
retry, or continuation was produced during preparation.

The repair retains all 3,739 durable source outputs, supports the three
`OOMKilled` and two `JobSuspended` source states, and refuses any source commit,
attempt, count, hash, adapter, test identity, schema, order, or score mismatch.

## Safety changes

- fresh worker process for each unfinished seed;
- fixed batch size 16, gated by non-test single/batch equivalence;
- external 900-second no-progress, 85% memory, and six-hour worker guards;
- per-row `fsync` and atomic corpus-free progress retained;
- metric-free resource-guard summaries support fresh-GO continuation;
- one A100 canary followed, only if passing, by two sequential-seed lanes;
- two CPUs and 64 GiB RAM per A100 Pod; and
- `backoffLimit: 0` everywhere.

## Validation

- `python -m compileall -q scripts tests`: passed.
- focused issue-#171/#173 suite: 15 tests passed.
- complete suite: 280 tests passed.
- one canary Job and two continuation Jobs passed Kubernetes client dry-run.
- the same three objects passed Kubernetes server dry-run.
- zero dry-run objects persisted.

Execution remains disabled pending merge and a fresh exact-commit canary GO.
