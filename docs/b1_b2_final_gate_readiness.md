# B1-P1/B2-P1 final-gate readiness review

Status updated: 2026-07-28. Issue #125 failed before model loading; another
final execution remains unauthorized.

Issue #116 separates runtime discovery from dependency installation after the
issue #114 DNS failure. `scripts/check_b1_b2_kaggle_runtime.py` is a standalone
probe that imports only PyTorch, reads installed package metadata, and reports
aggregate Python/CUDA/GPU/package information. It does not clone the
repository, install packages, access private inputs, load a model, or perform
inference. This repair issue does not authorize even the probe to run on
Kaggle. The exact executable probe commit is
`9572bad1c77b30cf8edef58d1619a94c869c835e`. A future probe needs a fresh GO
naming that exact reviewed commit, and a later B1-P1 final segment needs its
own separate GO after the probe is audited.

That single probe subsequently completed on phone-verified account `thgh15`.
It confirmed one Tesla P100, CUDA 12.8, and importable preinstalled PyTorch
2.10.0+cu128 at device-discovery level, but it did not execute a CUDA
tensor operation. Issue #125 later established that this build does not support
the P100's `sm_60` capability. Unsloth and bitsandbytes were absent, so the
environment was not ready for the frozen inference backend. See
`results/b1_b2_kaggle_runtime_probe_audit.md`. The probe accessed no private
input, loaded no model, and attempted no network access. Its authorization is
consumed. A future implementation must establish a P100-compatible PyTorch
stack and execute a CUDA tensor operation under a fresh no-private GO before a
separately authorized B1-P1 segment.

Issue #119 implements the resulting dependency-only smoke. It fails closed
unless the exact observed PyTorch 2.10.0+cu128, torchvision 0.25.0+cu128,
NumPy 2.0.2, CUDA 12.8, single-P100 base is present; installs only from public
PyPI under constraints that preserve that base; and import-checks Unsloth
2026.7.2 and bitsandbytes 0.49.2 without loading a model or touching private
input. The smoke returns a completed aggregate diagnostic even if dependency
resolution or import fails. Implementation does not authorize a kernel.
The exact executable dependency-smoke commit is
`3b28f99f4bbfe889ffaf56b1063ebfdc23a6ae72`.

That smoke subsequently completed installation, preserved the exact base
runtime, and imported both Unsloth and bitsandbytes. Its global `pip check`
returned one, however, and the diagnostic recorded only an output hash. See
`results/b1_b2_dependency_smoke_audit.md`. The run is therefore not a passing
final gate: a fresh no-private diagnostic must classify the conflict before
B1-P1 inference. The smoke authorization is consumed.

Issue #122's fresh no-input diagnostic classified every `pip check` complaint
as an unrelated preinstalled Kaggle-image conflict. None concerns the frozen
B1/B2 inference packages; installation, imports, CUDA, and the P100 base all
passed. See `results/b1_b2_pip_check_diagnostic_audit.md`. The dependency gate
is cleared. That diagnostic authorization is consumed and does not authorize
final inference.

Issue #109 subsequently authorized one B1-P1 segment on Kaggle account
`alba7oothresearchlab`. Kernel version 1 failed closed at approximately 1.07
seconds because the wrapper assumed an external `nvidia-smi` executable that
was unavailable. Server metadata recorded GPU enabled and the account had
30 GPU-hours remaining; CUDA availability was never measured. It did not reach
repository checkout, private-input access, model loading, inference, or a
metric. The authorization is consumed; this does not authorize a retry.

Issue #112 replaces that brittle assumption with
`python -m scripts.check_b1_b2_gpu_preflight`. The command uses PyTorch to
require CUDA, exactly one device, and a P100 identity before any private-input
access or model loading. It emits only aggregate runtime metadata. This repair
is implemented at exact executable commit
`f8c7ffd74993785f118bb32e0145295b31c5048d`; it must be merged and
independently reviewed before a fresh owner GO.

