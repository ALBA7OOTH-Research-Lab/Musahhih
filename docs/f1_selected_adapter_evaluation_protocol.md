# F1-P1 selected-adapter evaluation protocol

Status: proposed freeze for independent review under GitHub issue #59. No
Nahw-Passage inference is authorized by this document alone.

## Purpose and confirmatory question

This protocol defines the single confirmatory evaluation of the selected F1-P1
natural-data adapter against the accepted untouched B0 baseline. The question is
whether supervised fine-tuning on QALB natural training data changes exact-word
correction performance on the 511 test-only Nahw-Passage records.

Checkpoint selection, prompt design, parsing, decoding, and statistical methods
are frozen before adapter predictions are generated. Nahw-Passage must not be
used for training, checkpoint selection, pilot inference, prompt tuning, parser
tuning, or decisions about retrying a completed run.

## Frozen system

| Item | Frozen value |
|---|---|
| Protocol | `F1-P1` |
| Run ID | `F1-P1__gemma3-4b-it__nahw-passage__s3407__r01` |
| Selected adapter | private `checkpoint-250` |
| Selection rule | lowest development assistant-token loss; ties within `1e-6` choose epoch 1 |
| Base model | `unsloth/gemma-3-4b-it-unsloth-bnb-4bit` |
| Base revision | `316726ca0bd24aa323bfaf86e8a379ee1176d1fe` |
| Adapter config SHA-256 | `db19ef8bf4852698103dde20cd50b4429ca102ac96980f7939ecc4cff2049c4d` |
| Checkpoint selection SHA-256 | `898c19d5dcead1f6c8f0ed27b6e8c5c6b9ebaec2f1b2a9909e58d8c9758ee123` |
| Quantization | Unsloth 4-bit base loading; unmerged LoRA attached for inference only |
| Sequence limit | 2048 tokens |
| Seed | 3407 |

The evaluator loads the immutable base revision first, then attaches the private
adapter with PEFT in inference mode. It verifies the adapter directory name,
both hashes, base-model ID, LoRA rank/alpha/dropout, target modules, and selected
checkpoint before model loading. It does not merge, train, or modify weights.

## Frozen evaluation data and inference

- Official dataset: Nahw-Passage, split `test`, exactly 511 records.
- Prepared JSONL SHA-256:
  `acb3cfd204b35d5415532fbd32a4a5231b553fae329ab8f48e8454609e10279b`.
- Each record must have the required fields, a unique ID, the official source
  and split markers, and a stored prompt exactly reconstructed by
  `scripts.prepare_nahw_eval.PROMPT`.
- The exact stored B0 prompt is reused. There are no demonstrations and no
  adapter-specific instructions.
- Greedy decoding: `do_sample=False`, no temperature argument,
  `max_new_tokens=32`.
- The existing conservative `parse_model_response` function is reused without
  any Arabic normalization and without access to the gold value.
- Raw response, parsed correction, warnings, gold correction, and exact-match
  result are retained for every record in the private ignored output artifact.

There is no 25-record test pilot. All 511 records form one final run after the
model, parser, and serialization paths have already been checked on synthetic
fixtures and private development data.

## Frozen outcomes and paired analysis

The primary outcome is exact-word accuracy, preserving the gold and parsed
strings exactly. Report the F1-P1 accuracy, accepted B0 accuracy, and paired
difference `F1-P1 minus B0`.

The accepted B0 record-level predictions are also immutable: SHA-256
`6997b6fe5959f5502511ebdd1885d05a89ebaefeb27eefb73520842598f36ebc`.
The evaluator refuses any other comparison artifact.

For each shared record define:

- `baseline_wrong_adapter_right` (`n01`): B0 is wrong and F1-P1 is correct;
- `baseline_right_adapter_wrong` (`n10`): B0 is correct and F1-P1 is wrong.

The confirmatory significance test is the two-sided exact McNemar/binomial test:
`min(1, 2 * P[X <= min(n01, n10)])` for
`X ~ Binomial(n01 + n10, 0.5)`. If there are no discordant pairs, `p=1`.

The uncertainty interval is a deterministic paired bootstrap of the accuracy
difference: 10,000 samples, seed 3407, sampling the 511 paired records with
replacement. Report the percentile 95% interval using linear interpolation at
the 2.5th and 97.5th percentiles. No subgroup analysis, alternative test, or
metric becomes confirmatory after results are seen.

## Execution authorization

Before `--execute` can start, all of the following are required:

1. This protocol and evaluator are merged.
2. An independent reviewer posts GO or NO-GO and names the exact 40-character
   merged commit reviewed.
3. A separate GitHub execution issue records the reviewer, approval reference,
   approved commit, private adapter location, runtime, and intended run ID.
4. The executor supplies the exact confirmation string
   `RUN_F1_P1_NAHW_FINAL_511`, approved commit, and approval reference.
5. The evaluator verifies that the approved commit is an ancestor of its current
   checkout and completes every data and adapter preflight gate.

Passing software gates does not substitute for an independent review. A dry
preflight or synthetic test is not a final evaluation.

## Failure and retry rules

- Preserve every started run directory and mark failures `invalid`; never
  overwrite or delete partial predictions.
- A failure before the first model response (for example dependency, download,
  or model-load failure) may be retried only after documenting the cause and fix
  on the execution issue. Use the next replicate ID and retain the invalid run.
- A failure after any model response, any checksum/configuration mismatch, or
  any accidental test-output inspection stops the experiment. Do not retry
  until an independent protocol review authorizes a named replacement run.
- A completed 511-record run is never repeated because of its score, warnings,
  suspicious responses, or qualitative appearance.
- Technical retries must keep the same checkpoint, prompt, parser, decoding,
  data order, metrics, and statistics. A changed scientific setting is a new
  protocol, not a retry.

## Artifacts and reporting

Private ignored artifacts live under the canonical run directory:

```text
outputs/F1-P1__gemma3-4b-it__nahw-passage__s3407__r01/
  predictions.jsonl
  summary.json
  run.log
```

The summary records the hashes, approval provenance, Git commit, model and
runtime settings, package versions, counts, exact match, paired statistics,
warnings, and prediction checksum. Only a reviewed corpus-text-free summary may
later be committed under `results/`. QALB text, adapter weights, raw responses,
and record-level Nahw data remain private or ignored.
