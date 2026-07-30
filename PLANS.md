# Active implementation plan

## Issue #165 — use proven RWX storage for private staging

- [x] Preserve issue #163's unbound-PVC failure without retry or private upload.
- [x] Delete the unscheduled Pod and unbound, data-free PVC after evidence
  capture.
- [x] Switch from the waiting `cephfs` provisioner to the namespace's proven
  `rook-cephfs` RWX class.
- [x] Retain the exact PVC, no-GPU Pod, write-once upload, hash/count, and
  training-separation contracts.
- [x] Complete focused and full local validation.
- [x] Complete Kubernetes dry-run validation at the repair commit.
- [ ] Open and merge a review PR.
- [ ] Obtain a fresh exact-commit owner GO before replacement staging.

Issue #165 is repository-only repair work. It authorizes no PVC, Pod, private
upload, GPU allocation, model load, training, inference, metric, retry, or
continuation.

## Issue #163 — finalize import order and private staging gate

- [x] Preserve issue #161's passing no-input A100/compiler/import preflight.
- [x] Assemble the three frozen ignored local files with exact expected hashes
  and counts without printing corpus text.
- [x] Import Unsloth before bitsandbytes, datasets, and TRL.
- [x] Separate one CPU-only PVC/staging Pod from the five A100 training Jobs.
- [x] Make staging write-once, hash/count gated, and corpus-text-free.
- [x] Require the exact staging completion manifest before training opens the
  three private record files.
- [x] Complete focused and full local validation.
- [x] Complete Kubernetes dry-run validation at the preparation commit.
- [ ] Open and merge a review PR.
- [ ] Obtain separate fresh exact-commit owner GOs for staging, a final
  import-order preflight, and the five-Job training wave.

Issue #163 is repository-only preparation. It authorizes no Kubernetes object,
private upload, GPU allocation, model load, training, inference, metric, retry,
or continuation.

## Issue #161 — use a compiler-capable pinned Nautilus runtime

- [x] Preserve issue #159's failed compiler import gate without retry.
- [x] Release the terminal failed Job after recording aggregate diagnostics.
- [x] Retain PyTorch 2.6.0, CUDA 12.4, and cuDNN 9 while switching from the
  official `runtime` image to its matching official `devel` image.
- [x] Pin the full published Linux/AMD64 image digest.
- [x] Require a discoverable C compiler before the bitsandbytes/Unsloth import
  gate and add focused regression coverage.
- [x] Complete focused and full local validation.
- [x] Complete Kubernetes dry-run validation at the repair commit.
- [ ] Open and merge a review PR.
- [ ] Obtain a fresh exact-commit owner GO before one replacement preflight.

Issue #161 is repository-only repair work. It authorizes no Kubernetes object,
GPU allocation, private-input access, model load, training, inference, metric,
retry, or replacement preflight.

## Issue #159 — remove Nautilus main-runtime git dependency

- [x] Preserve issue #157's failed replacement preflight without retry.
- [x] Release the terminal failed Job after recording aggregate diagnostics.
- [x] Replace the main container's `git rev-parse` call with strict detached
  `.git/HEAD` verification from the init container's validated checkout.
- [x] Add regression coverage for an empty runtime `PATH`, symbolic HEAD,
  malformed commit IDs, and missing metadata.
- [x] Complete focused and full local validation.
- [x] Complete Kubernetes dry-run validation at the repair commit.
- [ ] Open and merge a review PR.
- [ ] Obtain a fresh exact-commit owner GO before one replacement preflight.

Issue #159 is repository-only repair work. It authorizes no Kubernetes object,
GPU allocation, private-input access, model load, training, inference, metric,
retry, or replacement preflight.

## Issue #157 — repair Nautilus checkout-image digest validation

- [x] Preserve issue #155's failed first preflight state without retry.
- [x] Release the failed pod's scheduled A100 after recording its diagnostics.
- [x] Replace the malformed 62-character checkout-image checksum with the
  authoritative 64-character Linux/AMD64 digest for the same image tag.
- [x] Reject unpinned or malformed container-image digests before manifest
  generation.
- [x] Complete focused and full local validation.
- [x] Complete Kubernetes dry-run validation at the repair commit.
- [ ] Open and merge a review PR.
- [ ] Obtain a fresh exact-commit owner GO before one replacement preflight.