Issue #114 subsequently authorized one fresh B1-P1 attempt at the repaired
commit. It failed before repository checkout because Kaggle repeatedly could
not resolve `download.pytorch.org` during dependency installation. The repaired
GPU preflight and all research stages were never reached. Its authorization is
consumed; this does not authorize a retry.

Issue #125 subsequently authorized one B1-P1 attempt on account `thgh15` at
commit `87102633e0f1b76a2ee4d83a3e29e20de0da9137`. Repository,
GPU-identity, dependency, and private-artifact hash gates passed. The attempt
then failed at approximately 114.95 seconds because the exact private input
used the prepared-Nahw `id` field while `run_prompt_baseline` requires
`record_id`. The model was not loaded and no inference, prediction, or metric
occurred. The log also showed that PyTorch 2.10.0+cu128 does not support the
P100's `sm_60` capability; the current discovery-only preflight did not detect
that executable incompatibility. See
`results/b1_p1_8710263_r03_failure_audit.md`. This authorization is consumed.

Issue #127 implements the resulting repairs at exact code commit
`cb65e2f3143179d34034b661116220a011ffdddd`. The exact frozen 511-row
private artifact now passes the consumer contract through a deterministic
`id`-to-record-identity alias without changing its bytes. Conflicting aliases
fail closed. The P100 guard now executes and synchronizes a CUDA tensor
operation before private-input access. This was validated locally and with
synthetic tests only; a real P100 smoke remains required under a fresh,
no-input/no-model GO after merge. See
`results/b1_b2_preflight_repair_audit.md`.

Issue #130 then authorized exactly one no-input/no-model P100 operation smoke.
The exact commit checkout passed, and the repaired guard rejected the runtime
at approximately 8.58 seconds because installed PyTorch supports CUDA
architectures beginning at `sm_70` while the P100 is `sm_60`. No dataset or
model was attached and no private input, model loading, inference, training,
prediction, or metric occurred. See
`results/b1_b2_p100_operation_smoke_audit.md`. The authorization is consumed.
The current P100 runtime is not execution-ready; another B1 attempt is
ineligible until a reviewed compatible-runtime or accelerator repair passes a
separately authorized no-input executable smoke.

Issue #132 returns to the already successful F2/F3 P100 pattern instead of
changing accelerators. At exact code commit
`9bc36e31fe486350319f363f79bfca06dbb5e7af`, a conditional bootstrap
restores official PyTorch 2.6.0/torchvision 0.21.0 CUDA 12.4 wheels and the
recorded compatible inference stack, then validates identities, a real CUDA
operation, synchronization, and Unsloth/bitsandbytes imports in a fresh process
with Unsloth compilation disabled. See
`results/b1_b2_proven_p100_runtime_restore_audit.md`. This was implemented and
tested without Kaggle execution. A separately authorized no-input/no-model
smoke remains required after merge.

Issue #135's single no-input/no-model restored-runtime smoke then completed in
approximately 268 seconds. All exact restored identities matched, the P100 CUDA
operation and synchronization passed, and Unsloth/bitsandbytes imported with
compilation disabled. See `results/b1_b2_restored_p100_smoke_audit.md`. The
authorization is consumed. The runtime blocker is cleared, but no B1/B2
evaluation is authorized.

Issue #137 adds a deterministic, write-once generator for one private B1-P1
final segment. The generated wrapper verifies the exact approved checkout,
runs the passing restored-P100 gate before private-input discovery, verifies
the frozen input and bundle hashes, and invokes the existing timeout-safe
runner. See `results/b1_p1_timeout_safe_kernel_preparation_audit.md`. This
preparation authorizes no Kaggle submission or inference.

## Decision

Issue #107 implements the required timeout-safe persistence and exact-prefix
continuation controls without changing either frozen prompt, demonstration
bundle, parser, decoding setting, input, statistic, or canonical run identity.
The exact executable implementation is
`16b4ca3dec6e757b41e233b22bc16cc6a57be4dd` in PR #108.
The gate remains disabled and must not be submitted until the implementation is
merged, independently reviewed at its exact commit, and named by a fresh
single-use owner GO.

## Completed prerequisites

