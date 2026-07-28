# B1/B2 proven P100 runtime restoration audit

## Scope

Issue #132 restores the P100 runtime pattern that already completed Musahhih's
F2/F3 training and selected-adapter development inference. The exact code
commit is `9bc36e31fe486350319f363f79bfca06dbb5e7af`.

No Kaggle kernel, GPU, dataset, model, inference, training, prediction, or
metric was used for this implementation.

## Restored runtime

`scripts/bootstrap_b1_b2_p100_runtime.py` conditionally replaces Kaggle's
incompatible newer base with the previously validated P100 stack:

- PyTorch 2.6.0 from the official CUDA 12.4 wheel index;
- torchvision 0.21.0 from the same index;
- xformers 0.0.29.post3;
- torchao 0.16.0;
- NumPy 2.0.2;
- Transformers 4.56.2;
- Unsloth 2026.7.3;
- Accelerate 1.13.0;
- PEFT 0.19.1;
- TRL 0.22.2;
- datasets 4.3.0; and
- bitsandbytes 0.49.2.

These are the public versions recorded by the completed F2-P1 training and
development-smoke audits. Unsloth 2026.7.3 declares
`unsloth_zoo>=2026.7.3`; the restoration pins the minimum compatible companion
version, 2026.7.3, to prevent present-day resolver drift. Triton's installed
version is reported rather than independently changed because the official
PyTorch wheel owns that dependency.

The bootstrap skips installation when every required identity already matches.
Installer stdout/stderr are represented only by hashes in its aggregate
report. It neither imports a model nor accesses private input.

## Fresh-process safety sequence

`scripts/check_b1_b2_restored_p100.py` codifies the only valid sequence:

1. run the conditional package restoration in one process;
2. start a fresh Python process;
3. require exact restored package identities and CUDA 12.4;
4. execute and synchronize a real CUDA tensor operation on exactly one P100;
5. import-check bitsandbytes and Unsloth with
   `UNSLOTH_COMPILE_DISABLE=1`; and
6. return aggregate evidence before any private-input access or model loading.

The bootstrap subprocess has a hard 600-second timeout and the fresh-process
validation has a hard 180-second timeout. Thus a network or package failure
cannot leave this engineering smoke consuming an open-ended GPU session.

`GemmaGenerator` independently enforces the restored package identities and
sets the same Unsloth compilation guard before importing the backend. This
prevents a wrapper from bypassing the restored-runtime contract.

## Validation

- `python -m compileall scripts tests`
- 37 focused tests plus 16 subtests passed
- 235 full-suite tests plus 65 subtests passed
- current PyPI metadata confirmed that the pinned Unsloth and companion
  releases remain available and that Unsloth 2026.7.3 supports the restored
  PyTorch/xformers combination

The implementation is ready for review, not research execution. After merge,
the next eligible Kaggle action is one separately authorized no-input/no-model
smoke of `scripts.check_b1_b2_restored_p100`. A passing smoke would not itself
authorize B1-P1 inference.
