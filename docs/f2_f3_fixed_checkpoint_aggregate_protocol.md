# F2/F3 fixed-checkpoint aggregate protocol

Status: issue #196 preparation only; no execution is authorized.

## Purpose

This CPU-only audit assembles the post-hoc five-seed sensitivity table for
fixed epoch 1, fixed epoch 2, and the frozen common-development checkpoint
selection rule. It performs no inference and does not change any checkpoint.
The original seed-3407 P100 comparison remains the primary experiment.

## Frozen private sources

- selected checkpoints: issue #183 attempt `5155890101`, evaluation commit
  `e004e625a00c9c1c6fac7e2dbc0e7bc450fbad17`;
- unselected checkpoints for seeds 3408, 3410, and 3411: issue #192 attempt
  `5157509573`, executable commit
  `6b77efafd53660d2b98557b93cff983e91dbbf27`;
- unselected replacement checkpoints for seeds 3407 and 3409: issue #194
  attempt `5158062318`, executable commit
  `3b2a30aa994071d5a51a51f62ee31df6cd13d958`.

The audit validates the retained training completion records and exact adapter
hashes without exposing development losses. It then validates 20 unique
prediction files: two arms, two epoch checkpoints, and five seeds. The three
reported policies reuse those files by exact checkpoint identity.

## Validation and output

Before computing any statistic, the audit requires exact source attempts and
commits, complete 511-row counts, the frozen test hash, prediction hashes,
schema, paired order, batch-16 RTX 3090 identity, pre-test gate success, and
the absence of retry, training, QALB-test use, prompt/parser change, or exposed
development values. It recomputes each source summary's counts and paired
statistics from private rows.

The public result contains only corpus-text-free per-seed counts, accuracies,
policy means, sample standard deviations, F3-minus-F2 differences, source
hashes, and validation flags. Predictions, record IDs, corpus text, model
responses, adapters, private logs, and development values remain on the PVC.

## Execution boundary

The manifest contains one write-once, no-GPU Job with `backoffLimit: 0` and a
one-hour deadline. Preparation and merge authorize no Kubernetes object, PVC
read, prediction read, metric, model loading, inference, training, checkpoint
selection or reselection, retry, QALB test, diagnostics, prompt/parser change,
or XG. One execution requires a fresh owner GO on issue #196 naming the exact
merged commit and confirmation `AGGREGATE_F2_F3_FIXED_CHECKPOINT_RESULTS`.