Issue #157 is repository-only repair work. It authorizes no Kubernetes object,
GPU allocation, private-input access, model load, training, inference, metric,
retry, or replacement preflight.

## Issue #155 — prepare five-seed F2/F3 Nautilus replication

- [x] Register a dedicated preparation issue and branch.
- [x] Confirm the namespace can create Jobs/PVCs and has quota for five A100s.
- [x] Freeze five paired seeds, balanced arm order, A100 runtime, and post-hoc
  interpretation.
- [x] Add fail-closed Nautilus activation, A100 preflight, paired training, and
  write-once private output handling.
- [x] Generate five Job manifests with no Nahw-Passage mount and no automatic
  retry.
- [x] Add focused tests and corpus-text-free preparation evidence.
- [ ] Open a review PR and record the exact merged executable commit.
- [ ] Obtain a separate GO for one no-input/no-model A100 smoke.
- [ ] Obtain another exact-commit GO before the five-job training wave.

Issue #155 is preparation only. It authorizes no cluster resource creation,
private-input access, model loading, optimizer step, training, inference,
Nahw-Passage access, metric, retry, or continuation.

## Issue #122 — classify the B1/B2 global package conflict

- [x] Register a diagnostic-repair issue and branch.
- [x] Preserve the exact issue #119 installation, runtime, and import checks.
- [x] Add bounded, character-sanitized `pip check` conflict lines.
- [x] Complete focused and full validation.
- [ ] Merge; the exact executable implementation commit is
  `1968cada39efd60a446a89271fe20c4276cd0127`.
- [x] Obtain and consume a fresh GO for one no-private diagnostic smoke.
- [x] Classify every global conflict as unrelated to the B1/B2 inference
  package layer.

Issue #122 authorizes no kernel, private-input access, model load, inference,
training, metric, or B1/B2 final segment.

## Issue #119 — add a PyTorch-preserving B1/B2 dependency smoke

- [x] Register a dedicated implementation issue and branch.
- [x] Freeze the observed P100 base runtime before package installation.
- [x] Use public PyPI only and constrain PyTorch, torchvision, NumPy, and
  xformers so the working CUDA stack cannot be replaced.
- [x] Pin the validated Unsloth, bitsandbytes, Transformers, and TRL layer.
- [x] Add import checks without private input or model loading.
- [x] Complete focused and full validation.
- [ ] Merge; the exact executable implementation commit is
  `3b28f99f4bbfe889ffaf56b1063ebfdc23a6ae72`.
- [x] Obtain and consume a fresh GO for one no-private dependency/import
  smoke.
- [x] Preserve terminal `COMPLETE`, successful installation and imports, and
  unchanged PyTorch/CUDA/P100 base.
- [x] Record the remaining global `pip check` failure without guessing its
  source.
- [ ] Repair the aggregate diagnostic to classify the package conflict.

Issue #119 authorizes no Kaggle submission, private-input access, model loading,
inference, training, metric, prompt/parser change, or B1/B2 final segment.

## Issue #116 — make the B1/B2 Kaggle bootstrap network-safe

- [x] Register a repair-only issue and branch without authorizing another
  final attempt.
- [x] Separate corpus-text-free runtime discovery from dependency
  installation, repository checkout, private-input access, and model loading.
- [x] Add a standalone probe for Python, PyTorch, CUDA, GPU identity, and
  installed inference-package metadata.
- [x] Validate the standalone probe with synthetic fixtures, compilation, the
  full test suite, and static forbidden-access checks.
- [x] Merge the repair; its exact executable implementation commit is
  `9572bad1c77b30cf8edef58d1619a94c869c835e`.
- [x] Obtain and consume a fresh scope-specific owner GO for one no-private
  Kaggle runtime probe on phone-verified account `thgh15`.
- [x] Preserve terminal `COMPLETE` and audit one P100, CUDA 12.8, working
  PyTorch 2.10.0+cu128, and the missing Unsloth/bitsandbytes inference layer.
- [x] Confirm zero datasets or models attached and no network, private-input,
  model-loading, inference, or metric access.
- [ ] Implement a dependency-only bootstrap that preserves the working
  PyTorch installation.
- [ ] Obtain a separate GO for a no-private import smoke before any B1-P1
  final segment.
- [ ] Obtain another separate exact-commit GO before a B1-P1 final segment.

