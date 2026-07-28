# B1/B2 restored-P100 runtime smoke audit

## Scope

Issue #135 authorized exactly one private, credit-capped, no-input/no-model
smoke of the restored P100 runtime at merged commit
`15ce99dc3b1d84ae6de418be1ea1cbcf0eb82644`.

The private kernel was
[`thgh15/musahhih-b1-b2-restored-p100-15ce99d-r01`](https://www.kaggle.com/code/thgh15/musahhih-b1-b2-restored-p100-15ce99d-r01),
version 1. Kaggle reported terminal `COMPLETE`.

## Terminal result

The exact repository checkout passed. The conditional bootstrap executed four
bounded package commands, all returning zero, and restored:

- PyTorch 2.6.0+cu124;
- torchvision 0.21.0+cu124;
- CUDA 12.4 and Triton 3.2.0;
- NumPy 2.0.2;
- xformers 0.0.29.post3;
- torchao 0.16.0;
- Transformers 4.56.2;
- Unsloth and Unsloth Zoo 2026.7.3;
- Accelerate 1.13.0;
- PEFT 0.19.1;
- TRL 0.22.2;
- datasets 4.3.0; and
- bitsandbytes 0.49.2.

The fresh-process gate then confirmed exactly one Tesla P100-PCIE-16GB, an
executable and synchronized CUDA tensor operation, and successful
Unsloth/bitsandbytes imports with Unsloth compilation disabled.

The total wrapper elapsed time was approximately 268.00 seconds (4.47 minutes),
well below the hard subprocess caps.

## Research and artifact boundary

The kernel attached zero datasets and zero models. It did not access private
input, download or load a model, render a prompt, perform inference or
training, create a prediction, or compute a metric.

The private log remains under ignored storage. Its SHA-256 is
`cb1785b833eb0a7f8186ae591f712b9dcc7b9d714783bdfc73071718bb0ec3d6`.
The ignored submitted wrapper SHA-256 is
`ba902928afbd838c1041fe43b44446eaedcf5ee3919081043e373fca21d39005`.
No corpus text or model response was printed or published.

## Decision

The restored P100 runtime engineering gate passes. The single-use issue #135
authorization is consumed, and no retry or second version was submitted.

This does not authorize B1-P1 or B2-P1 evaluation. A future B1-P1 segment must
use the same restored-runtime command before private-input access, preserve the
frozen 511-record contract, save and `fsync` every prediction, stop gracefully
at 9.5 hours, publish no partial metric, and require a new exact-commit owner
GO.
