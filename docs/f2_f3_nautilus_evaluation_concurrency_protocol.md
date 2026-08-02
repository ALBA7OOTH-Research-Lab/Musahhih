# F2/F3 Nautilus concurrent batch-16 evaluation repair

Status: superseded after its single authorized canary failed utilization.

> Execution note (2026-08-01): all five batch-16 workers reached the final
> utilization gate, but mean A100 utilization was 11.762%. Memory remained
> safe and no test input or metric was used. The Job was not retried. See
> `f2_f3_nautilus_evaluation_mps_protocol.md` for the issue #179 repair.

## Preserved evidence

The issue #173 synthetic canary proved byte-identical single-record and
batch-16 greedy outputs and completed its soak without OOM, but failed the NRP
requirement for mean A100 utilization above 40%. The exact utilization was not
persisted and is not inferred.

Issue #175 then tested batch 64 once at commit
`ff18bc5212d564aae5a110cd2636461f343a6428`. It failed closed before its soak
because the synthetic batch-64 outputs differed from single-record outputs.
The Job ran for 1,951 seconds, exited one with zero restarts, and persisted a
corpus-free failure summary. It did not open Nahw-Passage, run evaluation or
training, produce a prediction or metric, or continue any source output. Its
authorization is consumed.

The interrupted issue #171 evaluation remains fixed at 3,739 of 5,110 durable
record-arm outputs. Exactly one arm is incomplete for each seed:

| Seed | Complete source rows | Unfinished arm and prefix |
| --- | --- | --- |
| 3407 | F2-P1 511 | F3-P1 237/511 |
| 3408 | F3-P1 511 | F2-P1 236/511 |
| 3409 | F2-P1 511 | F3-P1 237/511 |
| 3410 | F3-P1 511 | F2-P1 237/511 |
| 3411 | F2-P1 511 | F3-P1 237/511 |

## Nautilus-informed design

NRP policy requires GPU utilization above 40%, requests close to observed
usage, batch Jobs for finite computation, and monitoring of GPU, CPU, and RSS.
The cluster exposes one 10 GB A100 MIG profile, but that is below the validated
model/runtime envelope. Completed training used both 40 GB and 80 GB A100s.

The repair therefore preserves the validated batch size 16 and uses five
isolated model processes concurrently on one 80 GB A100. This changes workload
packing, not prompts, parsing, decoding, checkpoints, record order, source
predictions, or statistics. Each process owns one seed directory and resumes
only that seed's exact source prefix. The five unfinished arms run together;
completed arms are copied byte-for-byte and never regenerated.

The Job requests and limits eight CPUs, 96 GiB RAM, 40 GiB ephemeral storage,
and one `nvidia.com/a100`. Required node affinity accepts only
`NVIDIA-A100-SXM4-80GB` or `NVIDIA-A100-80GB-PCIe`. Tokenizer and BLAS thread
counts are bounded. `backoffLimit` is zero.

## Synthetic canary

A separately authorized canary must run five isolated batch-16 workers with
the selected seed-3407 F2 adapter and synthetic non-corpus prompts. It may not
mount or open the staged test input. It must establish all of the following:

- five complete workers and equal synthetic output hashes across them;
- 24 batch-16 soak iterations per worker;
- 1,920 synthetic generations and 1,920 per-row `fsync` writes;
- at least ten successful GPU samples and zero sampler failures;
- mean GPU utilization at least 40%;
- peak GPU-memory fraction below 85%;
- peak cgroup-memory fraction below 80%; and
- no corpus text, private prediction, metric, training, QALB test, or XG.

The earlier issue #173 result supplies the single-record-to-batch-16 link; the
new canary supplies the concurrent-worker equivalence and resource-safety link.
A canary failure is terminal and cannot authorize continuation.

## Continuation safety

Only a separately authorized continuation may mount the staged 511-record test
input. One coordinator starts all five seed workers, redirects their full logs
to private write-once files, and monitors each corpus-free progress manifest.
Every prediction row remains separately flushed and `fsync`-ed. A nonzero
child, 900 seconds without per-seed progress, 85% cgroup-memory use, or six-hour
coordinator wall clock terminates all remaining children and writes metric-free
handoffs. There is no replacement, retry, or automatic continuation.

The continuation accepts only source attempt `5144097114` at evaluation commit
`30290dd3a8bde5054555cc37ac422f3d1512d3ba`. It validates all source hashes,
counts, row alignment, adapter identities, test identity, and write-once paths
before generation. Per-seed results stay private until the already prepared
CPU-only aggregation gate receives its own fresh GO.

## Authorization boundary

Preparation and merge authorize no Kubernetes object, GPU allocation, model
load, private-input access, inference, prediction, metric, training, retry,
continuation, QALB test, or XG. The synthetic canary and private continuation
require separate fresh issue-#177 owner comments naming the exact merged commit.
