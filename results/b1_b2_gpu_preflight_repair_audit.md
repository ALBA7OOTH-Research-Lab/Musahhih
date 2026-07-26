# B1-P1/B2-P1 GPU-preflight repair audit

## Scope

Issue #112 repairs the wrapper-preflight defect identified by issue #109. This
is implementation evidence only. No private input was read, no model was
loaded, no Kaggle kernel was edited or submitted, and no inference or metric
occurred.

## Repair

`scripts.check_b1_b2_gpu_preflight` now performs the wrapper-facing runtime
gate through PyTorch. It requires:

- CUDA availability;
- exactly one CUDA device; and
- a device name containing `P100`.

The guard neither invokes `nvidia-smi` nor uses another external process. It
emits only aggregate runtime identity and runs before private-input discovery or
model loading. The final Gemma backend calls the same helper, avoiding divergent
GPU checks.

Synthetic tests cover a passing P100, absent CUDA, multiple devices, a non-P100
device, aggregate-only CLI output, and static absence of `nvidia-smi` and
`subprocess` dependencies.

## Authorization boundary

Merging this repair does not authorize a kernel edit, new version, retry,
resubmission, final-test access, model loading, inference, or B2-P1. A future
attempt requires independent review of the exact executable repair commit and a
fresh scope-specific owner GO.
