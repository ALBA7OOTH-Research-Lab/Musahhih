# F2/F3 diagnostic private-dataset source repair audit

Recorded: 2026-08-02
Status: issue #202 repository repair prepared; no private bundle or kernel created

## Trigger

Before issue #200 submission, the active Kaggle account was confirmed as
`thgh15`. Read-only API checks returned HTTP 403 for all three required private
`univverssal` kernel sources. No kernel was submitted, no GPU was allocated, and
no model or private diagnostic record was opened.

## Repair

The existing wrapper already discovers every input, adapter, checkpoint
selection, and immutable B0/F1 prediction by its frozen SHA-256. The repair
therefore changes only Kaggle source topology:

- a disabled-by-default preparer can assemble the minimal 12-file private
  artifact bundle under ignored `outputs/` after an exact issue-#200 GO;
- the bundle includes only the two diagnostic inputs, two selected adapter
  models/configs and selections, and four immutable B0/F1 predictions;
- the preparer validates every existing schema and hash contract before copying;
- bundle creation is write-once and produces a corpus-free manifest;
- upload is deliberately absent from the preparer and must be an explicit
  `kaggle datasets create --private` action under the same authorization; and
- kernel metadata may attach the resulting private dataset instead of
  inaccessible cross-account kernel outputs. The inference wrapper and all
  scientific/runtime/timeout gates are unchanged.

Legacy source topology remains supported but cannot be mixed with the combined
private-dataset topology. A continuation may additionally attach only the exact
prior private kernel output locked by its public-summary SHA-256.

## Authorization boundary

This repair authorizes no private artifact read or copy, dataset creation or
upload, Kaggle kernel submission, GPU, model loading, inference, metric,
training, checkpoint selection or reselection, Nahw-Passage, QALB test,
prompt/parser change, retry, continuation, linguistic labeling, or XG. After
merge, one fresh exact-commit issue-#200 GO must explicitly authorize one
private dataset upload and one initial kernel segment.

## Validation

- `python -m compileall scripts`: passed;
- focused private-dataset and diagnostic tests: 18 passed;
- complete repository suite: 334 passed;
- generated dataset-only kernel wrapper compilation: passed;
- generated metadata contained one private dataset source, zero legacy kernel
  sources, and the exact P100 machine shape; and
- `git diff --check`: passed.
