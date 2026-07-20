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
- [ ] Review the selected adapter through a newly authorized private
  development-inference gate before deciding whether to proceed to F3-P1.

Do not execute F2 inference, another training run, final-test evaluation,
safety-diagnostic reruns, F3, or XG; upload private artifacts publicly; or
change a frozen research setting in this task. The F2-P1 training approval is
consumed. A later GO may authorize only its explicitly named execution stage.
