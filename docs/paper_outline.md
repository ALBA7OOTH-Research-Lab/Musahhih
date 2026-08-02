# Musahhih paper outline

Status: publication-synthesis draft. This is not a submission manuscript.

## Working title

**Natural, Synthetic, or Mixed Supervision for Open-Weight Arabic Grammatical
Error Correction**

Avoid titles claiming state of the art, expert validation, comprehensive Arabic
coverage, or universal superiority.

## One-sentence result

In a frozen equal-size comparison using Gemma-3 4B and 511 held-out
Nahw-Passage corrections, fixed 50:50 natural/synthetic supervision
substantially outperformed synthetic-only supervision, while it did not
establish an advantage over natural-only supervision in the staged comparison.

## Research questions

1. Does natural-data fine-tuning improve highlighted-token MSA correction over
   the accepted untouched model run?
2. With training size held constant, how does synthetic-only supervision
   compare with natural-only supervision?
3. Does a fixed equal natural/synthetic mixture outperform synthetic-only
   supervision?
4. Does the natural-data adapter affect overcorrection or selected general
   Arabic multiple-choice capability?

The current evidence includes both frozen B1-P1 five-shot and B2-P1
expert-style prompt baselines.

## Contributions

1. A leakage-controlled GEC fine-tuning extension of the Nahw benchmark using
   one open-weight instruction model.
2. A matched-size comparison of natural-only, synthetic-only, and fixed mixed
   supervision.
3. Frozen prompts, decoding, checkpoint rules, seeds, artifacts, and paired
   statistics with hash-verified private predictions.
4. A completed F1-P1 overcorrection and ArabicMMLU retention diagnostic.
5. A transparent audit trail covering private-data handling, time-limited GPU
   continuation, failed runs, and non-repetition of completed test results.

Do not claim publicly released adapters until the release audit is resolved.

## Suggested abstract structure

1. Motivation: practical MSA GEC remains weaker and less studied than Arabic
   grammar understanding.
2. Gap: prior work does not isolate natural, synthetic, and mixed supervision
   under the same open model, size, prompt, and held-out correction task.
3. Method: QLoRA adapters on Gemma-3 4B; equal-size F1/F2/F3 training views;
   frozen 511-record Nahw-Passage exact correction evaluation.
4. Primary result: F3-P1 31.70% versus F2-P1 20.55%, a paired difference of
   11.15 points with a 7.05–15.26-point interval.
5. Robustness: in a post-hoc five-seed cohort, F3-P1 exceeded F2-P1 in every
   seed; the mean paired advantage was 10.29 points (sample SD 1.45).
6. Format sensitivity: a post-hoc first-token rule rescued 0/20 flagged F2-P1
   outputs and 0/2 flagged F3-P1 outputs, leaving the primary gap unchanged.
7. Secondary result: F1-P1 28.38%; F3-P1 was not established as different from
   F1-P1.
8. Auxiliary diagnostics: F1-P1 reduced the selected overcorrection diagnostic and showed no
   established ArabicMMLU change.
9. Limitation: one model, one strict benchmark, staged F1/B0 comparisons, no
   expert linguistic error analysis, and private restricted artifacts.

## Main results table

| System | Supervision | Correct / 511 | Accuracy |
| --- | --- | ---: | ---: |
| B0-P1 | None, zero-shot | 86 | 16.83% |
| B1-P1 | None, frozen five-shot | 89 | 17.42% |
| B2-P1 | None, frozen expert-style | 108 | 21.14% |
| F1-P1 | Natural-only | 145 | 28.38% |
| F2-P1 | Synthetic-only | 105 | 20.55% |
| F3-P1 | 50:50 natural/synthetic | 162 | 31.70% |

The earlier 25-record QALB development values remain technical gate
diagnostics and must not replace these Nahw-Passage final results.

## Post-hoc five-seed robustness table

| Seed | F2-P1 | F3-P1 | F3 minus F2 |
| ---: | ---: | ---: | ---: |
| 3407 | 20.55% | 33.07% | +12.52 points |
| 3408 | 21.92% | 31.51% | +9.59 points |
| 3409 | 21.72% | 30.33% | +8.61 points |
| 3410 | 22.50% | 33.07% | +10.57 points |
| 3411 | 21.72% | 31.90% | +10.18 points |
| Mean (sample SD) | 21.68% (0.71) | 31.98% (1.15) | +10.29 (1.45) |

Training used the completed A100 five-seed wave; recovery inference used one
RTX 3090 per seed. Treat this as post-hoc robustness evidence. It supports the
stability of the mixed-over-synthetic direction but does not replace the
preregistered seed-3407 primary comparison.

## Paired-comparison table