The runtime-probe authorization is consumed. It did not authorize
Nahw-Passage or QALB access, model loading, inference, training, prompt/parser
changes, metric access, or a final attempt. The dependency smoke and B1-P1
final segment require separate authorizations.

## Issue #114 — execute one repaired B1-P1 final attempt

- [x] Record a fresh exact-repair-commit, account-specific, single-use owner
  GO.
- [x] Prepare a fresh private kernel slug without editing or versioning the
  failed issue #109 kernel.
- [x] Verify the repaired wrapper order, frozen hashes, private dataset, P100
  metadata, GPU quota, and permanent GO before submission.
- [x] Submit exactly one private kernel version and consume the authorization.
- [x] Preserve terminal Kaggle `ERROR` after repeated DNS failures resolving
  `download.pytorch.org` during the pinned PyTorch install.
- [x] Confirm that repository checkout, repaired GPU preflight, private-input
  access, model loading, inference, predictions, and metrics never occurred.
- [x] Record the corpus-text-free failure diagnostic without retry.

Issue #114 produced no research result and did not exercise the issue #112 GPU
repair. Do not edit the kernel, push another version, retry, resubmit, or run
B2-P1. Any future attempt requires a fresh exact-commit, scope-specific owner
GO.

## Issue #112 — repair the B1/B2 GPU preflight

- [x] Register a repair-only issue and branch without authorizing another
  kernel.
- [x] Replace the external `nvidia-smi` assumption with a reusable PyTorch
  CUDA/device guard.
- [x] Require CUDA, exactly one device, and a P100 identity without loading a
  model or reading private inputs.
- [x] Reuse the same guard inside the final Gemma backend.
- [x] Add a wrapper-facing aggregate-only preflight command.
- [x] Cover passing P100, missing CUDA, wrong device count, wrong GPU type, and
  absence of external-command dependencies with synthetic tests.
- [x] Complete full validation and record exact executable repair commit
  `f8c7ffd74993785f118bb32e0145295b31c5048d` for independent review.

Issue #112 is preparation only. It does not authorize a Kaggle submission,
kernel version, retry, final-test access, model loading, inference, B2-P1, or
continuation. A future attempt requires a fresh exact-commit owner GO.

## Issue #109 — execute one timeout-safe B1-P1 final segment

- [x] Record an exact-commit, account-specific, single-use owner GO.
- [x] Verify the frozen 511-record input and five-demonstration B1 bundle
  hashes without printing corpus text.
- [x] Create a private input dataset and submit exactly one private kernel
  version from Kaggle account `alba7oothresearchlab`.
- [x] Preserve terminal Kaggle `ERROR` after the wrapper could not find the
  external `nvidia-smi` executable at approximately 1.07 seconds.
- [x] Confirm that repository checkout, private-input access, model loading,
  inference, predictions, and metrics never occurred.
- [x] Record the corpus-text-free failure diagnostic and consume the
  authorization without retry.

Issue #109 produced no research result. Server metadata confirms that GPU was
requested and the account had 30 GPU-hours remaining; the failure does not
establish whether CUDA was available because the wrapper stopped before checking
it. Do not edit the kernel, push another version, retry, resubmit, or run B2-P1.
A future attempt requires a reviewed repair of the brittle external-command GPU
preflight and a new exact-commit, scope-specific owner GO.

## Issue #107 — add a timeout-safe resumable B1/B2 final gate

- [x] Register and claim a dedicated implementation issue and branch without
  authorizing model loading, inference, or final-test access.
- [x] Preserve the frozen B1-P1/B2-P1 prompts, bundle, parser, input identity,
  model revision, decoding, seed, statistic, and canonical run IDs.
- [x] Add a 9.5-hour safe stop measured from the private wrapper's first
  executable line.
- [x] Flush and `fsync` each private prediction row and atomically maintain a
  corpus-text-free progress manifest.
- [x] Return a successful metric-free `incomplete_time_budget` handoff that
  explicitly requires a fresh owner GO.
- [x] Verify the exact execution identity and complete private prefix before
  copying it into a new write-once segment; never regenerate completed rows.
- [x] Require the exact approved commit, issue-comment GO, frozen model/input/
  bundle identities, P100 runtime, and explicit final confirmation before
  model loading.
