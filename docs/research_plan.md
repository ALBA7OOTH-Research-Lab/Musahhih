# Research plan

## Research question

How does natural, synthetic, or mixed supervision affect highlighted-token
Modern Standard Arabic grammatical error correction when the base model,
training-set size, training interface, decoding, and final evaluation are held
fixed?

## Primary comparison

The pre-specified primary comparison is **F3 minus F2**:

- **F2-P1:** 2,000 Tibyan-derived synthetic training records.
- **F3-P1:** 1,000 QALB-derived natural records plus 1,000 Tibyan-derived
  synthetic records.

Both use the same Gemma 3 4B instruction-tuned revision, QLoRA configuration,
two-epoch training recipe, natural QALB development view, greedy decoding, and
511-record Nahw-Passage final test. The final test is never used for training,
prompt design, checkpoint selection, or development.

## Systems

| ID | System | Role |
| --- | --- | --- |
| B0 | untouched zero-shot model | historical baseline |
| B1 | untouched model with five demonstrations | staged prompt baseline |
| B2 | untouched model with an expert-style instruction | staged prompt baseline |
| F1 | QLoRA on 2,000 natural records | staged natural-only comparison |
| F2 | QLoRA on 2,000 synthetic records | primary synthetic-only arm |
| F3 | QLoRA on a fixed 50:50 mixture | primary mixed arm |

B0, B1/B2, F1, and the F2/F3 primary experiment were completed at different
stages. Only F2 and F3 form a simultaneous primary comparison; the other
contrasts are explicitly secondary.

## Training controls

- Model: Gemma 3 4B instruction-tuned, pinned to one immutable revision.
- Adaptation: 4-bit QLoRA with rank 16, alpha 32, zero dropout, and no bias.
- Target modules: query, key, value, output, gate, up, and down projections.
- Maximum formatted length: 1,024 tokens.
- Training: two epochs, batch size 1, gradient accumulation 16, AdamW 8-bit,
  learning rate `2e-4`, linear schedule, 3% warmup, and weight decay 0.01.
- Primary seed: 3407.
- Checkpoint selection: minimum assistant-token cross-entropy on the same
  frozen 975-record natural QALB development view; ties within `1e-6` favor
  epoch 1.

Equal record counts do not imply equal token budgets. The measured per-epoch
formatted-token totals are 312,644 for F1, 522,756 for F2, and 416,746 for F3.

## Final evaluation

All displayed systems use the same ordered 511 highlighted-token
Nahw-Passage records. Each prediction is conservatively parsed before scoring.
The principal metric is **exact-match accuracy**: the proportion of parsed
predicted tokens that exactly equal the single supplied reference. No Arabic
normalization is applied beyond the frozen parser's documented output-format
and whitespace handling.

For F3 minus F2, report:

- the paired difference in exact-match accuracy;
- a deterministic 10,000-sample paired-bootstrap percentile interval; and
- the exact two-sided McNemar test from aligned record outcomes.

The interval is conditional on the primary training seed and does not estimate
training randomness.

## Robustness analyses

The following analyses were added after the primary result and remain labeled
post-hoc:

1. Five independently trained F2/F3 replicas using seeds 3407–3411 on a
   uniform A100 training path and uniform RTX 3090 evaluation path.
2. Fixed epoch-1 and fixed epoch-2 comparisons across the same five replicas,
   alongside the original development-selected policy.
3. Symmetric first-token extraction for outputs already flagged as suspicious
   multi-token responses.

These checks assess training-seed sensitivity, checkpoint-policy sensitivity,
and output-format sensitivity without replacing the original primary result.

## Auxiliary behavioral diagnostics

Two frozen inputs probe behavior outside the final correction score:

- 154 QALB-2015 L2 development cases containing a designated already-correct
  token, used as a narrow overcorrection diagnostic; and
- a balanced 1,000-question ArabicMMLU subset, used as a selected capability
  diagnostic.

The diagnostics do not establish broad safety, non-inferiority, or expert
linguistic quality.

## Research boundaries

- QALB test is outside this study.
- No qualified linguist reviewed private predictions; no error-type or
  expert-quality claim is allowed.
- No new synthetic operator is used; Tibyan is the released synthetic source.
- Restricted text, predictions, responses, adapters, checkpoints, and logs
  remain private.
- Completed evaluations must not be rerun or used for tuning.

The final claim status is recorded in
[`research_completion_matrix.md`](research_completion_matrix.md), and the
public/private release boundary is recorded in
[`artifact_release_audit.md`](artifact_release_audit.md).
