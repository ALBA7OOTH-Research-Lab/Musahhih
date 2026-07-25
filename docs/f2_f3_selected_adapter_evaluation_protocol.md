# F2-P1/F3-P1 matched selected-adapter evaluation protocol

Status: the original gate merged at `22cc89164b4ad00476c91cb29f95e9e34e6f56b3`.
Its single authorized kernel reached Kaggle's hard runtime cutoff after roughly
40,000 seconds and ended `CANCEL_ACKNOWLEDGED`, with no output downloaded and no
metric reported. Issue #98 adds an unexecuted timeout-safe handoff repair. This
document and its implementation do not authorize Nahw-Passage inference.

## Purpose and research position

This protocol defines the single matched final evaluation of the selected
synthetic-only F2-P1 and mixed natural/synthetic F3-P1 adapters. Both are
evaluated on the same 511 test-only Nahw-Passage records in one private P100
runtime.

F1-P1 and B0 Nahw-Passage results were already known when the Tibyan-derived
F2/F3 companion study was frozen. Those results did not choose the F2/F3 data,
prompt, parser, training settings, checkpoints, or evaluation settings. The
paper must disclose this staged timing and must not call the full F1/F2/F3
comparison simultaneously preregistered.

The private F2/F3 development metrics remain blinded. They must not select an
arm, change this protocol, or determine whether either frozen adapter receives
final evaluation.

## Frozen systems

Common settings:

- base model: `unsloth/gemma-3-4b-it-unsloth-bnb-4bit`;
- base revision: `316726ca0bd24aa323bfaf86e8a379ee1176d1fe`;
- unmerged LoRA attached for inference to a 4-bit base;
- LoRA rank/alpha/dropout: `16/32/0.0`, bias `none`;
- the same seven projection targets used for F1;
- maximum sequence length: 2,048;
- seed: 3,407.

F2-P1:

- selected private checkpoint: `checkpoint-125`;
- adapter-model SHA-256:
  `935fdf02c95189934e40629f877d8692d325ef22895cbaa03fdb7390b0cd7b3e`;
- adapter-config SHA-256:
  `b07ab34155647961ea1de8fbfff0db8e17d00229da01f2b941a15a78499da986`;
- checkpoint-selection SHA-256:
  `39edee5e31d79c791a4ab0b14b7b85b838e28bcc302d9e552f168a03ac870e1b`.

F3-P1:

- selected private checkpoint: `checkpoint-250`;
- adapter-model SHA-256:
  `95bd333caac28e08b40fcafe7bc033f323188e817d7c16ecbe7745b34c1b44dc`;
- adapter-config SHA-256:
  `917893c00ea8f02f784ce21db4448b774e6a892fede6f484da18606bca884c21`;
- checkpoint-selection SHA-256:
  `b4d1deda9b01b82b07abd2a21e999f92e132604ca0c8463830edd8d43dedfa81`.

All three hashes for both adapters must match before final-test data is loaded
or a model is constructed. The evaluator must verify the selected checkpoint,
base-model identity, LoRA configuration, target modules, and two frozen
checkpoint evaluations.

## Frozen test and reference artifacts

- dataset: Nahw-Passage, official `test`, exactly 511 records;
- prepared JSONL SHA-256:
  `acb3cfd204b35d5415532fbd32a4a5231b553fae329ab8f48e8454609e10279b`;
- accepted B0 record-level predictions SHA-256:
  `6997b6fe5959f5502511ebdd1885d05a89ebaefeb27eefb73520842598f36ebc`;
- accepted F1-P1 record-level predictions SHA-256:
  `8c4d0ca25b48776a08ea02984af6c5c3ec0bc830d2d1a6994e0fb5eef995faa3`.

The evaluator must verify all 511 unique IDs and exact ID alignment across the
test records, B0, F1-P1, F2-P1, and F3-P1. It must reuse the stored B0 prompt
exactly. There are no demonstrations or adapter-specific instructions.

## Frozen inference

- private free Kaggle NVIDIA P100 environments;
- order: complete F2-P1 first, release it, then load and complete F3-P1;
- greedy decoding with `do_sample=False`;
- no temperature argument;
- `max_new_tokens=32`;
- unchanged `scripts.nahw_baseline_utils.parse_model_response`;
- no Arabic normalization, truncation, or score-aware repair.

There is no Nahw-Passage pilot. The completed private development smokes already
validated loading, generation, parsing, serialization, and artifact handling on
non-test records.

### Timeout-safe handoff

The private wrapper must capture Unix epoch time at its first executable line
and pass it as `--kernel-start-epoch-seconds`. The evaluator stops before
starting another record once 34,200 seconds (9.5 hours) have elapsed. This
leaves approximately 5,800 seconds before the cutoff observed in the cancelled
issue #96 attempt.