- [x] Cover interruption, successful continuation, hash/schema/order/score
  tampering, path privacy, and write-once behavior with synthetic fixtures.
- [x] Complete full validation, publish PR #108, and record exact executable
  implementation commit `16b4ca3dec6e757b41e233b22bc16cc6a57be4dd`
  for independent review.

Issue #107 is implementation only. It does not authorize Nahw-Passage access,
model loading, inference, Kaggle submission, continuation, QALB test, training,
safety diagnostics, prompt/parser changes, or XG. Every future segment requires
a fresh exact-commit, scope-specific owner GO.

## Issue #104 — prepare publication synthesis and remaining research gates

- [x] Register and claim the publication-readiness issue without authorizing
  inference, test access, training, or artifact release.
- [x] Audit the completed B0/F1/F2/F3 evidence, B1/B2 technical gate, F1 safety
  protocol, dataset licenses, and current private-artifact boundaries.
- [x] Add a machine-readable consolidated aggregate result.
- [x] Add a claim-by-claim research-completion matrix and paper outline.
- [x] Add an artifact-release audit that distinguishes technically available
  artifacts from artifacts legally and ethically cleared for release.
- [x] Record the execution-free B1/B2 final-gate readiness gaps, including a
  timeout-safe continuation requirement before any future Kaggle submission.
- [x] Propose, but do not freeze or execute, matched F2/F3 overcorrection and
  ArabicMMLU capability-retention diagnostics.
- [x] Validate compilation, tests, JSON, cross-document metrics, privacy,
  credential patterns, ignored artifacts, and diff hygiene.
- [x] Merge only corpus-text-free planning and aggregate evidence through PR
  #105 at `418c127bd0016a91b30ef2d02da8447cdeaa66ef`; obtain separate owner
  decisions for each optional future experiment or release.

Issue #104 does not authorize B1/B2 final inference, F2/F3 safety diagnostics,
QALB test access, training, checkpoint changes, Nahw-Passage access, XG,
linguistic labeling, or publication of adapters and record-level artifacts.

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

## Issue #93 — prepare and execute the F3-P1 private development smoke (complete)

- [x] Freeze the selected private `checkpoint-250`, adapter/config/selection
  hashes, model revision, prompt, parser, seed, and decoding contract.
- [x] Reuse the exact 25 deterministic QALB development record IDs from the
  completed F2-P1 smoke by retaining its selector namespace and locking the
  selected-record-ID digest.
- [x] Add a disabled-by-default notebook and strict write-once private
  activation-config helper.
- [x] Complete compilation, unit, notebook JSON/AST, privacy, stale-reference,
  credential-pattern, and diff checks without executing the gate.
- [x] Merge the implementation PR and record exact commit
  `2982a2ed62f0d59e51eacbbddb02a03994c73e4b`.
- [x] Obtain a separate exact-commit, single-use owner GO before any private
  model inference.
- [x] Submit exactly one private P100 attempt and preserve its first terminal
  `COMPLETE` state without retry.
- [x] Verify 25/25 completed records, zero empty outputs, zero parser warnings,
  frozen hashes, and corpus-text-free public evidence.

The single-use authorization is consumed. The private development metric and
record-level responses were not read or published. This technical gate does
not authorize final-test evaluation, another development run, safety
diagnostics, training, F1/F2, or XG.

## Issue #98 — add a timeout-safe F2/F3 evaluation handoff

- [x] Record issue #96 kernel version 1's first terminal state as
  `CANCEL_ACKNOWLEDGED`; do not download outputs, retry, or report metrics.
- [x] Register a repair-only issue and branch without authorizing inference.
- [x] Add a fixed 9.5-hour safe-stop threshold measured from the private
  wrapper's first executable line.
- [x] Flush and `fsync` every private row and atomically maintain a
  corpus-text-free progress manifest.
- [x] Return a successful metric-free timed handoff before Kaggle's cutoff.
- [x] Add a hash- and prefix-verified continuation path that never regenerates
  completed records and always requires a fresh exact-commit GO.
- [x] Complete compilation, unit, disabled-mode, privacy, credential-pattern,
  and diff validation without final-test access or model loading.
- [x] Merge PR #99 and record exact repair commit
  `cf25f6691a18515407c63e7bab7b6b4af405d731` for independent review.
- [x] Obtain one fresh owner GO for a replacement segment at exact workflow
  commit `80194505bd00513f4e1661ef10798f79b83ae16b`.
