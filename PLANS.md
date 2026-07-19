# Active implementation plan

## Issue #69 — build guarded F2/F3 Kaggle QLoRA workflow

- [x] Record GO for methodology commit
  `8ca3014e6b3659e2e8c3ffc519b0255e9af6b7a6` and close issue #67.
- [x] Build a fail-closed private adapter for the frozen F2 2,000-record arm,
  F3 1,000/1,000 nested mixture, and common QALB development view.
- [x] Add synthetic-fixture tests for hashes, provenance, nested selection,
  schema, privacy, deterministic order, role guards, and non-overwrite behavior.
- [x] Create a beginner-readable Kaggle P100 workflow with arm selection,
  non-generating preflight, one-step smoke, and separately gated full training.
- [x] Reuse the exact F1 model/LoRA/optimizer/checkpoint contract and record all
  runtime, token, VRAM, artifact, and reproducibility metadata.
- [x] Validate locally, publish an aggregate-only audit, open a PR, pass CI, and
  obtain exact-commit GO before any GPU smoke or two-epoch run.
- [x] Replace fragile Kaggle cell editing with a validated private execution-
  config file after the first exact-commit smoke attempt failed at syntax
  preflight without producing a model result.
- [ ] Validate the repaired non-executing workflow, merge it through a narrow
  PR, and obtain a fresh exact-commit GO before any GPU rerun.

Do not execute model training or inference, access final-test outcomes, activate
XG, upload private artifacts publicly, or change a frozen research setting in
this task. A later GO may authorize only the explicitly named execution stage.
