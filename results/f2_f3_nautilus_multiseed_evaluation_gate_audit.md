# F2/F3 Nautilus multi-seed evaluation-gate preparation audit

## Scope

Issue #171 prepares the post-hoc five-seed selected-adapter evaluation and
aggregate robustness gate. This is repository-only work. No Kubernetes object,
private file, model, inference, prediction, metric, training, retry, or
continuation was produced during preparation.

## Implemented gate

The repository now provides three independently authorized stages:

1. one CPU-only, write-once staging Pod for the exact 511-record prepared
   Nahw-Passage artifact on the existing PVC;
2. five unique timeout-safe A100 Jobs, one per seed, each evaluating its frozen
   F2-P1/F3-P1 selected-checkpoint pair; and
3. one CPU-only aggregate Job that validates all five summaries and all ten
   private prediction hashes/counts before reporting frozen seed-level and
   across-seed statistics.

The evaluator validates the exact completed training cohort before test access,
keeps development values private, disables TF32, retains the frozen prompt,
parser, decoding, base revision, and unmerged-adapter interface, and writes
every private prediction row with `fsync`. The 18-hour safe stop produces a
metric-free resumable handoff. Fresh-GO continuation accepts only an exact
validated prefix and reconciles at most one row durably written immediately
before a progress-manifest crash.

Every Job has `backoffLimit: 0`; fresh owner-comment IDs make Kubernetes names,
attempt directories, logs, and exit records write-once. No automatic retry is
implemented.

## Frozen reporting

If all five evaluations later complete under separate authorization, the
aggregate reports every seed result, per-arm mean and sample standard
deviation, and the mean, sample standard deviation, minimum, and maximum of the
five paired F3-P1-minus-F2-P1 differences. The original seed-3407 result remains
the primary preregistered comparison; this cohort is labeled post-hoc robustness
evidence.

## Validation

- `python -m compileall -q scripts tests`: passed.
- `python -m unittest tests.test_f2_f3_multiseed_eval -v`: 9 tests passed.
- `python -m unittest discover -s tests -v`: 274 tests passed.
- Generated staging manifest: one existing-PVC Pod, no GPU, no PVC creation.
- Generated evaluation manifest: five unique A100 Jobs, `backoffLimit: 0`.
- Generated aggregate manifest: one no-GPU Job, `backoffLimit: 0`.
- Kubernetes client and server dry-runs accepted all seven generated objects;
  the server dry-run persisted zero objects.

Execution remains disabled pending review, merge, and separate fresh
exact-commit owner GOs for staging, evaluation, and aggregation.
