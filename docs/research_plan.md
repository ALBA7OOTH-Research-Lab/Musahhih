# Experimental Plan

## Final question to lock first

**Does LoRA/QLoRA supervised fine-tuning on natural, synthetic, or mixed Arabic GEC data improve an open model's MSA correction accuracy over the untouched model and prompt-only baselines?**

## Hypotheses

- H1: Fine-tuning will outperform zero-shot and few-shot prompting on held-out Arabic GEC data.
- H2: Natural expert-written/validated data will be more sample-efficient than synthetic data.
- H3: Mixed natural + synthetic training will outperform synthetic-only training.
- H4: Targeted GEC fine-tuning may cause overcorrection or capability loss, so both must be measured.

## Phase A — Reproducible baseline

Model:
- First choice for direct connection to Nahw: `google/gemma-3-4b-it`
- A text-only causal LM may be added later for easier LoRA experiments.

Test set:
- Nahw-Passage, held out completely.

Baselines:
- B0-P1: untouched model, zero-shot
- B1-P1: untouched model, five-shot with deterministically selected eligible QALB train examples
- B2-P1: untouched model, explicit expert-style correction prompt with no demonstrations

The exact frozen prompts, demonstration-selection rule, and pre-test validation gate
are defined in [`prompt_baseline_protocol.md`](prompt_baseline_protocol.md). Run and
artifact identifiers follow [`experiment_naming.md`](experiment_naming.md). B1 is
the few-shot family and B2 is the expert-style family; do not reverse these labels.

Primary metric:
- exact correction accuracy on the highlighted erroneous token, matching Nahw's GEC setup

Secondary diagnostics:
- normalized exact match
- empty/invalid response rate
- overlong response rate
- performance by passage and correction form

## Phase B — Training data

Do not invent linguistic labels.

Freeze the natural-versus-synthetic-versus-mixed methodology before synthetic
generation or fine-tuning. See
[`synthetic_data_protocol.md`](synthetic_data_protocol.md). The primary novelty
claim is a matched, leakage-controlled comparison of supervision sources, not
the use of synthetic data by itself.

Potential training sources:
- QALB train/dev splits, if legally obtained
- expert-validated public corpora
- Tibyan, only after confirming the released data and license
- synthetic data released by the relevant studies, if compatible

Unified training record:

```json
{
  "prompt": [
    {
      "role": "user",
      "content": "صحح الكلمة الخاطئة المحددة في النص التالي، وأعد الكلمة المصححة فقط.\nالنص: ...\nالكلمة الخاطئة: ..."
    }
  ],
  "completion": [
    {
      "role": "assistant",
      "content": "الكلمة المصححة"
    }
  ],
  "source": "dataset_name",
  "split": "train"
}
```

## Phase C — Fine-tuning experiments

The first natural-data feasibility run is specified in
[`f1_natural_pilot_protocol.md`](f1_natural_pilot_protocol.md). F1-P1 completed
its frozen training, private development selection, and single Nahw-Passage
evaluation. The selected adapter reached 145/511 exact matches (28.38%), versus
86/511 (16.83%) for untouched B0; the paired difference was 11.55 percentage
points with a pre-registered 95% paired-bootstrap interval of 7.83–15.26 points.
See [`../results/f1_p1_final_evaluation_audit.md`](../results/f1_p1_final_evaluation_audit.md).
This feasibility result is not yet the final matched-size F1/F2/F3 comparison.

Hold the following constant:
- base model
- validation/test data
- prompt format
- random seeds where practical
- decoding parameters
- evaluation script

Runs:
- F1-P1: natural-only with `N` eligible records
- F2-P1: synthetic-only with the same `N`
- F3-P1: fixed 50:50 natural + synthetic with total size `N`
- F4-P1: preregistered mixture and data-size ablations selected on development
  data only

An explanation-augmented condition is optional and separate from the core
comparison. It must not be introduced as a post-test revision of F1–F4.

## Phase D — Evaluation

Evaluate all systems on:
- Nahw-Passage GEC
- QALB official test split, if licensed
- another held-out corpus if compatible

Compare:
- B0, B1, B2
- F1, F2, F3, F4

Also measure:
- unchanged/correct input behavior to estimate overcorrection
- ArabicMMLU or another general Arabic benchmark before and after fine-tuning
- inference cost and adapter size

The F1-P1 overcorrection/capability measurement was frozen in
[`f1_capability_retention_protocol.md`](f1_capability_retention_protocol.md):
154 reconstructed QALB-2015 L2 development targets and a balanced 1,000-record
ArabicMMLU test subset, with B0 and F1-P1 executed in one matched private P100
runtime. The single approved run found higher unchanged-token accuracy for
F1-P1 (50.65% versus 27.92%) and a -0.6-point ArabicMMLU difference whose
pre-registered interval spanned -3.2 to +1.9 points. See
[`../results/f1_safety_diagnostics_audit.md`](../results/f1_safety_diagnostics_audit.md).
This diagnostic must not be repeated or used to revise F1-P1.

The proposed released-synthetic/mixed implementation is now narrowed to the
Tibyan-derived highlighted-token view in
[`tibyan_f2_f3_protocol.md`](tibyan_f2_f3_protocol.md). Its canonical private
manifest contains a nested 2,000-record synthetic selection after deterministic
alignment, grouping, project splitting, and exact hash-overlap checks. The
methodology and compositions were frozen at merged commit
`8ca3014e6b3659e2e8c3ffc519b0255e9af6b7a6`; all 2,000 selected records passed
the pinned Gemma 1,024-token formatting gate. One authorized F2-P1 two-epoch
training run completed and selected private epoch-1 `checkpoint-125` by the
frozen common-development assistant-token loss rule. No inference or final-test
access occurred; see
[`../results/f2_p1_full_training_summary.json`](../results/f2_p1_full_training_summary.json).
The single private 25-record QALB-development pipeline smoke frozen in
[`f2_p1_private_dev_smoke_protocol.md`](f2_p1_private_dev_smoke_protocol.md)
subsequently passed with 25/25 rows, zero empty outputs, and no parser warnings;
see
[`../results/f2_p1_dev_smoke_audit.md`](../results/f2_p1_dev_smoke_audit.md).
Its private development metric was not published and it did not change the
selected checkpoint, prompt, parser, or research design.
One separately authorized F3-P1 longest-record P100 smoke subsequently
validated the frozen 1,000-natural/1,000-synthetic mixture and completed one
optimizer step with 9,392,357,376 bytes of measured headroom. This is an
engineering result, not a model-quality metric; F3 full training remains
unauthorized. See
[`../results/f3_p1_gpu_smoke_audit.md`](../results/f3_p1_gpu_smoke_audit.md).
Trainer automatically wrote a private temporary checkpoint after the smoke
step; it was not selected or evaluated and is recorded as an artifact-hygiene
caveat for the next GO/NO-GO review.
The existing F1 test results predate this companion protocol, so the paper must
disclose the staged design and cannot call all arms simultaneously preregistered.

## Phase E — Paper contribution

A credible paper should contribute:
1. A controlled extension of Nahw from GU fine-tuning to actual GEC fine-tuning.
2. A natural-versus-synthetic-versus-mixed comparison.
3. Reproducible open adapters and evaluation code.
4. Error/capability-retention analysis.
5. Clear limitations: no claim of expert-level Arabic and no manual linguistic annotation by non-linguists.

## Go/no-go rule after the pilot

Continue to the full study only if:
- baseline evaluation runs reproducibly
- at least one training corpus is legally available
- the fine-tuned pilot improves held-out accuracy without obvious leakage
