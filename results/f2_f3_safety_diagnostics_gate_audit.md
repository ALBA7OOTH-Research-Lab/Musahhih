# F2/F3 behavioral-diagnostics gate preparation audit

Recorded: 2026-08-02
Status: repository preparation complete on issue #200; no diagnostic executed

## Frozen scope

The gate extends the completed F1 behavioral design to the original frozen
seed-3407 F2-P1 and F3-P1 adapters. It reuses exactly:

- 154 QALB-2015 L2 development corrected-target records for designated-token
  overcorrection;
- the balanced 1,000-record, 40-task ArabicMMLU subset for capability; and
- the immutable B0/F1-P1 record-level diagnostic predictions as staged
  references, without rerunning either system.

The primary new paired comparisons are F3-P1 minus F2-P1 unchanged-token
accuracy and ArabicMMLU micro accuracy. B0/F1-P1 comparisons remain explicitly
staged. No Nahw-Passage system is repeated: a post-hoc common-date rerun would
not make the original study preregistered or simultaneous.

## Identity checks

Read-only local SHA-256 checks confirmed the already prepared private inputs and
original selected adapters without printing or interpreting record content:

| Artifact | SHA-256 |
| --- | --- |
| QALB-development overcorrection input | `fa0c3f7a5321ae0a97528aaaf8df0ac29fce0039d3fad9b1e3cf83de71ac2036` |
| Balanced ArabicMMLU input | `ff6d250150016a4a9d18248bd7af632d67c14a978c87ccb3e50cb2d28d4e9f9a` |
| F2-P1 checkpoint-125 adapter model | `935fdf02c95189934e40629f877d8692d325ef22895cbaa03fdb7390b0cd7b3e` |
| F2-P1 adapter config | `b07ab34155647961ea1de8fbfff0db8e17d00229da01f2b941a15a78499da986` |
| F3-P1 checkpoint-250 adapter model | `95bd333caac28e08b40fcafe7bc033f323188e817d7c16ecbe7745b34c1b44dc` |
| F3-P1 adapter config | `917893c00ea8f02f784ce21db4448b774e6a892fede6f484da18606bca884c21` |

The evaluator additionally gates the existing checkpoint-selection artifacts
and the four accepted B0/F1-P1 prediction hashes before any aggregate is
released.

## Safety and failure behavior

- execution is disabled by default;
- the exact merged commit, an issue-#200 GO URL, and an exact confirmation are
  mandatory;
- the proven P100-compatible runtime and synchronized CUDA-operation preflight
  run before diagnostic input discovery;
- each adapter is loaded fresh, unmerged, and released before the next arm;
- every private prediction/logit row is flushed and `fsync`ed;
- progress is atomically updated after every record;
- a 34,200-second safe stop produces a metric-free
  `incomplete_time_budget` handoff;
- continuation validates hashes, schema, scores, order, stage boundaries, and
  runtime, never regenerates completed records, and requires a fresh GO;
- complete aggregates contain no prompts, questions, target tokens, raw
  responses, logits, record identifiers, or adapter paths; and
- no per-task ArabicMMLU table is public by default.

## Validation

- `python -m compileall scripts`: passed;
- focused F2/F3 diagnostic tests: 12 passed;
- complete repository suite: 328 passed after the immutable-reference and
  exact-hash continuation extensions;
- generated Kaggle wrapper compilation and metadata parsing: passed;
- `git diff --check`: passed.

No GPU was allocated. No model was loaded. No inference, diagnostic metric,
training, checkpoint selection or reselection, Nahw-Passage, QALB test,
linguistic labeling, or XG occurred. Execution requires review, merge, and a
fresh exact-commit owner GO.
