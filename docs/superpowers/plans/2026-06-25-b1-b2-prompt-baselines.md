# B1/B2 Prompt Baselines Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement public, testable scaffolding for the frozen B1-P1 and B2-P1 prompt baselines without exposing private QALB text or touching Nahw-Passage final evaluation.

**Architecture:** Add three focused modules: prompt rendering, private B1 demonstration-bundle selection, and canonical run/artifact safeguards. Keep model execution and private-data validation gated so synthetic tests can verify logic publicly while real QALB/Nahw artifacts remain ignored.

**Tech Stack:** Python standard library, existing `scripts.prepare_nahw_eval.PROMPT`, existing `scripts.nahw_baseline_utils` parser, `unittest` synthetic fixtures.

---

### Task 1: Prompt assembly snapshots

**Files:**
- Create: `tests/test_baseline_prompts.py`
- Create: `scripts/baseline_prompts.py`

- [ ] **Step 1: Write failing tests**

Create tests that assert B1-P1 and B2-P1 render byte-for-byte frozen templates, B1 requires exactly five demos, and B0 uses the existing `prepare_nahw_eval.PROMPT`.

- [ ] **Step 2: Run tests to verify RED**

Run: `python -m unittest tests.test_baseline_prompts -q`

Expected: import failure because `scripts.baseline_prompts` does not exist.

- [ ] **Step 3: Implement prompt module**

Create `scripts/baseline_prompts.py` with `PromptDemo`, `render_b0_prompt`, `render_b1_prompt`, `render_b2_prompt`, `prompt_sha256`, and constants for protocol IDs.

- [ ] **Step 4: Run tests to verify GREEN**

Run: `python -m unittest tests.test_baseline_prompts -q`

Expected: all prompt snapshot tests pass.

### Task 2: B1 demonstration selection

**Files:**
- Create: `tests/test_prepare_b1_prompt_bundle.py`
- Create: `scripts/prepare_b1_prompt_bundle.py`

- [ ] **Step 1: Write failing tests**

Create synthetic fixture tests for M2 parsing, candidate filtering, skipped non-train/ineligible/multi-token/empty/repeated-token/out-of-length candidates, deterministic digest ordering, distinct-record selection, identity hash, and output privacy boundaries.

- [ ] **Step 2: Run tests to verify RED**

Run: `python -m unittest tests.test_prepare_b1_prompt_bundle -q`

Expected: import failure because `scripts.prepare_b1_prompt_bundle` does not exist.

- [ ] **Step 3: Implement bundle module**

Create dataclasses for private records and selected candidates, implement frozen candidate filtering and `SHA-256(candidate_identity + "|B1-P1")` ordering, write private text-bearing bundle JSON only to caller-specified ignored output paths, and fail closed against expected structural counts and selected identity hash.

- [ ] **Step 4: Run tests to verify GREEN**

Run: `python -m unittest tests.test_prepare_b1_prompt_bundle -q`

Expected: all synthetic selection tests pass.

### Task 3: Canonical output safeguards

**Files:**
- Create: `tests/test_run_prompt_baseline.py`
- Create: `scripts/run_prompt_baseline.py`

- [ ] **Step 1: Write failing tests**

Create tests for canonical experiment IDs, `outputs/<experiment-id>/` paths, refusal to overwrite existing run directories, final Nahw gating, summary hash helpers, and no model execution during dry planning.

- [ ] **Step 2: Run tests to verify RED**

Run: `python -m unittest tests.test_run_prompt_baseline -q`

Expected: import failure because `scripts.run_prompt_baseline` does not exist.

- [ ] **Step 3: Implement run scaffold**

Create helpers and a CLI that validates experiment IDs, prepares non-overwriting run directories, records prompt/bundle/input hashes, and refuses `nahw-passage` unless an explicit confirmation flag is set.

- [ ] **Step 4: Run tests to verify GREEN**

Run: `python -m unittest tests.test_run_prompt_baseline -q`

Expected: all output-safeguard tests pass.

### Task 4: Documentation and report

**Files:**
- Modify: `README.md`
- Create: `results/b1_b2_prompt_baseline_validation.md`

- [ ] **Step 1: Update README**

Document how to run synthetic tests and how licensed members can generate the private B1 bundle without committing text-bearing outputs.

- [ ] **Step 2: Add corpus-text-free report**

Record implemented safeguards, validation commands, and which private-data/model checks were not run locally.

### Task 5: Full validation and publish

**Files:**
- All changed files above.

- [ ] **Step 1: Run validation**

Run:

```bash
python -m compileall scripts
python -m unittest discover -s tests -q
git grep -n "<restricted-data-or-secret-patterns>"
```

- [ ] **Step 2: Review diff for research/data risks**

Run:

```bash
git status --short
git diff --stat
git diff -- README.md docs/superpowers/plans/2026-06-25-b1-b2-prompt-baselines.md results/b1_b2_prompt_baseline_validation.md scripts tests
```

- [ ] **Step 3: Commit, push, PR, Notion**

Stage only intended files, commit, push `codex/2-b1-b2-prompt-baselines`, open a draft PR linked to issue #2, update Notion with branch/commit/PR/validation, and move the task to Review.
