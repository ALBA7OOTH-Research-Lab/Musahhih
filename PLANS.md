# Active implementation plan

## Issue #85 — prepare the F3-P1 longest-record P100 smoke gate (complete)

- [x] Register a dedicated GitHub issue and matching verbose Notion task.
- [x] Confirm that F3-P1's frozen 2,000-record composition, hashes, prompt,
  model, seed, and training settings remain unchanged.
- [x] Replace the obsolete issue-#69-only URL check with strict validation of
  issue-comment permalinks in this repository.
- [x] Update notebook activation checks, helper tests, and user-facing docs.
- [x] Run compilation, unit, notebook JSON/AST, CLI, privacy, and secret checks.
- [x] Merge PR #86 and record exact executable workflow commit
  `6d64f699c04168cc15c045edc86389d5dc81f1bc`.

## Issue #88 — execute one F3-P1 engineering smoke (complete)

- [x] Obtain a fresh, single-use owner GO before one F3-P1 longest-record,
  one-step P100 smoke at exact commit
  `6d64f699c04168cc15c045edc86389d5dc81f1bc`.
- [x] Generate one new private F3-P1 smoke config and execute
  exactly one Kaggle P100 attempt; preserve its first terminal state.
- [x] Verify the terminal `COMPLETE` state, one optimizer step, registered
  input hashes, and 9,392,357,376 bytes of measured P100 headroom.
- [x] Record only aggregate, corpus-text-free evidence and disclose the
  private automatic `checkpoint-1` artifact-hygiene caveat.

## Issue #90/#91 — review and execute F3-P1 full training (complete)

- [x] Independently review the passing smoke, compatibility warnings, and
  automatic private checkpoint side effect.
- [x] Decide whether to repair smoke-only checkpoint saving before training or
  accept the current exact workflow for one two-epoch run.
- [x] Record a separate exact-commit, single-use GO for F3 full training.
- [x] Create a new private full-training config and fresh Kaggle
  P100 run; the smoke authorization cannot be reused.
- [x] Preserve the first terminal state, all 250 optimizer steps, both epoch
  development losses, selected private `checkpoint-250`, and corpus-text-free
  aggregate hashes.
- [ ] Make later, separate decisions about development inference and final
  tests.

The F3 smoke and full-training authorizations are consumed. Training completion
does not authorize inference, final-test evaluation, safety reruns, F1/F2
reruns, or XG.

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
- [x] Preserve and stop the second authorized attempt after Kaggle's current
  nested dataset mount exposed an obsolete flat-path assumption before model
  loading or an optimizer step.
- [x] Repair private-input discovery for current nested Kaggle mounts and
  validate the non-executing workflow locally.
- [x] Merge the nested-mount repair through PR #72 at
  `000c8ccd4db215ca588fa246659c599986660d98`.
- [x] Repair the conditional P100 dependency preflight through PR #74 at
  `f64edead0367e7659b107e5c4c309ed811d09071`.
- [x] Execute the exact-commit F2-P1 longest-record, one-step P100 smoke once;
  the 1 GiB headroom gate passed with 9,040,035,840 bytes measured headroom.
- [x] Preserve only aggregate, corpus-text-free smoke evidence in GitHub and
  Notion; no benchmark score or final-test result was produced.
- [x] Obtain review and a separate exact-commit GO for one F2-P1 full-training
  run at `f64edead0367e7659b107e5c4c309ed811d09071`.
- [x] Preserve full-training attempt 001 after it failed closed at repository
  preflight: current `main` was cloned instead of the approved workflow commit;
  no private-data validation, model load, optimizer step, or result occurred.
- [x] Merge issue #78's immutable approved-commit checkout repair through PR
  #79 at `ea4766ee205922c9fd4cb1af0357cca19bcfd59b`.
- [x] Record the owner's explicit waiver of an additional repair-only smoke and
  one-attempt F2-P1 full-training authorization.
- [x] Complete one private F2-P1 two-epoch P100 run and select
  `checkpoint-125` by the frozen common-development assistant-token loss rule.
- [x] Verify and record only aggregate, corpus-text-free run evidence and the
  selected private adapter hash.
- [x] Issue #82: freeze and implement a disabled-by-default F2-P1 private
  development-smoke workflow for selected `checkpoint-125`.
- [x] Validate and merge the exact workflow commit before execution.
- [x] Execute the single authorized deterministic 25-record QALB-development
  run, preserve its first terminal state, and publish only text-free evidence.
- [x] Audit the private outputs: 25/25 rows completed, no output was empty, no
  parser warning occurred, and all private hashes matched. F2-P1 is technically
  reloadable; the private development metric remains unpublished.
- [ ] Make a separate research decision about the next comparison stage. No
  final-test evaluation or F3 training is implied by the technical gate.

The F2-P1 private development-smoke authorization is consumed. Do not execute
another development run, training run, final-test evaluation, safety-diagnostic
rerun, F3, or XG; upload private artifacts publicly; or change a frozen
research setting without a fresh scope-specific GO. The completed technical
gate cannot change the selected checkpoint, prompt, or parser.