- B1-P1 and B2-P1 prompts are frozen in `docs/prompt_baseline_protocol.md`.
- The deterministic B1-P1 five-demonstration selection is frozen.
- The private B1-P1 prompt bundle exists under ignored storage and has the
  expected SHA-256
  `760674f0d6cc85c48b2be18d175b87e2025cd3d01fde31a6e25afaa08f9fc11a`.
- The selected B1 candidate-identity digest is
  `76edd4c3de4b6cb5a985464faa066dea40faf9b25b8fa2912b3bf9c4750a9e8c`.
- Both protocols completed the same 25-record QALB-2014 L1 development
  technical gate with zero empty/invalid outputs.
- The frozen prepared Nahw-Passage test input is locally available under
  ignored storage with SHA-256
  `acb3cfd204b35d5415532fbd32a4a5231b553fae329ab8f48e8454609e10279b`.
- The exact artifact passes `run_prompt_baseline` through the reviewed,
  deterministic `id` alias without changing its bytes; conflicting identity
  aliases fail closed.
- Prompt assembly, parsing, canonical run paths, non-overwrite behavior, and
  disabled final-test gating have unit coverage.
- Neither B1-P1 nor B2-P1 has accessed Nahw-Passage.

No private bundle text, test text, prompt, response, or record-level artifact
was read or printed during this readiness review.

## Implemented engineering safety

`scripts/run_prompt_baseline.py` now provides:

1. a required wrapper-start epoch captured before setup or network work;
2. a PyTorch CUDA/P100 preflight before private-input access;
3. a fixed 34,200-second safe-stop threshold below Kaggle's hard cutoff;
4. one flushed and `fsync`-ed private JSONL row after every completed record;
5. an atomically replaced corpus-text-free progress manifest;
6. a successful `incomplete_time_budget` state that reports counts and hashes
   but no partial metric;
7. a resume loader that verifies the exact input, protocol, bundle, prompt,
   model revision, completed prefix, schema, order, score consistency, and
   prediction hash before copying it;
8. skip logic that never regenerates a completed record;
9. an exact approved commit and fresh Musahhih issue-comment GO for every
   submitted segment;
10. first-terminal-state preservation with no automatic retry; and
11. private outputs under ignored paths only.

Synthetic-fixture tests cover interruption, identity and hash mismatch,
malformed schemas, reordered records, score mismatch, unexpected existing
directories, and successful multi-segment completion without reading
Nahw-Passage or loading a model. They did not validate the exact frozen private
input against the consumer schema or execute a CUDA tensor operation on the
selected runtime; issue #125 proved both omissions are blocking.

## Proposed execution shape

The preferred design is one state machine with the frozen order:

1. complete or resume B1-P1;
2. release the model and GPU memory;
3. complete or resume B2-P1;
4. only after both arms reach 511/511, compute their individual metrics and
   staged comparisons to accepted B0/F1/F2/F3 outcomes.

If the safe-stop threshold is reached, publish no partial score and require a
new owner GO for the next exact-prefix continuation. B1-P1 and B2-P1 must retain
separate private prediction files and canonical experiment identities.

The final comparison to already observed fine-tuned systems is necessarily
staged. It must not be described as a simultaneously preregistered experiment.

## Frozen fields that implementation may not change

- B1-P1 demonstration records, order, and bundle hash;
- B1-P1 and B2-P1 prompt bytes;
- base model ID and immutable revision;
- Nahw-Passage input hash and 511-record order;
- parser and exact-match rule;
- seed 3407;
- greedy decoding with no temperature argument;
- maximum 32 new tokens;
- protocol IDs and run naming;
- no adapters or model-weight changes; and
- no prompt selection based on B1/B2 final outcomes.

## Authorization boundary

This review does not authorize implementation to inspect Nahw-Passage, model
loading, inference, Kaggle submission, or a retry. A future sequence requires:

1. merge the timeout-safe code after synthetic/static validation;
2. independently review the exact merge commit;
3. obtain an owner GO naming that commit, one protocol, and one segment;
4. capture the private wrapper start time as its first executable operation;
5. preserve and audit that segment's first terminal state; and
6. obtain a new owner GO before any continuation.
