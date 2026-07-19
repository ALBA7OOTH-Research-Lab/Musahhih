# F1-P1 capability-retention and overcorrection protocol

Status: proposed freeze for issue #63. No corresponding model inference is
authorized by this document alone.

## Questions

This protocol adds two development/safety diagnostics after the completed F1-P1
Nahw-Passage evaluation:

1. Does the selected natural-data adapter unnecessarily change a token that is
   already correct in its sentence?
2. Does the adapter change general Arabic multiple-choice performance relative
   to the untouched model?

These diagnostics do not reopen checkpoint selection. Their results must not be
used to revise F1-P1, its prompt, parser, training data, or completed test result.

## Frozen systems and matched execution

Compare two systems:

- `B0`: untouched `unsloth/gemma-3-4b-it-unsloth-bnb-4bit` at revision
  `316726ca0bd24aa323bfaf86e8a379ee1176d1fe`;
- `F1-P1`: the same immutable 4-bit base with private `checkpoint-250`, adapter
  config SHA-256
  `db19ef8bf4852698103dde20cd50b4429ca102ac96980f7939ecc4cff2049c4d`
  and checkpoint-selection SHA-256
  `898c19d5dcead1f6c8f0ed27b6e8c5c6b9ebaec2f1b2a9909e58d8c9758ee123`.

Run B0 and F1-P1 in one private free Kaggle P100 kernel with the same Python,
CUDA, package stack, processor, sequence limit, record order, and scoring code.
Load a fresh immutable base for each system; do not attach F1 to the in-memory B0
instance. Do not train, merge, or alter the adapter.

Freeze the matched runtime to Python 3.12.13, CUDA 12.4, PyTorch 2.6.0+cu124,
Transformers 4.56.2, Unsloth 2026.7.3, Accelerate 1.13.0, PEFT 0.19.1, and
TRL 0.22.2 on one Tesla P100-PCIE-16GB. The maximum sequence length is 2,048.
Any mismatch fails before loading or scoring records.

## Overcorrection diagnostic

### Data

Use only `QALB-2015-L2-Dev.m2` and its paired `.cor` file, never QALB test. Their
frozen SHA-256 values are respectively
`026e2b2164cb8b9da16f40fefc77b582384f2b6c7db3e9a1673494d776b00c0f`
and `a1bf62ea4a14290d0a69cddebe793d2abe8d94bbceb59f294b76714547217f20`.
They contain 154 sentences with annotator `0` edits. Require every reconstructed
M2 target to equal the official `.cor` target after removal of its `S ` format
prefix.

The frozen prepared JSONL SHA-256 is
`fa0c3f7a5321ae0a97528aaaf8df0ac29fce0039d3fad9b1e3cf83de71ac2036`.

For every sentence, reconstruct the annotator-0 gold target by applying all M2
edits to the tokenized source in reverse span order. Reject malformed,
overlapping, out-of-range, or multi-annotator input. From the reconstructed
target, retain tokens containing at least one Unicode Arabic-script code point.
Choose exactly one eligible token by sorting candidates on
`SHA256("F1-overcorrection|3407|<record-id>|<position>")` and taking the first.
The hash rule does not inspect the token spelling or any model output.

The input passage is the complete reconstructed target. The designated token is
already present in that passage, and the expected output is the same exact token.
Use the frozen B0 correction prompt and conservative parser. Preserve strings
exactly; do not normalize Arabic letters, diacritics, punctuation, or Unicode.

### Inference and outcomes

- greedy decoding: `do_sample=False`, no temperature argument;
- `max_new_tokens=32`, seed 3407;
- retain prompt, raw response, parsed response, warnings, target token, and exact
  unchanged result privately for every record.

Primary per-system outcome: unchanged-token accuracy. Overcorrection rate is
`1 - unchanged-token accuracy`; invalid or suspicious output counts as not
unchanged. Harmless surrounding formatting removed by the already frozen parser
is retained as a warning but is not suspicious. Primary comparison: paired
F1-P1 minus B0 unchanged accuracy, with
discordant counts, exact two-sided McNemar p-value, and a deterministic 10,000-
sample paired-bootstrap 95% percentile interval (seed 3407).

This is an independently selected development diagnostic, not an official QALB
test result. Gold-corrected learner sentences may still contain unannotated or
alternate issues; no claim of flawless or expert-validated Arabic is made.

## General Arabic capability diagnostic

### Data and license

