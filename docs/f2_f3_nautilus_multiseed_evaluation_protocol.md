# F2/F3 Nautilus multi-seed evaluation and aggregation protocol

Status: issue #171 preparation only; no execution authorized.

## Purpose and interpretation

This gate evaluates the five completed paired-seed F2-P1/F3-P1 training runs
without changing their checkpoints or the completed primary experiment. It is
post-hoc robustness evidence. The original seed-3407 matched result remains the
primary preregistered comparison.

The gate asks whether the observed F3-P1 minus F2-P1 advantage remains stable
across training randomness. It does not authorize another training run, a new
model, a new test set, prompt or parser tuning, checkpoint reselection, or
qualitative example selection.

## Frozen inputs and systems

- training cohort commit:
  `108888dcf0ad34c49157b47e2561c406c5463bf8`;
- seeds: `3407`, `3408`, `3409`, `3410`, and `3411`;
- arms: F2-P1 and F3-P1 only;
- one selected private checkpoint per arm and seed, chosen before test access
  by the frozen common-development rule;
- base model: `unsloth/gemma-3-4b-it-unsloth-bnb-4bit`;
- base revision: `316726ca0bd24aa323bfaf86e8a379ee1176d1fe`;
- frozen 511-record prepared Nahw-Passage JSONL, SHA-256
  `acb3cfd204b35d5415532fbd32a4a5231b553fae329ab8f48e8454609e10279b`;
- unchanged B0 prompt and
  `scripts.nahw_baseline_utils.parse_model_response`;
- greedy decoding, no temperature argument, `max_new_tokens=32`;
- unmerged LoRA on the pinned 4-bit base; and
- no normalization, output repair, XG, or multiple-reference credit.

Before opening the test file, each evaluation Job validates its seed's
`99_pair_complete.json`, frozen arm order, training commit, both completion
markers, checkpoint-selection contract, and the exact identities of both epoch
checkpoints. It then uses only the already selected checkpoint. Development
loss values are never printed or copied into a public summary.

## Matched A100 execution

There are five Jobs, one per seed. Each requests one NVIDIA A100, executes a
synchronized CUDA operation before any private path is opened, uses the frozen
PyTorch 2.6.0/CUDA 12.4 package stack, disables TF32 and Unsloth compilation,
and evaluates both arms sequentially on the same assigned GPU. Evaluation arm
order matches the balanced training order:

- 3407, 3409, 3411: F2-P1 then F3-P1;
- 3408, 3410: F3-P1 then F2-P1.

Every Job has `backoffLimit: 0`. A fresh owner-comment ID determines the
write-once Kubernetes Job, private attempt, log, and exit-record identities.
No automatic retry or continuation is permitted.

## Timeout and crash safety

The private wrapper records wall-clock time before dependency setup. The
runner stops before starting a new record after 64,800 seconds (18 hours),
leaving up to six hours for scheduling and setup under the 24-hour Job
deadline. Each prediction row is written, flushed, and `fsync`-ed before an
atomically replaced corpus-free progress manifest advances.

A graceful time stop returns `incomplete_time_budget` with counts and hashes
but no metric. A later attempt requires a fresh GO and exact validation of the
evaluation commit, seed, test hash, adapter identities, runtime metadata, row
schema/order, parser result, and score consistency. If a crash occurs after a
row is durably written but before progress is replaced, continuation may
reconcile exactly one validated orphan row; any larger disagreement fails
closed. Completed rows are copied byte-for-byte and never regenerated.

Failure records contain only the phase-independent exception class, a hash of
the exception message, completed counts, and safety flags. Private prompts,
test text, gold corrections, model responses, predictions, adapters,
checkpoints, and full logs remain on the existing ignored PVC.

## Frozen per-seed outcomes

Only after both arms complete may a seed summary contain:

- exact-match correct count and accuracy per arm;
- invalid/empty, suspicious-output, multi-token, and parser-warning counts;
- prediction SHA-256 per arm;
- F3-P1 minus F2-P1 accuracy difference;
- F2-wrong/F3-right and F2-right/F3-wrong discordant counts;
- two-sided exact McNemar p-value; and
- deterministic 10,000-sample paired-bootstrap 95% interval, seeded by the
  training seed.

The Job console reports only completion status and record counts, never a
partial or completed metric. Per-seed result summaries remain private until
all five terminal states are preserved and the separate aggregate gate is
authorized.

## Frozen aggregate

The CPU-only aggregate Job requires all five complete summaries, exact source
attempt and evaluation-commit identities, and byte hashes plus 511-line counts
for all ten private prediction artifacts. It reports:

- every seed's F2-P1 accuracy, F3-P1 accuracy, and paired difference;
- per-arm mean accuracy and sample standard deviation;
- mean, sample standard deviation, minimum, and maximum of the five paired
  F3-P1 minus F2-P1 differences; and
- the explicit definition `sample SD with denominator n-1`.

It does not pool records across seeds as if they were independent runs and
does not convert this post-hoc cohort into a preregistered result.

## Authorization separation

Merge of issue #171 creates no Kubernetes object and authorizes no private
access, model loading, inference, prediction, metric, or aggregation.

Frozen test staging requires a fresh owner comment:

> GO: authorize exactly one CPU-only frozen Nahw-Passage staging Pod for
> Musahhih issue #171 at exact merged commit `<40-hex-commit>`. Mount only the
> existing `musahhih-f2-f3-replication` PVC, upload only the frozen 511-record
> `nahw_gec_test.jsonl`, verify SHA-256
> `acb3cfd204b35d5415532fbd32a4a5231b553fae329ab8f48e8454609e10279b`
> and count 511 without printing corpus text, preserve the first terminal
> state, and do not load a model, run inference or metrics, retry, replace, or
> access QALB test.

Only after staging passes may five evaluations receive a separate GO:

> GO: authorize exactly five write-once Nautilus A100 evaluation Jobs for
> Musahhih issue #171 at exact merged commit `<40-hex-commit>`, one for each
> frozen seed 3407–3411. Each Job may validate that seed's frozen completed
> F2-P1/F3-P1 checkpoint identities and evaluate only the selected adapters on
> the exact staged 511-record Nahw-Passage artifact with frozen greedy decoding,
> per-row fsync, atomic progress, and the 18-hour metric-free safe stop. Keep
> predictions, responses, checkpoints, and logs private. Run no training,
> QALB test, prompt/parser/checkpoint change, or XG; do not automatically retry,
> replace, or continue any Job. Preserve every first terminal state.

Only after all five complete summaries are preserved may aggregation receive
a third GO:

> GO: authorize exactly one CPU-only aggregation Job for Musahhih issue #171
> at exact merged commit `<40-hex-commit>`, reading only the five completed
> issue-#171 summaries and hashing/counting their ten private prediction files.
> Validate the exact evaluation commit and source attempt, compute only the
> frozen per-seed and across-seed aggregates, print no corpus text or model
> response, preserve the first terminal state, and do not retry or alter any
> scientific setting.

Any incomplete or failed evaluation requires independent review and a fresh
scope-specific continuation GO naming the exact source attempt. A completed
seed is never repeated because of its score.
