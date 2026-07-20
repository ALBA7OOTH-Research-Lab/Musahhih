# Tibyan-derived F2/F3 matched protocol

Status: frozen methodology and data-composition protocol. The canonical private
manifest build and processor-length validation passed, and exact merged commit
`8ca3014e6b3659e2e8c3ffc519b0255e9af6b7a6` received GO on issue #67. This
approval authorized guarded workflow implementation only. GPU smoke, training,
model inference, checkpoint selection, and final-test access require their own
later exact-commit/stage approvals.

GitHub issue: https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/67

## Purpose and scope

This protocol defines the proposed released-synthetic (`F2-P1`) and mixed
natural/released-synthetic (`F3-P1`) arms that complete Musahhih's core matched
comparison with the completed natural-only `F1-P1` pilot. It uses the released
Tibyan sentence pairs; it does not activate the project-generated `XG` operator
or create new Arabic errors.

| Arm | Frozen training composition | Total records |
| --- | --- | ---: |
| `F1-P1` | existing QALB-2014 L1 natural selection | 2,000 |
| `F2-P1` | Tibyan-derived highlighted-token selection | 2,000 |
| `F3-P1` | 1,000 frozen F1 records plus 1,000 frozen F2 records | 2,000 |

This is a staged extension. The F1-P1 Nahw-Passage and safety-diagnostic results
were already known when this companion protocol was written. Those results must
not select the Tibyan source, extraction rule, record count, mixture, prompt,
hyperparameters, checkpoint, or evaluation settings. Any paper must disclose
the staged timing and must not describe all three arms as simultaneously
preregistered.

## Authoritative source and attribution

- dataset: `Tibyan-corpus`;
- Zenodo record: `14623621`, DOI `10.5281/zenodo.14623621`;
- license: CC BY 4.0;
- release file: `Data (1).rar`, 5,614,320 bytes;
- archive SHA-256:
  `a7f318d9c64d7d2c214a5f44ee515b70c7d1ee930178b4b6b00cf5c733b0dfda`;
- final corrected file SHA-256:
  `5f8fde9319df89419ade12114f14466301cafb181ce807df896fb5de2361c4e4`;
- final erroneous file SHA-256:
  `e3b72a45abffbf2a63da07912adc0fa0b29a41c495d609aa2b917fc4d58956a6`;
- expected final lines: 6,192 on each side, paired by one-based line number.

Use must cite the dataset and paper, link the license, and state that Musahhih
changes the released sentence pairs into a highlighted-token training view.
The paper describes professional/linguistic review of the released corpus.
Musahhih has not independently reproduced that review and must not call the
derived token alignments expert gold labels.

The paper's 618,598/604,592 word totals differ from the repository audit's
simple whitespace counts of 596,749/572,572. Preserve both statements with
their definitions; do not silently replace the published counts.

## Exact-text contract

Read both final files as UTF-8 with optional BOM handling. Preserve every line,
Arabic letter, diacritic, punctuation mark, and whitespace sequence. Whitespace
tokenization is used only to locate a candidate span; it does not rewrite the
stored passage. Reject the whole build if either file has a different hash or
line count, the sides have different line counts, a line is empty, or decoding
fails.

Offsets are zero-based token indices over Python `str.split()` tokens. The
stored passage remains the exact erroneous line. The correction target remains
one exact token from the corrected line. No normalization, hamza conversion,
diacritic removal, spelling repair, or category inference is allowed.

## Deterministic alignment eligibility

The release supplies sentence pairs, not token alignments. Derive candidates
with this automatic, source-independent rule:

1. Let the erroneous whitespace tokens be the source sequence and the corrected
   whitespace tokens be the target sequence.
2. Build the full unit-cost Levenshtein dynamic program. Exact-token diagonals
   cost zero; substitution, insertion, and deletion each cost one.
3. Retain the directed acyclic graph containing every edge that belongs to at
   least one minimum-cost alignment.
4. Split every optimal diagonal edge with a virtual intermediate node. Grid
   nodes and virtual nodes are assigned layer `source_index + target_index`, so
   every complete path visits exactly one active node in every layer.
