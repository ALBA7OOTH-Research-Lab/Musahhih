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
