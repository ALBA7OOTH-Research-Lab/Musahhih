# B1-P1/B2-P1 final-gate readiness review

Status updated: 2026-07-26. Implementation prepared; no execution authorized.

## Decision

Issue #107 implements the required timeout-safe persistence and exact-prefix
continuation controls without changing either frozen prompt, demonstration
bundle, parser, decoding setting, input, statistic, or canonical run identity.
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
2. a fixed 34,200-second safe-stop threshold below Kaggle's hard cutoff;
3. one flushed and `fsync`-ed private JSONL row after every completed record;
4. an atomically replaced corpus-text-free progress manifest;
5. a successful `incomplete_time_budget` state that reports counts and hashes
   but no partial metric;
6. a resume loader that verifies the exact input, protocol, bundle, prompt,
   model revision, completed prefix, schema, order, score consistency, and
   prediction hash before copying it;
7. skip logic that never regenerates a completed record;
8. an exact approved commit and fresh Musahhih issue-comment GO for every
   submitted segment;
9. first-terminal-state preservation with no automatic retry; and
10. private outputs under ignored paths only.

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
