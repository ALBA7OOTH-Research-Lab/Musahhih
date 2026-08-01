# F2/F3 Nautilus evaluation utilization follow-up audit

## Outcome

Issue #175 prepares a repository-only follow-up to the single failed issue-#173
canary. It does not submit a Job or access a model, corpus, prediction, or
metric.

The preserved issue-#173 Job `musahhih-f2-f3-eval-canary-a51539419` failed
after approximately 41 minutes 26 seconds with exit code 1, zero restarts, and
`RepairCanaryError: mean GPU utilization did not clear 40 percent`. The full
synthetic batch-16 soak completed; no OOM occurred. The exact mean utilization
was not persisted by that failure path and is not reported.

## Prepared changes

- fixed continuation batch size: 64;
- synthetic soak: 16 batches and 1,024 total generations;
- single-versus-batch-64 equivalence remains mandatory;
- 1,024 corpus-free per-row durability writes with `fsync` are included in the
  utilization sampling window;
- exact corpus-free resource telemetry is persisted on pass and failure;
- issue-#173 authorization cannot activate the new gate; and
- all prior memory, timeout, prefix, hashing, and no-retry safeguards remain.

Execution remains disabled pending merge and a fresh exact-commit issue-#175
GO for one canary. Continuation requires a later, separate GO even if that
canary passes.

## Local validation

- `python -m compileall -q scripts tests`: passed.
- focused issue-#175 suite: 7 tests passed.
- complete repository suite: 281 tests passed.
- generated manifest JSON for one canary and two continuation lanes parsed
  successfully.
- Kubernetes client/server dry-runs were attempted but the Nautilus API was
  unreachable; no object was persisted.
