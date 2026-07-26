# Proposed F2-P1/F3-P1 capability-retention and overcorrection protocol

Status: issue-#104 planning draft. Not frozen, implemented, or authorized.

## Purpose

The completed final evaluation established that mixed F3-P1 outperformed
synthetic-only F2-P1 on highlighted-token Nahw-Passage correction. It did not
measure whether either adapter unnecessarily changes already-correct tokens or
changes selected general Arabic multiple-choice performance.

This proposal extends the already completed F1-P1 safety design without
reopening training, checkpoint selection, prompts, parsing, or final-test
decisions.

## Systems

Evaluate only the two frozen private adapters in one matched execution:

- F2-P1 private `checkpoint-125`:
  - adapter model SHA-256
    `935fdf02c95189934e40629f877d8692d325ef22895cbaa03fdb7390b0cd7b3e`;
  - adapter config SHA-256
    `b07ab34155647961ea1de8fbfff0db8e17d00229da01f2b941a15a78499da986`;
  - checkpoint-selection SHA-256
    `39edee5e31d79c791a4ab0b14b7b85b838e28bcc302d9e552f168a03ac870e1b`.
- F3-P1 private `checkpoint-250`:
  - adapter model SHA-256
    `95bd333caac28e08b40fcafe7bc033f323188e817d7c16ecbe7745b34c1b44dc`;
  - adapter config SHA-256
    `917893c00ea8f02f784ce21db4448b774e6a892fede6f484da18606bca884c21`;
  - checkpoint-selection SHA-256
    `b4d1deda9b01b82b07abd2a21e999f92e132604ca0c8463830edd8d43dedfa81`.

Use the same immutable 4-bit base model revision
`316726ca0bd24aa323bfaf86e8a379ee1176d1fe`. Load a fresh base for each arm,
attach the verified adapter without merging, evaluate, release it, and clear GPU
memory before the next arm.

Do not rerun B0 or F1-P1. Their accepted record-level safety predictions remain
private immutable staged references. Repeating F1-P1 is prohibited by its
completed protocol.

## Frozen diagnostic inputs proposed for reuse

Preparation and implementation must use only the existing ignored prepared
inputs and their identities. Do not select new records or inspect content while
designing this extension.

### Overcorrection

- source role: QALB-2015 L2 development corrected targets;
- records: 154;
- prepared JSONL SHA-256:
  `fa0c3f7a5321ae0a97528aaaf8df0ac29fce0039d3fad9b1e3cf83de71ac2036`;
- prompt, parser, decoding, target selection, and unchanged-token scoring:
  exactly the completed F1-P1 safety protocol.

### General Arabic capability

- source: MBZUAI/ArabicMMLU, pinned revision
  `7aa530e2893ac420352b3f5c1a1310c010e9758b`;
- selection: the existing 25 records per task across 40 tasks;
- records: 1,000;
- prepared JSONL SHA-256:
  `ff6d250150016a4a9d18248bd7af632d67c14a978c87ccb3e50cb2d28d4e9f9a`;
- prompt, Latin answer-letter token checks, next-token-logit scoring, task
  strata, and choice handling: exactly the completed F1-P1 safety protocol.

QALB test, Nahw-Passage, ArabicMMLU development demonstrations, new sampling,
new thresholds, and new prompt variants are prohibited.

## Proposed run order and timeout safety

Use one private P100 workflow with this fixed order:

1. F2-P1 overcorrection;
2. F2-P1 ArabicMMLU;
3. release F2-P1 and its base;
4. F3-P1 overcorrection;
5. F3-P1 ArabicMMLU;
6. compute aggregate comparisons only after both systems complete both
   diagnostics.

The workflow must be timeout-safe before submission:

- capture the kernel start time from the private wrapper's first executable
  line;
- use a conservative safe stop no later than 34,200 elapsed seconds;
- flush and `fsync` every private prediction/logit row;
- atomically update a corpus-text-free progress manifest;
- preserve exact per-stage counts and hashes;
- return `incomplete_time_budget` without metrics if any stage is incomplete;
- resume only from the immediately preceding hash-verified prefix;
- never regenerate a completed record;
- require a fresh exact-commit owner GO for every segment; and
- preserve the first terminal state with no automatic retry.

Because the ArabicMMLU task scores logits rather than generated text, resume
validation must verify the candidate set, candidate-token identities, stored
finite logits, selected answer, correctness boolean, task, and ordered record
identity without printing question text or answers.

## Proposed outcomes and comparisons

### Overcorrection endpoint

Per system:

- unchanged-token exact count and accuracy;
- overcorrection rate;
- empty/invalid count;
- suspicious-output count; and
- warning counts.

Primary new comparison: F3-P1 minus F2-P1 unchanged-token accuracy.

Staged secondary comparisons:

- F2-P1 minus accepted B0;
- F3-P1 minus accepted B0;
- F2-P1 minus accepted F1-P1; and
- F3-P1 minus accepted F1-P1.

For each comparison, report aligned discordant counts, exact two-sided McNemar
p-value, and a deterministic 10,000-sample paired-bootstrap 95% percentile
interval using seed 3407.

### Capability endpoint

Per system:

- micro accuracy over 1,000 questions; and
- descriptive per-task accuracy for the fixed 40 tasks.

Primary new comparison: F3-P1 minus F2-P1 micro accuracy.

Use the same staged secondary systems as the overcorrection endpoint. Report
discordant counts, exact two-sided McNemar p-value, and the existing
40-task-stratified 10,000-sample paired-bootstrap interval with seed 3407.

The two endpoints answer different safety questions. Do not combine them into
one score, select an adapter from them, or represent the diagnostic as a formal
non-inferiority trial.

## Interpretation rules

- A confidence interval spanning zero is insufficient evidence of a
  difference.
- Absence of a detected ArabicMMLU difference is not proof that capability was
  preserved on all Arabic tasks.
- The QALB diagnostic estimates behavior on deterministically selected tokens
  in corrected development sentences; it is not an official QALB metric.
- Accepted B0/F1-P1 references predate this extension. Comparisons to them are
  staged and may include package/runtime differences even though data and
  scoring identities are frozen.
- Results may not change F2-P1/F3-P1 checkpoints, prompts, training data, the
  completed Nahw result, or paper inclusion decisions made from development
  evidence.

## Artifacts and privacy

Keep all prepared inputs, prompts, questions, answer choices, gold answers,
raw responses, parsed responses, logits, predictions, adapters, and logs under
ignored local/Kaggle private paths. Public artifacts may contain only:

- input and prediction hashes;
- counts and aggregate metrics;
- paired statistics;
- package/runtime metadata;
- text-free per-task counts if license review permits; and
- explicit safeguards and staged-comparison caveats.

ArabicMMLU remains CC BY-NC 4.0. QALB remains research-restricted. Preserve
their existing attribution and privacy controls.

## Required review decisions before implementation

1. Confirm that the paper needs F2/F3 safety diagnostics.
2. Approve or revise the proposed F3-minus-F2 primary comparisons.
3. Decide whether staged comparisons to both accepted B0 and F1-P1 are useful
   enough to justify their runtime/package caveat.
4. Review the multi-segment ordering and safe-stop threshold.
5. Approve the public per-task reporting policy for ArabicMMLU.

Only after those decisions may a dedicated implementation issue add code and
synthetic tests. Implementation must merge before an independent exact-commit
GO. This draft authorizes no data access, model loading, inference, or Kaggle
submission.
