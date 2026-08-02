# F2/F3 five-seed RTX 3090 evaluation recovery

Status: issue #183 repository preparation only; no execution authorized.

## Decision

The A100 source attempt remains immutable with 3,739/5,110 private rows and no
metric. Batch 64 changed outputs, five ordinary batch-16 A100 workers averaged
11.762% utilization, and MPS changed repeated outputs in all five workers while
still observing only 27.748% utilization. None is eligible for continuation.

The recovery starts all five seeds from record zero on one exact hardware
class: `NVIDIA GeForce RTX 3090`, CUDA capability 8.6, with at least 23 GiB of
reported device memory. Nautilus currently labels 49 such nodes, 47 of them
schedulable at preparation time. Each Job requests one generic GPU and uses an
exact product affinity. The local GTX 1650 SUPER has only 4 GiB and is retained
only as a last-resort development machine, not an evaluation target.

## One five-Job wave

Seeds 3407–3411 run as five independent Jobs. Each Job:

1. checks out the exact approved commit and executes a CUDA operation;
2. validates its two frozen selected adapters without opening test input;
3. loads the first arm selected by the frozen balanced arm order;
4. on 16 synthetic non-corpus prompts, requires single-record output to equal
   batch-16 output and a repeated batch-16 output;
5. only after that gate, opens the existing hash-gated 511-row frozen test;
6. evaluates both arms from record zero with batch size 16 and greedy decoding;
7. writes every private row with `fsync` and atomically refreshes progress;
8. stops safely at 11 hours or after 20 minutes without progress; and
9. uses `backoffLimit: 0`, a 12-hour Job deadline, and no automatic retry.

The output root is a new write-once tree,
`/private/evaluations/issue-183`. The A100 source tree is never passed as a
resume source. Each Job uses the same pinned image, model revision, adapters,
prompt, parser, decoding, batch size, GPU product, and code commit.

## Interpretation and boundary

This is a post-hoc infrastructure recovery, not a preregistered hardware
choice. Training remains the already completed A100 wave; inference for all
five recovered seeds is uniform RTX 3090. The paper must disclose that fact.

Preparation and merge authorize no Kubernetes object, private input, model
load, inference, prediction, metric, training, retry, continuation, QALB test,
or XG. One fresh issue-#183 owner GO naming the exact merged commit authorizes
only the five-Job wave. Metrics remain private until all five complete and a
separate CPU aggregate audit is authorized. No partial claim is allowed.
