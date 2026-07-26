# B1-P1/B2-P1 timeout-safe final-gate implementation audit

## Scope

Issue #107 hardens the frozen B1-P1/B2-P1 Nahw-Passage runner against Kaggle's
hard runtime cutoff. This is implementation evidence only. No model was loaded,
no private or final-test record was read, no inference ran, and no result was
produced.

## Implemented controls

- fixed 34,200-second safe stop measured from the private wrapper start;
- per-record private JSONL flush and `fsync`;
- atomically replaced, corpus-text-free `progress.json`;
- successful metric-free `incomplete_time_budget` handoff;
- write-once continuation into a new run directory;
- exact execution-identity checks for protocol, seed, input, prompt, optional
  B1 bundle, model revision, decoding, and approved commit;
- exact private-prefix checks for hash, schema, order, prompt rendering, parser
  output, warning list, and score consistency;
- skip-only continuation that never regenerates completed records;
- final activation bound to an exact confirmation, repository issue-comment
  approval, approved checkout, frozen identities, and one P100 GPU; and
- no automatic retry or continuation.

Synthetic fixtures exercise a planned interruption, successful continuation,
identity mismatch, prediction-hash mismatch, schema mutation, row reordering,
score mutation, private-path restrictions, and existing-run refusal. The
fixtures contain no Nahw-Passage or QALB text.

## Validation

- `python -m compileall scripts`
- `python -m pytest -q` — 207 tests and 62 subtests passed
- disabled final CLI probe — rejected before input read or output creation
- JSON parsing for both changed result summaries
- ignored-root checks for `outputs/` and `data/processed/`
- credential-pattern scan
- `git diff --check`

## Authorization boundary

Merging this implementation does not authorize model loading, Nahw-Passage
access, inference, Kaggle submission, or continuation. Every segment requires
independent review of the exact merged commit and a fresh scope-specific owner
GO recorded as a Musahhih issue-comment permalink. A timed handoff publishes no
partial metric.
