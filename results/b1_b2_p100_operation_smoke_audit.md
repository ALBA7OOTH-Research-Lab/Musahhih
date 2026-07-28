# B1/B2 repaired P100-operation smoke audit

## Scope

Issue #130 authorized exactly one private, no-input/no-model Kaggle smoke of
the executable P100 guard at code commit
`cb65e2f3143179d34034b661116220a011ffdddd`.

The private kernel was
[`thgh15/musahhih-b1-b2-p100-operation-cb65e2f-r01`](https://www.kaggle.com/code/thgh15/musahhih-b1-b2-p100-operation-cb65e2f-r01),
version 1. Kaggle reported terminal `ERROR`.

## Terminal evidence

The exact repository gate passed. PyTorch then observed one Tesla
P100-PCIE-16GB with CUDA capability `sm_60`. The installed PyTorch build
reported compiled support beginning at `sm_70`, so the newly required CUDA
tensor operation could not execute.

The preflight failed closed with:
`B1/B2 final execution requires an executable P100 CUDA operation`.
The aggregate preflight error occurred at approximately 8.58 seconds, followed
by the wrapper's terminal subprocess traceback at approximately 10.61 seconds.

This is the intended behavior of issue #127's repaired guard. It converts the
previous false-positive device-discovery result into a fast, explicit runtime
rejection.

## Research and artifact boundary

The kernel attached no dataset or model. It did not access private input,
download or load a model, render a prompt, perform inference or training,
create a prediction, or compute a metric.

The private log remains under ignored storage. Its SHA-256 is
`034e0bb7d4dac978bf064fb01fe65eb547be0319d7b5a6cf13abefe1ba960bbb`.
The ignored submitted wrapper SHA-256 is
`11cf4b2b706170488231692576c7bfc819d8df83bfc0d1a661f40a3065debfd6`.
No corpus text or model response was printed or published.

## Decision

The smoke is a successful fail-closed engineering result, not a passing GPU
gate and not a B1/B2 research result. Its single-use authorization is consumed.
No edit, second version, retry, resubmission, hot-patch, or evaluation was
launched.

A future attempt requires a reviewed P100-compatible PyTorch/inference-stack
strategy or a separately reviewed accelerator change. That repair must pass a
new no-input/no-model executable smoke under a fresh GO before B1-P1 inference
can be considered.
