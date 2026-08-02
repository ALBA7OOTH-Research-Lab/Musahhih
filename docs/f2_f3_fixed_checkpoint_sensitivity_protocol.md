# F2/F3 fixed-checkpoint sensitivity protocol

Status: issue #192 preparation only; no execution is authorized.

## Question

The five-seed robustness cohort selected checkpoints by the frozen lowest-loss
rule on the common natural QALB development set. This post-hoc sensitivity
analysis asks whether F3-P1 remains ahead of F2-P1 when every seed-arm is
compared under matched fixed epoch 1 and fixed epoch 2 policies.

This is not a new primary experiment. The original seed-3407 P100 comparison
remains primary, and the independently trained seed-3407 A100 member is labeled
`3407-A100 replication` rather than an exact reproduction.

## Reuse and minimum new inference

Both retained epoch checkpoints are already available for every F2-P1 and
F3-P1 seed 3407–3411:

- epoch 1: `checkpoint-125`;
- epoch 2: `checkpoint-250`.

The completed issue-#183 selected-checkpoint predictions are reused only after
their exact adapter, prediction, test, count, schema, and ordering identities
pass the existing issue-#185 audit. Each issue-#192 Job evaluates only the
other retained checkpoint for both arms. Thus the requested 20 epoch-policy
cells require 10 new adapter evaluations, not 20. No training, checkpoint
selection, or selected-adapter reevaluation occurs.

## Frozen execution

Five write-once Jobs, one per seed, use the same RTX 3090 runtime and frozen
batch-16 greedy decoding that completed the selected-checkpoint cohort. Before
test access, each Job validates the completed training pair and byte identities
of both epoch checkpoints, then passes the existing synthetic single/batch-16
equivalence gate. TF32 remains disabled. Prompt, parser, base revision,
`max_new_tokens=32`, test SHA-256, and exact-match definition remain unchanged.

Every prediction row is flushed and `fsync`-ed, and a corpus-free progress
manifest is atomically replaced. Each Job has `backoffLimit: 0`, an 11-hour
safe stop, a 12-hour hard deadline, and a 20-minute no-progress guard. No
automatic retry is permitted. A stop or failure reports no metric and any
continuation requires a fresh exact-source GO.

## Separate CPU aggregate

After all five Jobs complete, a separate reviewed CPU-only gate will validate
all source identities and assemble, for each seed and arm, the fixed epoch-1,
fixed epoch-2, and dev-selected outcomes. It will report this compact table:

| Checkpoint policy | F2 mean | F3 mean | F3 − F2 |
|---|---:|---:|---:|
| Fixed epoch 1 | pending | pending | pending |
| Fixed epoch 2 | pending | pending | pending |
| Dev-selected | 21.68% | 31.98% | +10.29 pp |

No conclusion about the fixed policies is permitted before that aggregate is
authorized and completed.

## Authorization boundary

Preparation and merge authorize no Kubernetes object, GPU allocation,
private-test access, model loading, inference, prediction, metric, training,
retry, continuation, QALB test, prompt/parser change, or XG. Execution requires
a fresh owner comment naming the exact merged commit. Aggregation requires a
later separate GO and gate.