Use the official `MBZUAI/ArabicMMLU` dataset, CC BY-NC 4.0, pinned at revision
`7aa530e2893ac420352b3f5c1a1310c010e9758b`. The benchmark contains 14,575
original Arabic multiple-choice questions across 40 tasks. The official `dev`
split contains 120 few-shot examples and the official `test` split contains
14,455 questions. Do not use `dev` demonstrations in this zero-shot diagnostic.

Select exactly 25 test questions from each of the 40 task directories, excluding
the aggregate `All/` duplicate. For each task, sort rows by
`SHA256("F1-capability|3407|<task>|<ID>")` and take the first 25. The selection
does not inspect answer keys, question text, or model output. The resulting
balanced set contains exactly 1,000 questions. Record the per-file hashes,
selected identity hash, and prepared JSONL hash before inference.

The frozen prepared JSONL SHA-256 is
`ff6d250150016a4a9d18248bd7af632d67c14a978c87ccb3e50cb2d28d4e9f9a`.
It contains 108 two-choice, 111 three-choice, 757 four-choice, and 24
five-choice questions. The canonical 40-file source-manifest SHA-256 is
`bd4c4ea40f5871fbd8055284ae83f1af93f2416b15e7a2817a86388f9d5be65b`.

### Prompt, scoring, and outcomes

Reuse the official zero-shot English-prompt/Latin-answer format implemented by
EleutherAI's `lm-evaluation-harness` ArabicMMLU task, pinned for reference at
commit `f4d4b3de3ee6741a7151a9fe74945ee515262f4c`. Use its prompt wording and
choice order exactly. Do not add demonstrations or optimize the prompt.

Score the next-token logits for the available ordered Latin answer-letter prefix
(`A`-`B` through `A`-`E`) after the chat-formatted prompt. Before scoring,
require every candidate letter `A` through `E` to tokenize to exactly one
distinct token under the pinned processor.
Choose the highest logit; ties choose the earliest displayed option. There is no
sampling, generated explanation, random fallback, or answer-aware parsing.

Primary outcome: micro accuracy over the 1,000 balanced questions. Primary
comparison: paired F1-P1 minus B0 accuracy. Report per-task accuracy only as a
pre-specified descriptive table. Use a stratified paired bootstrap: within each
of the 40 tasks, resample its 25 paired records with replacement, combine all
1,000 differences, repeat 10,000 times with seed 3407, and report the 95%
percentile interval. Also report discordant counts and the exact two-sided
McNemar p-value.

This diagnostic measures observed multiple-choice retention on the selected
balanced subset. It is not the full ArabicMMLU leaderboard result and cannot
establish broad Arabic intelligence or benchmark non-inferiority. Possible
ArabicMMLU contamination in the base model's pretraining is unknown. Because the
subset comes from the official test split, neither its aggregate nor per-task
results may be used to tune prompts, scoring, checkpoints, or model decisions.

## Artifacts and privacy

Derived QALB records, prompts, adapter artifacts, and all record-level model
outputs remain under ignored `data/processed/` or `outputs/` and in private
Kaggle storage. ArabicMMLU remains subject to CC BY-NC 4.0 attribution. Commit
only text-free selection/run summaries and aggregate results.

Every run summary records the Git commit, approval reference, source and
selection hashes, base/adapter hashes, runtime/package versions, GPU, processor,
prompt/scoring implementation, counts, metrics, prediction hashes, and warnings.

## Authorization, failure, and retry rules

1. Preparation code, evaluator, tests, and this protocol must be merged.
2. A reviewer must post GO or NO-GO naming the exact merged commit.
3. A separate execution issue must identify the approved commit, inputs,
   adapter, runtime, run IDs, and approval reference.
4. The private execution must require an exact confirmation string and refuse
   existing run directories.

The matched run ID is
`F1-P1__gemma3-4b-it__safety-diagnostics__s3407__r01`; later replicates are
allowed only by the failure rule below. The execution confirmation is exactly
`RUN_MATCHED_F1_SAFETY_DIAGNOSTICS`.

Preserve failures as `invalid`. A failure before any response/logit result may
be repaired and retried only after documenting it; use the next replicate. A
failure after any record result stops both matched systems pending independent
review. Never repeat a complete comparison because of its score.

## Prohibited actions

- no Nahw-Passage or QALB test access;
- no training, checkpoint reselection, prompt tuning, parser tuning, threshold
  tuning, or data selection from model results;
- no XG/F2/F3 activation before qualified linguistic review;
- no expert linguistic claim, invented Arabic label, paid dependency, secret,
  private-data publication, or adapter publication.