5. A one-token substitution is *forced* only when its virtual node is the sole
   active node in that layer. Therefore every minimum-cost alignment traverses
   that same erroneous-token/corrected-token edge; no arbitrary backtrace
   tie-break chooses it.
6. Reject a substitution if the exact erroneous token occurs more than once in
   the erroneous passage. This is required because the frozen correction prompt
   names the token but not its position.
7. If a released pair has multiple eligible forced substitutions, retain one by
   the lowest hexadecimal value of
   `SHA256("Tibyan-edit|3407|" + line_number + "|" + source_index + "|" +
   target_index + "|" + correction_token_sha256)`.
8. Retain at most one record per released line pair. Do not assign an ARETA or
   Musahhih linguistic category.

The highlighted error may be one of several errors remaining in the sentence.
That resembles Nahw's passage-level context but is not proof that the automatic
span is the only error or that its correction is contextually unique.

## Stable identities and connected source groups

For each retained pair, derive a text-free record ID from the release ID,
one-based line number, exact erroneous/corrected line hashes, token indices, and
exact erroneous/correction token hashes. Never use Python's process-randomized
`hash()`.

Create an undirected graph in which records are connected when they share an
exact erroneous-line hash or exact corrected-line hash. A connected component
is one `source_group_id`. All members of one group must receive the same split,
and only one seeded representative from a group may enter a training or
development selection. This prevents exact repeated source material from being
weighted twice or crossing the project split.

## Leakage and overlap exclusions

Before assigning a split, compare both full-line hashes for every member of a
source group with:

- source and correction hashes from every registered QALB train, development,
  and test record; and
- exact hashes of the registered Nahw-Passage `passage`, `error`, `correction`,
  and `explanation` strings.

Exclude the entire connected group if any full side matches any QALB or Nahw
hash. Excluding QALB train/development overlap as well as test overlap preserves
the intended natural-versus-released-synthetic distinction. This is an exact
UTF-8 check only; it does not rule out paraphrase, shared upstream sources, or
pretraining contamination.

The overlap program may load authorized private QALB data and the frozen Nahw
file only to compute/compare hashes. It must not print text or inspect model
outcomes. QALB test and Nahw-Passage remain evaluation-only and may never supply
training text, demonstrations, selection labels, or generation seeds.

## Musahhih project split and selections

Tibyan has no official train/development/test split. Call this a *Musahhih
project split* everywhere.

1. Compute
   `bucket = int(SHA256("Tibyan-project-split|3407|" + source_group_id)[:16],
   16) % 100`.
2. Assign buckets 0 through 79 to project training and 80 through 99 to project
   development.
3. Within every group, keep the record with the lowest
   `SHA256("Tibyan-group-record|3407|" + record_id)` as its representative.
4. Order eligible training representatives by
   `SHA256("F2-P1|3407|" + record_id)` and take the first 2,000.
5. `F2-P1` uses those 2,000 records. The F3 synthetic half uses the first 1,000
   records from that same frozen order; it is a nested subset, not a resample.
6. The F3 natural half uses the first 1,000 records in the already frozen
   F1-P1 selection order. Do not rescore, replace, or top up either half.

The canonical rebuild reproduced F1-P1's registered 2,000-record selection hash
`03588f135e82575f8de9030b948d6b59cd14e3ca9c218207b0f33885d1f8e2d1`.
The ordered first-1,000 record-ID digest for the F3 natural half is
`7a21b02232163752188d7a9cd0f8e9c11f4e3bbbd26d3d3cd6f70df0d7ba7fd2`.

The protocol is invalid if fewer than 2,000 eligible project-training group
representatives survive. Overlength records are not silently replaced; the
implementation gate must check all 2,000 with the exact model processor before
training and require a protocol amendment if any exceed 1,024 formatted tokens.

The project-development selection is a data-quality diagnostic only. To keep
checkpoint selection comparable with the completed F1-P1 run, F2-P1 and F3-P1
use the same frozen eligible QALB-2014 L1 development view, lowest mean
assistant-token cross-entropy between epoch 1 and epoch 2, the same `1e-6` tie
tolerance, and the same earliest-checkpoint tie break. Nahw-Passage, QALB test,
Tibyan project development generation, manual preferences, and safety results
must not choose a checkpoint.