| Comparison | Difference | 95% interval | Exact McNemar p | Status |
| --- | ---: | ---: | ---: | --- |
| F3-P1 − F2-P1 | +11.15 points | +7.05 to +15.26 | `2.15e-07` | Primary preregistered comparison |
| F1-P1 − B0 | +11.55 points | +7.83 to +15.26 | `4.07e-09` | Earlier staged comparison |
| F2-P1 − B0 | +3.72 points | −0.78 to +8.22 | `0.121` | Difference not established |
| F3-P1 − B0 | +14.87 points | +10.76 to +18.98 | `3.19e-12` | Staged secondary comparison |
| F2-P1 − F1-P1 | −7.83 points | −12.52 to −3.13 | `0.00137` | Staged secondary comparison |
| F3-P1 − F1-P1 | +3.33 points | −0.39 to +7.05 | `0.0966` | Difference not established |
| B0-P1 − B1-P1 | −0.59 points | −3.33 to +2.15 | `0.775` | Difference not established |
| F1-P1 − B1-P1 | +10.96 points | +7.24 to +14.68 | `1.59e-08` | Staged secondary comparison |
| F2-P1 − B1-P1 | +3.13 points | −1.17 to +7.44 | `0.181` | Difference not established |
| F3-P1 − B1-P1 | +14.29 points | +10.18 to +18.40 | `6.97e-11` | Staged secondary comparison |
| B2-P1 − B0-P1 | +4.31 points | +1.96 to +6.85 | `0.000941` | Staged secondary comparison |
| B2-P1 − B1-P1 | +3.72 points | +0.78 to +6.65 | `0.0183` | Staged secondary comparison |
| F1-P1 − B2-P1 | +7.24 points | +3.33 to +10.96 | `0.000296` | Staged secondary comparison |
| F2-P1 − B2-P1 | −0.59 points | −5.09 to +3.91 | `0.862` | Difference not established |
| F3-P1 − B2-P1 | +10.57 points | +6.65 to +14.48 | `2.52e-07` | Staged secondary comparison |

## Recommended section structure

### 1. Introduction

- practical MSA correction motivation;
- difference between grammar understanding and correction;
- supervision-source question;
- concise contributions without inflated novelty claims.

### 2. Related work

- Nahw GU/GED/GEC/GEX benchmark;
- QALB shared tasks;
- prompted and instruction-tuned Arabic GEC;
- synthetic Arabic GEC and Tibyan;
- automatic error analysis and its limits.

Use `docs/literature_matrix.md` as the source map. Re-verify every citation and
numeric prior-work claim against the primary paper before submission.

### 3. Data and safeguards

- QALB roles and restrictions;
- Tibyan CC BY 4.0 release and deterministic derived view;
- exact overlap and grouping controls;
- Nahw-Passage as test-only;
- private artifacts and blinded F2/F3 development metrics.

### 4. Systems and training

- immutable base revision and 4-bit QLoRA;
- equal training size;
- F1 natural-only, F2 synthetic-only, F3 fixed 50:50 mixture;
- checkpoint selection by frozen common-development loss;
- exact prompt, parser, decoding, and seed.

### 5. Evaluation and statistics

- highlighted-token exact match;
- 511 paired records;
- F3-minus-F2 primary comparison;
- staged B0/F1 comparisons;
- exact McNemar test and deterministic paired bootstrap;
- warning and invalid-output counts.

### 6. Results

- main system table;
- paired-comparison table;
- emphasize mixed versus synthetic-only;
- state explicitly that mixed versus natural-only was not established.

### 7. Safety diagnostics

- F1-P1 selected overcorrection diagnostic;
- balanced ArabicMMLU subset;
- no formal non-inferiority claim;
- F2/F3 diagnostics marked absent unless separately completed before the paper
  is frozen.

### 8. Limitations and ethics

- strict single-gold exact match;
- one model, one training size, and one principal benchmark;
- the primary comparison uses one seed, partly addressed by a separately
  executed post-hoc five-seed robustness cohort;
- the F2 multi-token anomaly is mechanically resolved: first-token extraction
  changes neither arm's score and rescues none of the flagged outputs;
- possible alternate valid corrections;
- no independent expert linguistic labeling;
- staged rather than simultaneous B0/F1/F2/F3 timing;
- cross-runtime/hardware caveats for accepted historical comparisons;
- restricted QALB and non-commercial ArabicMMLU handling;
- adapters and record-level artifacts currently private.

### 9. Reproducibility

- public code and aggregate evidence;
- exact commits, revisions, hashes, package versions, seeds, and hardware;
- private-artifact availability statement that does not promise redistribution;
- timeout-safe continuation and audit trail.

## Figures

Recommended:

1. accuracy plot for B0/F1/F2/F3 with paired-difference intervals shown
   separately;
2. data-composition diagram for equal-size F1/F2/F3 training;
3. research workflow diagram showing freeze, training, private development,
   single final evaluation, and audit.

Do not plot B1/B2 development values alongside Nahw-Passage results.

## Claims to avoid

- “F3 is better than F1”;
- “synthetic-only training improves the base model”;
- “all fine-tuning beats few-shot or expert prompting”;
- “no capability loss” as a general claim;
- “expert-validated Musahhih outputs”;
- “state of the art” without a same-task comparable benchmark;
- “open-source adapters” before release clearance; or
- “complete Arabic GEC” from a 511-record highlighted-token benchmark.

## Work required before submission

Required:

- author and affiliation decisions;
- verified bibliography and citation formatting;
- final tables/figures generated from the consolidated JSON;
- explicit software and artifact availability statement;
- authorship review of claims and limitations;
- venue formatting and paper-level language review.

Optional strengthening experiments:

- frozen B1-P1/B2-P1 final Nahw-Passage baselines;
- matched F2-P1/F3-P1 safety diagnostics;
- qualified private linguistic error analysis; and
- an independently licensed additional held-out GEC evaluation.

Each optional experiment requires a separate decision. None is authorized by
this outline.
