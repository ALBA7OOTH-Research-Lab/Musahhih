# Fixed-checkpoint batch-stability repair preparation audit

## Scope

Issue #194 prepares, but does not execute, replacements for only issue-#192
seeds 3407 and 3409. The three completed seeds are preserved without rerun.

## Failure audit

Both failed Jobs terminated before test staging validation because the
synthetic single-record and batch-16 outputs differed. The private retained
logs were hashed and matched against a fixed corpus-free signature list without
printing their content:

- seed 3407: SHA-256
  `27dc39f62f031deb78502f3b34578799184716c08685711690c481cef1ceb107`,
  2,481 bytes, 21 lines;
- seed 3409: SHA-256
  `4e6ff65fe9e1f1242cf7880731e0269711cd7084dda2765ae7dc78b3363cacd4`,
  2,481 bytes, 21 lines.

No Nahw-Passage record was opened, no prediction was written, and no metric
was computed by either failed Job.

## Prepared change

The replacement canary requires repeated stability of the exact frozen
batch-16 path rather than equality between two different execution shapes.
All remaining identities and safety controls are unchanged. Exactly two fresh
Jobs are generated, with no automatic retry or successful-seed rerun.

Preparation authorizes no execution. Validation results are recorded after the
focused and full checks complete.

## Validation

- `python -m unittest tests.test_f2_f3_fixed_checkpoint_repair -v`: 4 passed.
- `python -m unittest discover -s tests -v`: 313 passed, 2 skipped because the
  optional local Nahw download is absent.
- `python -m compileall -q scripts tests`: passed.
- Ruff passed for all new Python files.
- Generated manifest: exactly two Jobs, only seeds 3407 and 3409, namespace
  `aiea-interns`, `backoffLimit: 0`, no training path.
- Kubernetes client and server dry-runs accepted both Jobs; zero objects were
  persisted.