## Matched training contract

Reuse F1-P1's exact base model and task interface:

- `unsloth/gemma-3-4b-it-unsloth-bnb-4bit` at revision
  `316726ca0bd24aa323bfaf86e8a379ee1176d1fe`;
- 4-bit checkpoint-supplied quantization, fresh unmerged LoRA adapters;
- the frozen Arabic highlighted-token correction prompt and assistant-only loss;
- maximum formatted length 1,024; packing disabled;
- two epochs, per-device batch 1, gradient accumulation 16, learning rate
  `2e-4`, linear scheduler, warmup ratio `0.03`, `adamw_8bit`, weight decay
  `0.01`, clipping `1.0`;
- LoRA rank/alpha/dropout `16/32/0.0`, bias `none`, and the same seven projection
  targets; and
- seed 3407 for the core matched comparison.

F1-P1 has only one completed seed. Do not run additional seeds for F2/F3 alone
and present them as a symmetric comparison. A future replication must register
and run the same additional seeds for every trainable arm.

The arms match total records, epochs, optimizer steps, effective batch, and
settings. Their actual sequence lengths and tokens seen will differ and must be
reported as a limitation and possible source confound. Do not claim token-budget
matching. Use the already validated free private Kaggle P100 runtime unless a
separate pre-run compatibility amendment is reviewed before any new result.

## Evaluation and execution gates

Training-workflow implementation, GPU smoke, training, selected-adapter
evaluation, and result publication require separate issues and exact-commit GO
decisions. The later evaluation protocol must be frozen before either adapter
is evaluated and must reuse F1's prompt, conservative parser, deterministic
decoding, raw-response retention, and aggregate reporting rules.

Each execution approval reference must be a permanent comment URL on the
dedicated stage-specific issue in the Musahhih GitHub repository. The workflow
validates the repository, issue-comment URL shape, exact approved commit, arm,
stage, and confirmation string. An earlier issue's consumed authorization must
not be reused for a later arm or stage.

Each F2/F3 adapter may access Nahw-Passage exactly once only after its model,
checkpoint rule, parser, artifact paths, and retry rules are frozen. A failure
after any record result exists is preserved and independently reviewed; it is
not silently repaired or rerun. The existing F1-P1 Nahw result must not tune
F2/F3. QALB test remains outside the current study unless a later protocol and
license decision explicitly authorize one single frozen evaluation.

Run the already frozen overcorrection and ArabicMMLU diagnostics for F2/F3 only
under a separately approved matched protocol. A capability interval spanning
loss and gain is not proof of non-inferiority.

## Private and public artifacts

Private ignored manifests must retain exact passages, tokens, hashes, indices,
group IDs, exclusion flags, split, selection order, prompts where applicable,
and source attribution. Private model outputs, checkpoints, adapters, and logs
stay outside Git and Notion.

Public Git artifacts may contain only source metadata, algorithms, aggregate
counts, distribution summaries, and non-reversible hashes. Do not publish
corpus lines, tokens, prompts containing corpus text, reversible encodings, or
private QALB material even when the Tibyan license itself permits redistribution.

## Freeze gate

Before status changes from draft NO-GO to frozen:

- [x] a deterministic implementation with synthetic fixtures reproduces the
      alignment, group, split, overlap, and nested-selection rules;
- [x] an ignored canonical build reproduces all aggregate counts and hashes;
- [x] all 2,000 selected records pass exact processor-length and schema checks;
- [x] the public audit contains no corpus text or credentials;
- [x] Tibyan attribution and CC BY 4.0 change disclosure are present;
- [x] the method, staged-design limitation, and leakage rules were reviewed and
      GO was posted for merged commit
      `8ca3014e6b3659e2e8c3ffc519b0255e9af6b7a6` on issue #67.

The frozen F2-P1/F3-P1 compositions are registered, but remain non-executable
until the guarded workflow itself receives the separately required approval.
The `XG` operator remains disabled regardless of this protocol's status.
