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
engineering result, not a model-quality metric. See
[`../results/f3_p1_gpu_smoke_audit.md`](../results/f3_p1_gpu_smoke_audit.md).
Trainer automatically wrote a private temporary checkpoint after the smoke
step; it was not selected or evaluated and is recorded as an artifact-hygiene
caveat. A later, separately authorized F3-P1 two-epoch run completed all 250
optimizer steps and selected private epoch-2 `checkpoint-250` by the frozen
common-development assistant-token loss rule. No inference or final-test
access occurred; see
[`../results/f3_p1_full_training_audit.md`](../results/f3_p1_full_training_audit.md).
Issue #93's single authorized private selected-adapter technical smoke
completed the exact same 25 deterministic QALB development records used for
F2-P1, with zero empty outputs and zero parser warnings. The frozen contract is
documented in
[`f3_p1_private_dev_smoke_protocol.md`](f3_p1_private_dev_smoke_protocol.md).
See the corpus-text-free
[`../results/f3_p1_dev_smoke_audit.md`](../results/f3_p1_dev_smoke_audit.md).
The private development metric remains unpublished, the checkpoint did not
change, and the single-use authorization is consumed.
Issue #96's single authorized matched F2/F3 Nahw-Passage kernel reached the
Kaggle hard runtime cutoff and ended `CANCEL_ACKNOWLEDGED`; no output was
downloaded and no metric was reported. Issue #98's timeout-safe repair merged at
`cf25f6691a18515407c63e7bab7b6b4af405d731`: it provides a metric-free
private handoff at 9.5 hours plus hash-verified continuation that never
regenerates completed records. The primary new contrast remains F3-P1 minus
F2-P1; staged comparisons to accepted B0 and F1-P1 remain secondary. See
[`f2_f3_selected_adapter_evaluation_protocol.md`](f2_f3_selected_adapter_evaluation_protocol.md).
This preparation does not authorize test access or inference, and QALB test
remains outside the current companion study.

The first timeout-safe replacement segment completed F2-P1 511/511 and
preserved F3-P1 168/511 before returning the preregistered metric-free
`incomplete_time_budget` handoff. The private prefix passed exact hash, schema,
and ordered-alignment audit. No score or partial comparison was reported, and
continuation required a fresh exact-commit owner GO. The separately authorized
continuation reused those exact artifacts, completed F3-P1 511/511, and closed
the frozen matched evaluation. F2-P1 produced 105/511 exact matches and F3-P1
produced 162/511. The primary F3-P1-minus-F2-P1 difference was
`0.11154598825831702`, with a preregistered paired-bootstrap 95% interval of
`[0.07045009784735812, 0.15264187866927592]`. See
[`../results/f2_f3_final_evaluation_audit.md`](../results/f2_f3_final_evaluation_audit.md).
The continuation authorization is consumed; the final evaluation must not be
repeated or used for tuning.
The existing F1 test results predate this companion protocol, so the paper must
disclose the staged design and cannot call all arms simultaneously preregistered.

