# B1-P1/B2-P1 final-gate readiness review

Status updated: 2026-07-27. Network-safe runtime probe in review; no execution
authorized.

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

Synthetic-fixture tests cover interruption, identity and hash mismatch, malformed
schemas, reordered records, score mismatch, unexpected existing directories,
and successful multi-segment completion without reading Nahw-Passage or loading
a model.

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
