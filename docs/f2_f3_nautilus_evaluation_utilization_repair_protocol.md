# F2/F3 Nautilus evaluation utilization repair protocol

Status: superseded after its single authorized canary failed batch equivalence.

> Execution note (2026-08-01): the issue #175 canary at
> `ff18bc5212d564aae5a110cd2636461f343a6428` failed closed before its soak
> because batch-64 and single-record synthetic outputs differed. No test input,
> prediction, metric, training, retry, or continuation occurred. See
> `f2_f3_nautilus_evaluation_concurrency_protocol.md` for the issue #177 repair.

## Preserved failed canary

Issue #173 canary attempt `5151539419` ran exactly once at commit
`f861ad34631c66f211f49a4278c2028b624ca5d4`. It passed synthetic
single-versus-batch-16 equivalence and completed the 64-batch synthetic soak,
then failed closed because mean A100 utilization was below the required 40%.
The Pod used about 11 GiB of its 64 GiB limit immediately before exit, was not
OOM-killed, exited with code 1, and had zero restarts. No test corpus,
prediction, metric, training, continuation, or retry occurred.

The failed implementation raised before writing its public summary, so the
exact observed utilization and peak-memory values were not persisted. They
must not be inferred.

## Narrow repair

The follow-up changes only execution mechanics and canary observability:

- continuation batch size increases from 16 to 64;
- the canary compares single-record and batch-64 greedy outputs;
- the soak uses 16 batches, preserving the prior total of 1,024 synthetic
  generations while increasing work per GPU launch;
- the soak writes a fixed corpus-free 2 KiB synthetic durability payload for
  every output and calls `fsync` per row, so the utilization gate includes the
  persistence overhead used by the real continuation;
- pass and failure paths atomically preserve the exact sample count, sampler
  failures, mean GPU utilization, peak cgroup-memory fraction, elapsed time,
  durability-row count, batch size, and error digest when available; and
- new issue-#175 approval URLs and confirmation strings prevent replay of the
  consumed issue-#173 authorization.

Prompts, parser, greedy decoding, 32-token output limit, model revision,
selected adapters, source predictions, record order, hashes, checkpoints, and
metrics are unchanged. Every returned real evaluation row remains separately
written, flushed, and `fsync`-ed.

## Gates

One fresh exact-commit owner GO may authorize exactly one non-test canary. It
must pass all of these before continuation can be considered:

- byte-identical single-versus-batch-64 synthetic outputs;
- 1,024 completed synthetic generations and 1,024 per-row durability writes;
- at least ten successful GPU samples and zero sampler failures;
- mean A100 utilization of at least 40%;
- peak cgroup memory below 80%; and
- no Nahw-Passage, QALB test, private prediction, metric, or training access.

The canary retains one A100, two CPUs, 64 GiB RAM, `backoffLimit: 0`, and the
4,200-second external timeout. Failure consumes its GO and cannot authorize a
retry or continuation. A passing canary still does not authorize continuation;
the two continuation lanes require a separate fresh exact-commit GO.

## Authorization boundary

Preparation and merge authorize no Kubernetes object, GPU allocation, model
loading, private-input access, inference, prediction, metric, retry,
continuation, training, QALB-test access, or XG.
