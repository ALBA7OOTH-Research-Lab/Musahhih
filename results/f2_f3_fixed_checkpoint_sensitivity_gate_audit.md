# F2/F3 fixed-checkpoint sensitivity gate preparation audit

## Scope

Issue #192 prepares the post-hoc fixed-epoch sensitivity evaluation. No
cluster object, private file, model, inference, prediction, metric, training,
retry, or continuation was produced during preparation.

## Prepared gate

The gate validates both retained epoch checkpoints for each of seeds
3407–3411, then evaluates only the checkpoint not already represented by the
completed selected-adapter result. This reduces new work from 20 to 10 adapter
evaluations without changing any scientific setting. Five write-once RTX 3090
Jobs retain batch-16 equivalence, per-row durability, an 11-hour safe stop, a
20-minute no-progress guard, a 12-hour hard deadline, and no automatic retry.

The original seed-3407 P100 result and the independent `3407-A100` replication
are explicitly distinct. A later CPU-only aggregate gate must validate all
selected and unselected artifacts before reporting fixed epoch-1 or epoch-2
statistics.

## Authorization

This repository-only preparation authorizes no execution. A fresh exact-commit
owner GO is required for the five evaluation Jobs, and a separate later GO is
required for aggregation.

## Validation

- `python -m unittest tests.test_f2_f3_fixed_checkpoint -v`: 3 passed.
- `python -m unittest discover -s tests -v`: 306 passed, 2 skipped because the
  optional local Nahw download is absent.
- `python -m compileall -q scripts tests`: passed.
- Generated manifest: five unique RTX 3090 Jobs, ten new adapter evaluations,
  `backoffLimit: 0`, no training path.
- Kubernetes client and server dry-runs accepted all five Jobs; zero objects
  were persisted.