- [x] Submit exactly one private P100 segment and preserve terminal Kaggle
  `COMPLETE` / evaluator `incomplete_time_budget`.
- [x] Audit the metric-free handoff: F2-P1 511/511, F3-P1 168/511, exact frozen
  hashes, ordered-prefix alignment, and corpus-text-free summaries passed.
- [x] Merge the narrow public handoff audit through PR #101 at exact commit
  `75cc315a7f1f231dc2dea8c777c7e729739050c8`.
- [x] Obtain a separate exact-commit continuation GO on issue #98 and submit
  exactly one private continuation kernel.
- [x] Reuse the byte-identical 511-record F2-P1 artifact and 168-record F3-P1
  prefix without regenerating completed records.
- [x] Complete F3-P1 511/511 and preserve terminal Kaggle/evaluator `COMPLETE`.
- [x] Audit exact hashes, ordered alignment, schemas, score consistency, arm
  counts, warnings, and all five preregistered paired comparisons without
  printing corpus text or private responses.
- [x] Publish only the reviewed corpus-text-free final audit and summary.

The cancelled issue #96 authorization and both issue #98 segment
authorizations are consumed. The matched evaluation is complete. Do not repeat
it or use its frozen-test results to tune prompts, parsing, checkpoints,
training data, or experiment decisions.

## Issue #96 — freeze the matched F2/F3 final-evaluation gate (complete)

- [x] Register a dedicated issue and branch without authorizing execution.
- [x] Freeze both selected checkpoints, adapter/config/selection hashes, the
  511-record Nahw input, accepted B0/F1 predictions, prompt, parser, decoding,
  run order, statistics, and retry rules.
- [x] Keep F2/F3 private development metrics blinded and QALB test outside the
  current study.
- [x] Add a disabled-by-default evaluator and synthetic/static tests that do
  not read Nahw-Passage or load a model.
- [x] Complete compilation, focused unit/pytest, disabled-mode, metadata-only
  adapter, privacy, credential-pattern, and diff validation without test access.
- [x] Merge the implementation through PR #97 at exact commit
  `22cc89164b4ad00476c91cb29f95e9e34e6f56b3`.
- [x] Obtain and consume one exact-commit owner GO.
- [x] Preserve kernel version 1's first terminal state,
  `CANCEL_ACKNOWLEDGED`, after Kaggle's hard runtime cutoff; report no metric,
  download no output, and do not retry.

The authorization is consumed. The cancelled run produced no reviewed result.
Any future attempt depends on issue #98's timeout-safe repair and a fresh
scope-specific owner GO.

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

## Issue #125 — execute one B1-P1 final segment (failed; audit complete)

- [x] Obtain one exact-commit, scope-specific owner GO for B1-P1 only.
- [x] Submit exactly one private Kaggle kernel version and preserve its first
  terminal `ERROR` state without retry.
- [x] Verify that repository, GPU-identity, dependency, and private-artifact
  hash gates passed.
- [x] Identify the terminal failure at approximately 114.95 seconds: the exact
  511-row private input uses `id`, while `run_prompt_baseline` requires
  `record_id`.
- [x] Confirm that model loading, inference, predictions, metrics, and training
  were never reached.
- [x] Record the independent P100 blocker: PyTorch 2.10.0+cu128 does not
  support `sm_60`, and the existing preflight executed no CUDA tensor
  operation.
- [x] Publish only corpus-text-free evidence and keep the private log ignored.
- [ ] Under a new repair issue, implement and review exact private-input
  consumer validation and an executable P100 CUDA preflight.

Issue #125's authorization is consumed. Do not edit, resubmit, retry, or launch
B2-P1. Any future B1-P1 attempt requires a reviewed exact repair commit and a
fresh scope-specific owner GO.

## Issue #127 — repair B1/B2 input and executable-GPU preflights

- [x] Register a repair-only issue and branch without authorizing Kaggle or
  inference.
- [x] Accept the frozen prepared-Nahw `id` deterministically while retaining
  canonical `record_id` support and rejecting conflicting aliases.
- [x] Add a corpus-text-free validator that requires the exact frozen input
  hash before loading its consumer schema.
- [x] Validate all 511 ignored private rows and unique resolved identities
  without changing the input bytes or printing corpus text.