Every private prediction row is flushed and `fsync`-ed before progress advances.
After every row, the evaluator atomically replaces `progress.json`, which
contains only record counts, private-file hashes, runtime metadata, elapsed
time, frozen identities, and safety flags. It contains no corpus text,
responses, corrections, record IDs, or metrics.

A timed stop returns successfully with `run_status=incomplete_time_budget`,
allowing Kaggle to preserve the private output. It reports no metric. A later
kernel may continue only from that private output, only after a new exact-commit
owner GO on issue #98. The continuation verifies the prior summary, manifest,
protocol commit, counts, hashes, exact ordered record prefix, stored prompt and
gold fields, parser output, and score consistency before copying the prefix. It
starts at the first unfinished record and never regenerates a completed record.

## Frozen outcomes and comparisons

For each arm, retain exact-word accuracy, invalid/empty count, parser-warning
counts, suspicious-output count, multi-token count, and prediction SHA-256.

The primary new comparison is `F3-P1 minus F2-P1`. Report:

- accuracy difference;
- F2-wrong/F3-right and F2-right/F3-wrong discordant counts;
- two-sided exact McNemar/binomial p-value; and
- deterministic 10,000-sample paired-bootstrap percentile 95% interval with
  seed 3,407 and linear percentile interpolation.

The following are staged secondary comparisons using the same frozen method:

- F2-P1 minus accepted B0;
- F3-P1 minus accepted B0;
- F2-P1 minus accepted F1-P1;
- F3-P1 minus accepted F1-P1.

Report the secondary comparisons transparently without relabeling them as the
primary confirmatory contrast. Do not add subgroups, normalization, alternative
tests, or preferred examples after results are seen. Exact match is strict and
does not establish that alternate corrections are linguistically invalid.

## Execution authorization

The committed evaluator is disabled unless `--execute` is supplied. Before it
may load final-test data, all of the following are required:

1. this protocol and implementation pass CI and merge;
2. an independent owner review posts a new GO or NO-GO comment on issue #98;
3. a GO names the exact 40-character merged commit and exactly one matched
   F2/F3 final run;
4. the executor supplies that issue-comment URL, the exact commit, and
   confirmation `RUN_F2_F3_MATCHED_NAHW_FINAL_511_TIMEOUT_SAFE`;
5. the repository checkout equals the approved commit exactly; and
6. both private adapters, test input, B0 predictions, and F1 predictions pass
   every frozen hash and schema check; and
7. any continuation supplies only the immediately preceding timed handoff and
   passes all private-prefix validation before new inference.

Preparation, compilation, synthetic tests, `--help`, and disabled invocation
must not read Nahw-Passage, reference predictions, private development metrics,
or adapter files. Passing software gates is not execution authorization.

## Failure and retry rules

- Use only logical replicate `r01`; never overwrite a run directory.
- Preserve the first terminal state and every partial private artifact.
- A planned `incomplete_time_budget` handoff is not a completed evaluation and
  publishes no metric. Preserve it privately.
- Continuing a timed handoff requires a fresh exact-commit owner GO. The owner
  decision may use only corpus-text-free counts, hashes, and execution
  diagnostics, not partial scores or qualitative outputs.
- A continuation is part of logical replicate `r01`, not a new replicate. It
  must copy the verified prefix byte-for-byte and skip every completed record.
- A failure before any model response may be retried only after documenting
  the cause and obtaining a fresh exact-commit owner decision.
- A failure after any F2 or F3 response exists is result-bearing. Do not patch,
  retry, or complete the other arm without independent protocol review and a
  new explicit authorization.
- A completed two-arm run is never repeated because of scores, warnings,
  suspicious responses, or qualitative inspection.
- A scientific-setting change is a new protocol, not a technical retry.

## Private and public artifacts

The ignored private run directory contains:

```text
outputs/F2-F3__gemma3-4b-it__nahw-passage__s3407__r01/
  f2-p1_predictions.jsonl
  f3-p1_predictions.jsonl
  progress.json
  public_summary.json
  run.log
```

Prediction rows retain test text, gold corrections, prompts, raw responses,
parsed corrections, warnings, and exact-match flags. They remain private.
`progress.json` is a private handoff manifest even though it is corpus-text-free.

The summary contains only identities, hashes, runtime metadata, aggregate
metrics, paired statistics, and safety flags. Audit it for corpus text before
committing a reviewed copy under `results/`.

## Prohibited scope

Do not read the hidden F2/F3 development metrics, run QALB test, repeat F1,
rerun safety diagnostics, train, merge adapters, change checkpoints, tune the
prompt or parser, normalize outputs, activate XG, publish private records or
adapter bytes, or claim expert linguistic validation.
