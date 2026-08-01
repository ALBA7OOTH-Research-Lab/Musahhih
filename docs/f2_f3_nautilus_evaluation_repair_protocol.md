# F2/F3 Nautilus evaluation repair protocol

Status: issue #173 repository preparation only; no execution authorized.

## Preserved source

Issue #171 attempt `5144097114` is immutable. The five Jobs durably preserved
3,739 of 5,110 record-arm outputs before three Pods were OOM-killed and two
owner-suspended Pods were released after prolonged no-progress GPU idling.
No partial metric was computed. The exact source executable commit is
`30290dd3a8bde5054555cc37ac422f3d1512d3ba`.

| Seed | F2-P1 | F3-P1 | First terminal state |
| --- | ---: | ---: | --- |
| 3407 | 511 | 237 | `OOMKilled` |
| 3408 | 236 | 511 | `JobSuspended` |
| 3409 | 511 | 237 | `OOMKilled` |
| 3410 | 237 | 511 | `JobSuspended` |
| 3411 | 511 | 237 | `OOMKilled` |

The source progress, prediction hashes, record order, score booleans, selected
adapter identities, source commit, test hash, and recorded counts must all
validate before a continuation writes a new attempt. At most one validated
orphan row may be reconciled. Completed rows are copied byte-for-byte.

## Root cause and repair

The failed Jobs requested eight CPUs and 32 GiB RAM while decoding one record
at a time. Each process retained enough host memory across sequential arms to
reach the cgroup limit. The in-process wall-clock check ran only between
records and therefore could not interrupt a generation call stalled by memory
pressure. The same stall left the reserved A100 underutilized.

The repair changes only execution mechanics:

- each unfinished seed runs in a fresh child process, so a completed prior arm
  is not resident;
- test prompts are decoded in fixed batches of 16 with unchanged prompt text,
  greedy decoding, maximum 32 new tokens, parser, selected checkpoint, and
  model revision;
- every returned row is still individually written, flushed, and `fsync`-ed;
- an external parent stops the child after 900 seconds without a committed
  row, at 85% cgroup memory, or after six hours;
- guard stops write a metric-free, fresh-GO resumable summary;
- each Pod requests two CPUs, 64 GiB RAM, and one A100; and
- two continuation lanes cover all five seeds sequentially, limiting live
  A100 concurrency to two and forcing a fresh process between seeds.

## Required non-test canary

Continuation is impossible until one separately authorized A100 canary passes
at the exact continuation commit. It mounts the retained training artifacts
but receives no Nahw-Passage path. It uses fixed synthetic prompts to require:

- byte-identical decoded strings for single-record and batch-16 greedy
  generation on the synthetic set;
- at least 40% mean GPU utilization during a 64-batch synthetic soak;
- peak cgroup memory below 80%; and
- no test corpus, prediction, metric, or training access.

The canary has `backoffLimit: 0`, a 4,200-second external timeout, and one A100.
Its first terminal state is preserved. Failure does not authorize a retry.

## Continuation and reporting

Only after the canary passes may a separate owner GO authorize the two
write-once continuation Jobs. A resource guard or nonzero child stops its lane;
there is no automatic retry or advance to the next seed. Any later continuation
accepts an exact metric-free repair handoff at the same code commit.

Metrics remain disabled until all five seeds reach 511/511 for both arms. The
existing issue #171 CPU-only aggregation gate remains the sole path to the
post-hoc robustness statistics.

## Authorization boundary

Merge of issue #173 authorizes no Kubernetes submission, GPU allocation,
model loading, private-input access, inference, metric, retry, continuation,
training, QALB-test access, or XG. The canary and continuation require separate
fresh owner comments naming the exact merged commit.