- [x] Require a real CUDA tensor operation, reduction, result check, and
  synchronization in the P100 preflight before private-input access.
- [x] Add focused success/failure and privacy tests.
- [x] Complete compilation, focused/full tests, exact private-artifact
  validation, diff, JSON, and credential-pattern checks.
- [x] Merge the repair through PR #128 at
  `84566e8a7b114c942047a3c14455b83e4cc35f7b`.
- [ ] Under a separate fresh GO, run only the repaired no-input/no-model P100
  preflight smoke.

Issue #127 authorizes no Kaggle submission or research execution. Even a later
passing P100 smoke would not authorize B1-P1 or B2-P1 inference.

## Issue #130 — run one repaired no-input P100 operation smoke (complete)

- [x] Obtain a fresh exact-commit owner GO for one no-input/no-model smoke.
- [x] Submit exactly one private P100 kernel version with zero dataset and model
  attachments.
- [x] Verify startup immediately and preserve first terminal `ERROR`.
- [x] Confirm exact repository checkout and fast fail-closed rejection of the
  incompatible PyTorch/P100 CUDA operation.
- [x] Confirm no private input, model loading, inference, training,
  predictions, or metric.
- [x] Preserve only the ignored private log and publish aggregate evidence.

Issue #130's authorization is consumed. Do not edit, retry, resubmit, or launch
an evaluation. A future repair must choose and review a P100-compatible runtime
or another accelerator, then obtain a fresh GO for another no-input executable
smoke.

## Issue #132 — restore the already proven P100 runtime

- [x] Recover the exact successful F2/F3 P100 bootstrap and final recorded
  package identities.
- [x] Conditionally restore official PyTorch 2.6.0/torchvision 0.21.0 CUDA
  12.4 wheels rather than preserving incompatible PyTorch 2.10.
- [x] Pin the recorded compatible inference stack and the minimum matching
  Unsloth Zoo companion version.
- [x] Disable Unsloth compilation on `sm_60`.
- [x] Require fresh-process package identity, CUDA-operation, synchronization,
  and inference-import validation before private input.
- [x] Enforce the same runtime contract again inside `GemmaGenerator`.
- [x] Pass compilation, focused tests, and the full test suite without Kaggle
  or model execution.
- [x] Cap restoration at 600 seconds and fresh-process validation at 180
  seconds so a smoke cannot consume an open-ended GPU session.
- [ ] Merge the reviewed repair and record its merge commit.
- [ ] Under a separate fresh GO, run one no-input/no-model restored-runtime
  smoke.

Issue #132 authorizes no Kaggle submission or B1/B2 inference. A later passing
runtime smoke would consume its own GO and still would not authorize final
evaluation.

## Issue #135 — run one credit-capped restored-P100 smoke (complete)

- [x] Obtain one exact-commit, no-input/no-model owner GO.
- [x] Submit one private P100 kernel with zero dataset/model attachments.
- [x] Verify startup immediately and monitor through terminal `COMPLETE`.
- [x] Restore the recorded PyTorch 2.6.0+cu124/CUDA 12.4 inference stack.
- [x] Pass exact identities, a synchronized CUDA operation, and
  Unsloth/bitsandbytes imports with compilation disabled.
- [x] Complete in approximately 268 seconds under the hard time caps.
- [x] Publish only aggregate evidence and keep the private log ignored.

Issue #135's authorization is consumed. No retry or second version is allowed.
B1/B2 evaluation remains unauthorized pending a separately reviewed,
timeout-safe wrapper and fresh exact-commit GO.

## Issue #137 — prepare timeout-safe B1-P1 final segment

- [x] Reuse the restored P100 runtime that passed issue #135.
- [x] Generate a write-once private P100 package from an exact commit and GO.
- [x] Keep private-input discovery after the restored-runtime gate.
- [x] Freeze the B1 input, bundle, model, revision, prompt, seed, and decoding.
- [x] Retain the 34,200-second safe stop and per-row durable persistence.
- [x] Accept only complete or metric-free resumable handoff terminal states.
- [x] Add synthetic/static tests without reading private corpus text.
- [ ] Merge the preparation and record its exact executable commit.
- [ ] Obtain a separate owner GO before any Kaggle submission.

Issue #137 authorizes preparation only. It authorizes no private-input access,
model loading, inference, metric, Kaggle submission, retry, continuation, or
B2-P1 run.

