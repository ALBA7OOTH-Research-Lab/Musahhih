# AGENTS.md

## Purpose

Musahhih is a research repository for improving Modern Standard Arabic grammatical error correction with open-weight language models.

Treat this file as a map, not a full manual. Follow the linked docs for details.

## Sources of truth

- Project overview and setup: `README.md`
- Experimental design: `docs/research_plan.md`
- Dataset roles and leakage rules: `docs/dataset_audit.md`
- Prior work and research gap: `docs/literature_matrix.md`
- Current implementation task: `docs/tasks/001_colab_unsloth_baseline.md`

## Current milestone

`F1-P1` natural-data training, private development smoke, the single frozen
Nahw-Passage evaluation, and the matched overcorrection/ArabicMMLU diagnostics
are complete. See `results/f1_p1_final_evaluation_audit.md` and
`results/f1_safety_diagnostics_audit.md`. QALB text, benchmark questions, model
responses, and adapter artifacts remain private.

Do not tune prompts, parsing, checkpoints, training data, or experiment
decisions from the completed Nahw-Passage or safety-diagnostic results. The next
milestone is to resolve and freeze the synthetic/mixed F2/F3 study. The proposed
`XG` synthetic operator remains disabled pending qualified linguistic review.

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
