# AGENTS.md

## Purpose

Musahhih is a research repository for improving Modern Standard Arabic grammatical error correction with open-weight language models.

Treat this file as a map, not a full manual. Follow the linked docs for details.

## Sources of truth

- Project overview and setup: `README.md`
- Experimental design: `docs/research_plan.md`
- Dataset roles and leakage rules: `docs/dataset_audit.md`
- Prior work and research gap: `docs/literature_matrix.md`
- Research completion status: `docs/research_completion_matrix.md`
- Publication synthesis: `docs/paper_outline.md`
- Artifact release constraints: `docs/artifact_release_audit.md`
- Qualified linguistic review boundary: `docs/qualified_linguistic_review_plan.md`
- Current implementation task: `docs/tasks/001_colab_unsloth_baseline.md`

## Current milestone

`F1-P1` natural-data training, private development smoke, the single frozen
Nahw-Passage evaluation, and the matched overcorrection/ArabicMMLU diagnostics
are complete. See `results/f1_p1_final_evaluation_audit.md` and
`results/f1_safety_diagnostics_audit.md`. QALB text, benchmark questions, model
responses, and adapter artifacts remain private.

Do not tune prompts, parsing, checkpoints, training data, or experiment
decisions from the completed Nahw-Passage or safety-diagnostic results. The
Tibyan-derived F2/F3 methodology and compositions are frozen at commit
`8ca3014e6b3659e2e8c3ffc519b0255e9af6b7a6`. The fail-closed Kaggle workflow
at `f64edead0367e7659b107e5c4c309ed811d09071` passed its longest-record P100
smoke. The immutable-checkout wrapper repair is merged at
`ea4766ee205922c9fd4cb1af0357cca19bcfd59b`. After an explicitly documented
owner waiver of an additional repair-only smoke, one authorized F2-P1
two-epoch run completed and selected private `checkpoint-125` by the frozen
common-development loss rule. See `results/f2_p1_full_training_summary.json`.
Issue #82's single private F2-P1 `checkpoint-125` smoke completed all 25 frozen
QALB development records and passed its technical gate with zero empty outputs
and no parser warnings. See `results/f2_p1_dev_smoke_audit.md`. Its private
development metric and record-level responses were not published, and the
checkpoint did not change. The authorization is consumed. Issue #85's F3-P1
smoke-gate preparation is merged at
`6d64f699c04168cc15c045edc86389d5dc81f1bc`. One subsequently authorized
F3-P1 longest-record P100 smoke completed one optimizer step and passed with
9,392,357,376 bytes of measured headroom. See
`results/f3_p1_gpu_smoke_audit.md`. Trainer also wrote an incidental private
temporary `checkpoint-1`; it was not selected, evaluated, or published. The
smoke authorization is consumed. Issue #91's separately authorized F3-P1
two-epoch run subsequently completed all 250 optimizer steps and selected
private `checkpoint-250` by the frozen common-development loss rule. See
`results/f3_p1_full_training_audit.md`. No F3 inference or final-test access
occurred, and the selected adapter remains private. The full-training
authorization is consumed. Do not run further F2 inference, another F3 smoke,
F3 training or inference, final-test evaluation, safety reruns, or XG without
a fresh scope-specific GO. Issue #93's single private F3-P1 selected-adapter
smoke completed the exact same 25 deterministic QALB development records used
for F2-P1, with zero empty outputs and zero parser warnings. See
`results/f3_p1_dev_smoke_audit.md`. The private development metric and
record-level responses were not read or published, and `checkpoint-250` did
not change. The authorization is consumed. Issue #96's single authorized
matched F2/F3 Nahw-Passage kernel reached Kaggle's hard runtime cutoff after
roughly 40,000 seconds and ended `CANCEL_ACKNOWLEDGED`. No output was
downloaded, no metric was reported, and no retry occurred. Its authorization
is consumed. Issue #98's timeout-safe, resumable private handoff repair merged
at `cf25f6691a18515407c63e7bab7b6b4af405d731` with a 9.5-hour
graceful-stop threshold. The merge does not authorize test access, inference,
retry, or continuation; every future kernel requires a fresh exact-commit owner
GO. One subsequently authorized replacement segment completed F2-P1 511/511
and F3-P1 168/511 before returning the planned metric-free
`incomplete_time_budget` handoff. See
`results/f2_f3_final_evaluation_handoff_audit.md`. Private predictions remain
ignored; no score or partial comparison was reported. The authorization is
consumed. A separately authorized exact-commit continuation then reused the
byte-identical F2-P1 result and preserved F3-P1 prefix, completed F3-P1
511/511, and closed the frozen matched evaluation. See
`results/f2_f3_final_evaluation_audit.md`. F3-P1 achieved 162/511 exact
matches versus F2-P1's 105/511; the preregistered paired difference was 11.15
percentage points with a 95% paired-bootstrap interval of 7.05–15.26 points.
Private predictions and logs remain ignored. The continuation authorization is
consumed. Do not repeat the final evaluation or tune any decision from its
results. QALB test remains outside the current study.
The proposed `XG` operator remains disabled pending qualified linguistic review.
Issue #104 is preparing the corpus-text-free publication synthesis and remaining
gate plans. It authorizes no inference, test access, adapter release, linguistic
labeling, or new GPU run.
Issue #107's timeout-safe resumable B1-P1/B2-P1 final gate is implemented at
exact executable commit `16b4ca3dec6e757b41e233b22bc16cc6a57be4dd`
through PR #108. It adds a 9.5-hour safe stop, per-row persistence,
metric-free handoff, exact-prefix continuation, and strict exact-commit
activation. The implementation does not authorize model loading,
Nahw-Passage access, inference, Kaggle submission, or continuation. Every
future segment requires independent review and a fresh scope-specific owner GO.
Issue #109's single authorized B1-P1 segment on new Kaggle account
`alba7oothresearchlab` failed closed after approximately 1.07 seconds because
the wrapper assumed an external `nvidia-smi` executable that was unavailable.
Kaggle stored `enable_gpu=true`, the account had 30 GPU-hours remaining, and
CUDA availability was never measured, so do not attribute this failure to
account eligibility or a definitively absent GPU. No repository checkout,
private input access, model loading, inference, predictions, or metric occurred.
See `results/b1_p1_final_attempt_failure_audit.md`. The authorization is
consumed; do not retry or submit another version. Any future B1 attempt requires
a reviewed GPU-preflight repair and a fresh exact-commit owner GO.
Issue #112's PyTorch CUDA/P100 preflight repair is implemented at exact
executable commit `f8c7ffd74993785f118bb32e0145295b31c5048d`. It
requires CUDA, exactly one device, and a P100 before private-input access, with
no dependency on external `nvidia-smi`. The repair does not authorize another
kernel; any future B1 attempt requires independent review and a fresh
scope-specific owner GO.
Issue #114's single authorized repaired B1-P1 attempt failed closed before
repository checkout because Kaggle could not resolve `download.pytorch.org`
across all pinned-PyTorch install retries. The repaired GPU preflight, private
input, model, inference, predictions, and metrics were never reached. See
`results/b1_p1_repaired_attempt_failure_audit.md`. The authorization is
consumed; do not edit the kernel, push another version, or retry.
Issue #125's single authorized B1-P1 attempt on `thgh15` passed repository,
GPU-identity, dependency, and private-artifact hash gates, then failed closed
at approximately 114.95 seconds because all 511 frozen input rows used `id`
while `run_prompt_baseline` required `record_id`. Model loading, inference,
predictions, metrics, and training were never reached. The same log exposed an
independent blocker: PyTorch 2.10.0+cu128 warned that the P100's `sm_60`
capability was unsupported, while the preflight had performed no CUDA tensor
operation. See `results/b1_p1_8710263_r03_failure_audit.md`. The authorization
is consumed. Do not retry; a future attempt requires reviewed schema-contract
and executable-CUDA preflight repairs plus a fresh exact-commit owner GO.
Issue #127 implements both repairs at exact code commit
`cb65e2f3143179d34034b661116220a011ffdddd`. The prompt runner now
deterministically accepts the frozen prepared-Nahw `id` alias, rejects
conflicting aliases, and the exact ignored 511-row artifact passes a
corpus-text-free contract check without changing its bytes. The P100 preflight
now requires a real CUDA tensor operation and synchronization before any
private-input access. See `results/b1_b2_preflight_repair_audit.md`. No Kaggle
run or model load occurred. Actual P100 execution remains unvalidated; the
next permissible run is a separately authorized no-input/no-model preflight
smoke after merge `84566e8a7b114c942047a3c14455b83e4cc35f7b`, not B1 inference.
Issue #130's single authorized no-input/no-model P100 smoke then confirmed the
repaired guard fails closed correctly. The exact commit checkout passed, but
PyTorch could not execute on the P100 because its compiled architectures begin
at `sm_70` while the device is `sm_60`. The aggregate error occurred at
approximately 8.58 seconds. No dataset/model was attached and no private input,
model load, inference, training, prediction, or metric occurred. See
`results/b1_b2_p100_operation_smoke_audit.md`. The authorization is consumed;
do not retry. A future path requires a reviewed P100-compatible runtime
strategy or accelerator change, another no-input executable smoke, and fresh
scope-specific GOs.
Issue #132 restores the already successful F2/F3 P100 runtime pattern at exact
code commit `9bc36e31fe486350319f363f79bfca06dbb5e7af`: official PyTorch
2.6.0/torchvision 0.21.0 CUDA 12.4 wheels, the recorded compatible inference
stack, `UNSLOTH_COMPILE_DISABLE=1`, fresh-process identity/import validation,
and the executable CUDA-operation guard. See
`results/b1_b2_proven_p100_runtime_restore_audit.md`. All 235 tests and 65
subtests pass. No Kaggle or model execution occurred. After merge, only a
fresh-GO no-input/no-model restored-runtime smoke is eligible; B1/B2 inference
remains unauthorized.
Issue #135's single authorized restored-runtime smoke subsequently completed
in approximately 268 seconds. It restored the exact PyTorch 2.6.0+cu124/CUDA
12.4 stack, passed the synchronized P100 CUDA operation, and import-checked
Unsloth/bitsandbytes with compilation disabled. See
`results/b1_b2_restored_p100_smoke_audit.md`. Zero datasets/models were
attached and no private input, model load, inference, training, prediction, or
metric occurred. The authorization is consumed. B1/B2 evaluation remains
unauthorized and requires a fresh exact-commit GO with timeout-safe per-record
persistence.
Issue #137 prepares a deterministic, write-once private B1-P1 511-record
kernel package using that passing restored runtime and the existing
34,200-second safe stop, per-row `fsync`, atomic progress manifest, and
metric-free resumable handoff. See
`results/b1_p1_timeout_safe_kernel_preparation_audit.md`. Preparation does not
authorize Kaggle submission, private-input access, model loading, inference,
metrics, retry, continuation, or B2-P1. A real segment requires a fresh owner
GO naming the exact merged commit.
Issue #139's single authorized B1-P1 segment subsequently completed all 511
frozen Nahw-Passage records in 22,612 seconds. B1-P1 achieved 89/511 exact
matches (17.42%) with zero empty outputs. See
`results/b1_p1_final_evaluation_audit.md`. The paired B0-minus-B1 interval
included zero; F1-P1 and F3-P1 exceeded B1-P1 in staged comparisons, while the
F2-P1-minus-B1 interval included zero. Private predictions, prompts, raw
responses, gold values, and logs remain ignored. The authorization is
consumed; do not repeat B1-P1 or tune from its result. B2-P1 remains
unauthorized.
Issue #141 prepares a deterministic, write-once private B2-P1 511-record
kernel package using the same passing P100 runtime and timeout-safe runner. It
accesses only the frozen test input after the runtime gate and passes no
demonstration bundle. See
`results/b2_p1_timeout_safe_kernel_preparation_audit.md`. Preparation does not
authorize Kaggle submission, private-input access, model loading, inference,
metrics, retry, or continuation. A real B2-P1 segment requires a fresh owner
GO naming the exact merged commit. B1-P1 must not be repeated.
Issue #143's single authorized B2-P1 attempt passed exact checkout and the
restored P100 runtime, then failed closed at approximately 259.94 seconds
because its fixed Kaggle input-mount path did not exist. No private corpus file
was opened or hashed, and no model load, inference, training, prediction, or
metric occurred. See `results/b2_p1_2767ca6_r01_failure_audit.md`. The
authorization is consumed; do not retry or submit version 2. A future B2
attempt requires a reviewed corpus-text-free mount-discovery repair and a
fresh exact-commit owner GO.
Issue #145 replaces the failed fixed mount path with recursive discovery of
exactly one `nahw_gec_test.jsonl` followed by the frozen SHA-256 gate. The B1
bundle is neither opened nor passed. See
`results/b2_p1_mount_discovery_repair_audit.md`. No Kaggle run or private
corpus access occurred; a fresh exact-commit owner GO remains required.
Issue #147's single authorized repaired B2-P1 run completed all 511 frozen
Nahw-Passage records. B2-P1 achieved 108/511 exact matches (21.14%) with zero
empty outputs and no demonstration bundle. See
`results/b2_p1_final_evaluation_audit.md`. B2-P1 exceeded B0-P1 and B1-P1;
F1-P1 and F3-P1 exceeded B2-P1; F2-P1 was not established as different from
B2-P1. Private record-level artifacts remain ignored. The authorization is
consumed; do not rerun or tune from B2-P1.
Issue #155's authorized five-seed A100 robustness wave failed before its first
optimizer step. Retained logs for seeds 3408, 3409, and 3411 showed that Gemma
loaded as BF16 on A100 while the frozen trainer requested FP16; Unsloth rejected
the mismatch during `SFTTrainer` construction. No checkpoint, inference,
prediction, or metric was produced, and no retry occurred. The authorization
is consumed. Issue #167's repository repair forces an explicit FP16 model
configuration, adds a no-private zero-step model/trainer smoke, writes durable
private logs and corpus-free failure records, and retains 25-step recovery
checkpoints for fresh-GO continuation. The separately authorized A100 smoke
then completed model, LoRA, collator, and `SFTTrainer` construction in 138
seconds with zero optimizer steps. Unsloth used float32 master weights for
Gemma 3 while retaining the frozen FP16 trainer path; the prior
BF16-model/FP16-trainer construction failure did not recur. See
`results/f2_f3_nautilus_fp16_trainer_smoke_audit.md`. No PVC, corpus, private
record, training, inference, prediction, or metric was used. The smoke
authorization is consumed. Replacement training remains unauthorized and
requires a fresh exact-commit owner GO.
Issue #116's separately authorized, corpus-text-free runtime probe subsequently
completed on phone-verified Kaggle account `thgh15`. It confirmed exactly one
Tesla P100, CUDA 12.8, and importable preinstalled PyTorch 2.10.0+cu128, but
did not execute a CUDA tensor operation. Issue #125 later established that this
build does not support the P100's `sm_60` capability. Unsloth and bitsandbytes
were absent, so the runtime was not ready for the frozen B1/B2 backend. No
datasets or models were attached; no repository checkout, package
installation, private-input access, model loading, inference, or metric
occurred. See `results/b1_b2_kaggle_runtime_probe_audit.md`. The probe
authorization is consumed. Any dependency repair and any later B1 attempt
require separate fresh, scope-specific owner GOs.
Issue #119's single authorized dependency/import smoke then preserved the
PyTorch/CUDA/P100 base and successfully imported pinned Unsloth 2026.7.2 and
bitsandbytes 0.49.2, but reported `ready: false` because global `pip check`
returned one. The check output was hashed rather than classified. See
`results/b1_b2_dependency_smoke_audit.md`. No private input, model loading,
inference, or metric occurred. Its authorization is consumed. Do not start B1
until a fresh no-private diagnostic classifies the package conflict.
Issue #122's fresh no-input diagnostic classified all global `pip check`
complaints as unrelated preinstalled Kaggle-image conflicts; none involves the
B1/B2 inference package layer. Installation and Unsloth/bitsandbytes imports
passed while PyTorch/CUDA/P100 remained unchanged. See
`results/b1_b2_pip_check_diagnostic_audit.md`. The dependency gate is cleared,
but only at package-resolution/import level; issue #125 later proved the
PyTorch build cannot execute on the P100. The diagnostic authorization is
consumed and does not authorize B1.