## Issue #139 — run one timeout-safe B1-P1 final segment (complete)

- [x] Obtain the exact-commit owner GO.
- [x] Generate and hash the write-once private kernel package.
- [x] Submit exactly version 1 on the passing restored P100 runtime.
- [x] Complete all 511 records before the 34,200-second safe stop.
- [x] Verify exact input, bundle, prompt, model, revision, seed, and decoding.
- [x] Reproduce record alignment, parser outputs, exact-match booleans, counts,
  hashes, and staged paired statistics without printing corpus text.
- [x] Keep predictions, prompts, raw responses, gold values, and logs private.
- [x] Publish only the corpus-text-free aggregate audit.

Issue #139's authorization is consumed. Do not rerun B1-P1 or tune from the
result. B2-P1 remains unauthorized.

## Issue #141 — prepare timeout-safe B2-P1 final segment

- [x] Reuse the runtime and timeout-safe runner that completed B1-P1.
- [x] Generate a write-once private P100 package from an exact commit and GO.
- [x] Keep private-input access after the restored-runtime gate.
- [x] Address and hash only the frozen test input; pass no B1 bundle.
- [x] Freeze B2 prompt, model, revision, seed, greedy decoding, and 32 tokens.
- [x] Retain the 34,200-second safe stop and per-row durable persistence.
- [x] Add synthetic/static tests without reading private corpus text.
- [ ] Merge the preparation and record its exact executable commit.
- [ ] Obtain a separate owner GO before any Kaggle submission.

Issue #141 authorizes preparation only. It authorizes no private-input access,
model loading, inference, metric, Kaggle submission, retry, continuation, or
B1-P1 repeat.

## Issue #143 — run one timeout-safe B2-P1 final segment (failed closed)

- [x] Obtain the exact-commit owner GO.
- [x] Generate and hash the write-once private kernel package.
- [x] Submit exactly version 1.
- [x] Pass exact checkout and the restored P100 runtime gate.
- [x] Preserve terminal `ERROR` when the fixed input-mount path did not exist.
- [x] Confirm no corpus file open, model load, inference, prediction, or metric.
- [x] Publish only aggregate non-corpus failure evidence.
- [x] Do not retry or submit version 2.

Issue #143's authorization is consumed. A future B2 attempt requires a reviewed
mount-discovery repair and a fresh exact-commit owner GO.

## Issue #145 — repair B2 mount discovery

- [x] Remove the fixed Kaggle mount slug.
- [x] Recursively locate only `nahw_gec_test.jsonl`.
- [x] Require exactly one candidate and the frozen SHA-256.
- [x] Keep the B1 bundle unopened and unpassed.
- [x] Preserve all runtime, protocol, and timeout safeguards.
- [x] Validate locally without Kaggle or private corpus access.
- [ ] Merge and obtain a fresh exact-commit GO before another B2 attempt.

## Issue #147 — run repaired B2-P1 final segment (complete)

- [x] Complete 511/511 with no bundle and zero empty outputs.
- [x] Reproduce alignment, hashes, counts, and staged paired statistics.
- [x] Keep all record-level artifacts private.
- [x] Publish only corpus-text-free evidence.

Issue #147's authorization is consumed. Do not rerun or tune from B2-P1.

## Issue #167 — repair A100 FP16 initialization and crash safety

- [x] Preserve and report issue #155's five terminal failures without retry.
- [x] Force the frozen FP16 dtype during Gemma model loading on A100.
- [x] Add a no-private, zero-step exact model/collator/trainer smoke stage.
- [x] Give every fresh GO a unique write-once Job, log, exit, and attempt ID.
- [x] Persist complete stdout/stderr and corpus-free failure records on the PVC.
- [x] Retain recovery checkpoints every 25 steps without changing selection.
- [x] Permit only fresh-GO, identity-verified checkpoint/arm continuation.
- [ ] Pass focused and full validation.
- [ ] Obtain review and merge the repository-only repair.
- [ ] Obtain a fresh exact-commit GO before one FP16 trainer smoke.
- [ ] Obtain a later separate GO before any replacement training wave.

Issue #167 authorizes repository preparation only. It authorizes no GPU
execution, private-input access, training, retry, continuation, inference,
prediction, metric, Nahw-Passage access, or QALB-test access.