Issue #155 separately prepares a post-hoc, prospectively frozen five-seed
F2-P1/F3-P1 robustness cohort on matched A100 hardware. Seeds 3407–3411 are
paired within five Jobs, with alternating arm order, forced FP16, disabled
TF32, both epoch checkpoints retained, and the original common-development
selection rule unchanged. See
[`f2_f3_nautilus_multiseed_protocol.md`](f2_f3_nautilus_multiseed_protocol.md).
Preparation authorizes no cluster object, private-input access, model loading,
training, inference, Nahw-Passage access, metric, retry, or continuation.
The first separately authorized no-input/no-model A100 preflight failed before
its init container started because the pinned checkout-image checksum had an
invalid length. No checkout or CUDA operation occurred, the failed allocation
was released without retry, and that authorization is consumed. Issue #157
prepares a repository-only full-digest repair and manifest-generation guard;
even after merge, a replacement preflight requires a fresh exact-commit GO.
That replacement passed checkout and runtime setup but failed before CUDA
because the main container lacked the `git` executable used by a redundant
commit check. Issue #159 prepares strict detached-HEAD metadata verification
without a main-runtime Git dependency. The replacement authorization is
consumed, and any further preflight still requires a fresh exact-commit GO.
A fresh second replacement then passed the exact-A100 synchronized CUDA
operation but failed the complete import gate because Triton required a C
compiler absent from the minimal PyTorch runtime image. Issue #161 prepares a
matching official digest-pinned `devel` image while retaining PyTorch 2.6.0,
CUDA 12.4, cuDNN 9, and every frozen experiment setting. That authorization is
consumed; another preflight requires a fresh exact-commit GO.
The compiler-capable replacement subsequently passed the complete no-input
A100 gate. It validated exact A100 identity, a synchronized CUDA operation,
the compiler, frozen packages, imports, and precision controls. Issue #163
prepares the remaining Unsloth-first import-order correction and separates
write-once CPU-only private PVC staging from the five GPU Jobs. Staging, a
final exact-commit preflight, and training each require independent owner GOs.
Issue #163's first authorized staging attempt then remained unbound on the
`cephfs` provisioner; its Pod never scheduled and no private file was uploaded.
Issue #165 prepares a narrow switch to the namespace's proven `rook-cephfs`
RWX class. The failed staging authorization is consumed.
The replacement staging and final import-order preflight then passed at exact
commit `b01e93d35bf134fc7b547b7dbc17bec185794faf`. The separately authorized
five-seed wave nevertheless failed before its first optimizer step because
Gemma loaded as BF16 on A100 while the frozen trainer requested FP16. Issue
#167 prepares the narrow scientific-contract repair: force FP16 at model load,
prove exact model/collator/trainer construction in one no-private A100 smoke,
persist write-once logs and failure records, and retain 25-step recovery
checkpoints for fresh-GO continuation. It changes no dataset, model revision,
optimizer, schedule, batch, loss, evaluation cadence, checkpoint-selection
rule, inference, or metric. Merge authorizes no GPU execution or retry.
The separately authorized smoke subsequently completed the exact A100
model/LoRA/collator/`SFTTrainer` construction path with zero optimizer steps.
The explicit float16 model-configuration guard passed and the prior BF16/FP16
construction mismatch did not recur. Unsloth used float32 master weights for
Gemma 3 while retaining the frozen FP16 trainer configuration. No PVC, corpus,
private record, training, inference, prediction, or metric was used. See
[`../results/f2_f3_nautilus_fp16_trainer_smoke_audit.md`](../results/f2_f3_nautilus_fp16_trainer_smoke_audit.md).
The authorization is consumed; replacement training still requires a fresh
exact-commit owner GO. That separately authorized replacement wave later
completed all five seeds, with both frozen two-epoch arms and the
common-development checkpoint-selection workflow returning normally in every
Job. See
[`../results/f2_f3_nautilus_multiseed_training_audit.md`](../results/f2_f3_nautilus_multiseed_training_audit.md).
No test set, inference, prediction, or final metric was used. The training
authorization is consumed; evaluation and aggregation require a separately
reviewed protocol and fresh GO.
Issue #171 prepares that protocol with separate frozen-test staging,
five-seed selected-adapter evaluation, and corpus-free aggregation gates. Each
evaluation uses the exact selected training artifacts, deterministic decoding,
per-row persistence, a metric-free safe stop, and fresh-GO-only continuation.
The aggregate reports every seed, per-arm mean/sample SD, and the mean,
sample SD, and range of paired F3-minus-F2 differences. See
[`f2_f3_nautilus_multiseed_evaluation_protocol.md`](f2_f3_nautilus_multiseed_evaluation_protocol.md).
Preparation authorizes no execution or private access.
The authorized staging later passed, but the first five evaluation Jobs
preserved only 3,739/5,110 record-arm outputs before three OOM failures and two
owner suspensions after prolonged no-progress GPU idling. No metric was
computed. Issue #173 therefore prepared fresh-process, externally supervised,
batch-16 continuation behind a separate non-test equivalence/utilization
canary. Its single authorized canary completed the synthetic equivalence and
soak without OOM but failed the 40% mean-A100-utilization gate. Issue #175's
single authorized batch-64 follow-up then failed closed before its soak because
batch-64 and single-record synthetic outputs differed. It accessed no test
input or metric and was not retried. Issue #177 now prepares five isolated,
concurrent batch-16 workers on one 80 GB A100, retaining the already established
single/batch-16 equivalence while satisfying the official NRP utilization rule
through workload packing rather than a decoding change. See
[`f2_f3_nautilus_evaluation_concurrency_protocol.md`](f2_f3_nautilus_evaluation_concurrency_protocol.md).
The source prefixes remain immutable. The synthetic canary, private
continuation, and aggregation each require separate fresh exact-commit GOs.
The single issue-#177 canary later reached the final utilization check with all
five batch-16 workers but averaged only 11.762% A100 utilization; memory stayed
within both guards and no test input or metric was used. Issue #179 therefore
prepares the same canary under NVIDIA MPS, which allows independent CUDA
processes to overlap work through one server context. See
[`f2_f3_nautilus_evaluation_mps_protocol.md`](f2_f3_nautilus_evaluation_mps_protocol.md).
No MPS canary or real continuation is authorized by preparation or merge.
The separately authorized MPS canary later attached all five clients but every
worker failed the same repeated batch-16 output-equivalence check. Its observed
mean utilization was 27.748%, still below the 40% gate, while both memory
guards remained safe. A CPU-only read-only audit confirmed byte-identical
worker logs and clean MPS shutdown. MPS is therefore rejected for the frozen
evaluation. With no complete multi-seed metric, the extension is frozen for
this submission and no robustness claim is allowed.
The owner subsequently required completion before submission. Issue #183
therefore prepares a clean post-hoc infrastructure recovery on five uniform
RTX 3090 GPUs. Each seed restarts both arms from record zero; no A100 prefix is
reused. An inline synthetic equivalence gate must pass before test access in
each Job. This hardware recovery is not preregistered and must be disclosed as
post-hoc. No result is reportable until all five Jobs and the separately gated
aggregate audit complete.
The separately authorized issue-#183 recovery later completed all five seeds,
both arms per seed, with exit code zero and zero restarts. Issue #185 now
prepares the final CPU-only audit of all ten private prediction artifacts. It
recomputes hashes, counts, record alignment, exact-match values, paired
statistics, and the frozen across-seed summaries before any number is released.
The separately authorized audit completed and validated all ten private files,
their hashes, 511-row counts, record alignment, exact-match recounts, and every
paired statistic. F2-P1 averaged 21.68% (sample SD 0.71 percentage points),
F3-P1 averaged 31.98% (sample SD 1.15), and paired F3-minus-F2 averaged +10.29
points (sample SD 1.45; range +8.61 to +12.52). F3 exceeded F2 in all five
seeds. This is post-hoc robustness evidence; the original seed-3407 result
remains primary.