## Non-negotiable research rules

- `Nahw-Passage` is test-only. Never train, tune prompts, or select checkpoints on it.
- Preserve official train/dev/test splits for every external dataset.
- Do not invent Arabic linguistic labels or claim expert validation.
- Never fabricate metrics, dataset access, completed runs, or citations.
- Record exact model IDs/revisions, prompts, decoding settings, seeds, hardware, and package versions.
- Save predictions as well as aggregate metrics.
- Prefer zero-cost tools and free Kaggle/Colab runtimes; do not introduce paid dependencies.
- Never commit API keys, Hugging Face tokens, Google credentials, or private datasets.

## Repository conventions

- Put reusable Python code in `scripts/`.
- Put Colab/Jupyter notebooks in `notebooks/`.
- Put small, human-readable result summaries in `results/`.
- Keep downloaded data, checkpoints, adapters, and large outputs out of Git.
- Use UTF-8 for Arabic text and preserve original strings unless normalization is part of an explicitly documented metric.
- Keep changes narrow. Do not refactor unrelated files.

## Team and agent coordination

- For non-trivial work, use one GitHub issue, one owner, one branch, and one pull request.
- Before editing, check the linked issue, current branch, `git status`, and likely overlapping pull requests or local changes.
- Prefer branch names like `codex/<issue-number>-<short-description>` or `human/<issue-number>-<short-description>`.
- Do not let two agents edit the same files at the same time unless one task explicitly depends on the other.
- Keep Notion as the lab-facing status and decision hub; update the linked task after meaningful progress, merge, or blockage.
- Follow `docs/collaboration_workflow.md` for the full team workflow.

## Validation

For Python changes, run:

```bash
python -m compileall scripts
```

For data preparation, run:

```bash
python scripts/download_nahw.py
python scripts/inspect_nahw.py
python scripts/prepare_nahw_eval.py
```

For notebooks:

- validate that the notebook is valid JSON
- make setup cells idempotent where practical
- ensure a fresh supported notebook runtime can run cells in order
- keep the 25-example pilot separate from the full 511-record run

If a required check cannot run because no GPU or external access is available, state that clearly and report what was validated instead.

## Working style

- Read the relevant docs before editing.
- Inspect existing files before creating replacements.
- For tasks expected to take multiple hours, create or update `PLANS.md` before implementation.
- Prefer a small working vertical slice over a broad unfinished system.
- End each task with a concise summary of changed files, checks run, unresolved issues, and the next step.
