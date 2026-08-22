# AGENTS.md

## Purpose

Musahhih is a publication repository for a controlled Modern Standard Arabic
grammatical error correction study. Keep changes narrow, auditable, and
corpus-text-free.

## Sources of truth

- Manuscript: `paper/main.tex`
- Experimental design: `docs/research_plan.md`
- Dataset roles and leakage controls: `docs/dataset_audit.md`
- Research status and allowed claims: `docs/research_completion_matrix.md`
- Artifact release rules: `docs/artifact_release_audit.md`
- Aggregate paper data: `results/research_results_consolidated.json`
- Evidence index: `results/README.md`

## Current status

The B1/B2 prompt baselines, F1 natural-only arm, F2 synthetic-only arm, F3
mixed arm, primary paired evaluation, five-seed robustness cohort,
fixed-checkpoint sensitivity, first-token sensitivity, and matched behavioral
diagnostics are complete. The manuscript reports only reviewed aggregate
evidence.

Do not rerun, reselect, retry, continue, or tune any completed experiment from
its results. Any new private-data access, model execution, inference, training,
or metric computation requires a new scope-specific owner authorization.

## Non-negotiable research rules

- `Nahw-Passage` is test-only. Never train, tune prompts, select checkpoints,
  or create development decisions from it.
- Preserve official train/dev/test roles for every external dataset.
- Do not invent Arabic linguistic labels or claim expert output validation.
- Never fabricate metrics, dataset access, completed runs, or citations.
- Keep QALB text, ArabicMMLU questions, record-level predictions, raw model
  responses, adapters, checkpoints, private logs, and credentials out of Git.
- Use UTF-8 for Arabic and preserve original strings unless normalization is an
  explicitly documented metric operation.
- Do not describe the repository as open-source until an explicit software
  license has been selected.

## Repository conventions

- `paper/`: manuscript sources and generated aggregate figures.
- `docs/`: durable study design and protocol documents.
- `results/`: small, reviewed, corpus-free aggregate evidence.
- `scripts/`: reusable data, training, evaluation, and analysis code.
- `notebooks/`: supported end-to-end notebook entry points.
- `tests/`: public regression and privacy-boundary checks.
- `data/`: public schema/example files only. Downloaded and processed datasets
  remain ignored.

Historical failed-run audits and obsolete repair infrastructure belong in Git
history, not the publication-facing tree.

## Workflow

For non-trivial work, use one GitHub issue, one owner, one `codex/<issue>-...`
branch, and one pull request. Before editing, inspect the issue, branch, status,
and overlapping pull requests. Preserve unrelated user changes.

## Validation

For Python changes:

```bash
python -m compileall -q scripts tests
python -m unittest discover -s tests -q
```

For manuscript changes:

```bash
python scripts/generate_paper_figures.py
tectonic paper/main.tex --outdir paper/build
```

Render and inspect every PDF page before delivery. If a GPU or restricted
dataset is unavailable, report that explicitly and validate only the public
surface; never substitute fabricated or partial evidence.