One separately authorized local CPU-only post-hoc audit then tested the
reviewer-suggested first-token sensitivity on only outputs already flagged
`multiple_words`. It rescued 0/20 F2-P1 outputs and 0/2 F3-P1 outputs, leaving
both scores and the 11.15-point primary difference unchanged. See
[`../results/f2_f3_first_token_sensitivity_audit.md`](../results/f2_f3_first_token_sensitivity_audit.md).
The audit did not change the parser, rerun inference, or publish record-level
content. Its authorization is consumed; do not rerun it.

A separately gated post-hoc fixed-checkpoint sensitivity then reused the five
selected-checkpoint results and evaluated only the retained unselected epoch
for each seed-arm. The CPU-only issue-#196 aggregate validated all 20 unique
prediction files and checkpoint identities. F3-P1 exceeded F2-P1 in every seed
under both matched policies: the mean gap was +6.11 points at fixed epoch 1
and +6.58 at fixed epoch 2. The frozen natural-development rule selected F2
epoch 1 and F3 epoch 2 for all five replicas, producing the larger +10.29-point
dev-selected gap. This shows that selection amplifies the estimated magnitude
but does not create the direction. The analysis remains post-hoc and the
original seed-3407 P100 comparison remains primary. See
[`../results/f2_f3_fixed_checkpoint_sensitivity_audit.md`](../results/f2_f3_fixed_checkpoint_sensitivity_audit.md).

One separately authorized B1-P1 five-shot final run subsequently completed all
511 frozen Nahw-Passage records at exact executable commit
`0c34d1846cebc81ea847d8c2c352c353f8988d46`. It produced 89/511 exact
matches (17.42%). The paired B0-minus-B1 interval included zero. F1-P1 and
F3-P1 exceeded B1-P1 in staged comparisons, while the F2-P1-minus-B1-P1
interval included zero. See
[`../results/b1_p1_final_evaluation_audit.md`](../results/b1_p1_final_evaluation_audit.md).
The authorization is consumed; do not repeat or tune from this result.

One separately authorized repaired B2-P1 expert-style run then completed all
511 records and achieved 108/511 exact matches (21.14%). B2-P1 exceeded B0-P1
and B1-P1; F1-P1 and F3-P1 exceeded B2-P1; F2-P1 was not established as
different from B2-P1. See
[`../results/b2_p1_final_evaluation_audit.md`](../results/b2_p1_final_evaluation_audit.md).
The authorization is consumed; do not repeat or tune from this result.

## Phase E — Paper contribution

A credible paper should contribute:
1. A controlled extension of Nahw from GU fine-tuning to actual GEC fine-tuning.
2. A natural-versus-synthetic-versus-mixed comparison.
3. Reproducible evaluation code and adapter identities; adapter weights only
   if a separate release review clears them.
4. Error/capability-retention analysis.
5. Clear limitations: no claim of expert-level Arabic and no manual linguistic annotation by non-linguists.

The current claim-by-claim status is recorded in
[`research_completion_matrix.md`](research_completion_matrix.md), the draft
manuscript structure in [`paper_outline.md`](paper_outline.md), and the current
public-release boundary in [`artifact_release_audit.md`](artifact_release_audit.md).
These planning documents do not authorize any optional remaining experiment.

## Go/no-go rule after the pilot

Continue to the full study only if:
- baseline evaluation runs reproducibly
- at least one training corpus is legally available
- the fine-tuned pilot improves held-out accuracy without obvious leakage
