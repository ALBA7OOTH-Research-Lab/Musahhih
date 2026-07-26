# B1-P1 repaired final-attempt failure audit

## Scope

Issue #114 authorized exactly one new private Kaggle P100 attempt for the frozen
B1-P1 Nahw-Passage final evaluation at repaired executable commit
`f8c7ffd74993785f118bb32e0145295b31c5048d`.

The private kernel was
[`alba7oothresearchlab/musahhih-b1-final-repaired-f8c7ffd-r02`](https://www.kaggle.com/code/alba7oothresearchlab/musahhih-b1-final-repaired-f8c7ffd-r02),
version 1. Kaggle reported terminal `ERROR`.

## Failure

During the initial pinned PyTorch installation, pip made five attempts to reach
`https://download.pytorch.org/whl/cu124/torch/`. Every attempt failed with a
temporary DNS name-resolution error. At approximately 204 seconds, pip reported
no available `torch==2.6.0` distribution and the wrapper preserved
`CalledProcessError`.

This occurred before:

- repository clone or repaired-commit checkout;
- the issue #112 PyTorch CUDA/P100 preflight;
- private-input discovery or record access;
- model or processor loading;
- prompt rendering or response generation;
- prediction, progress, or summary creation; and
- metric computation.

The only downloaded private artifact was the kernel log, retained under the
ignored execution directory. Its SHA-256 is
`bb94cfd2991bb6e1819f16e7b4c71a524667b79ed04c2ba19446f5fd87a14052`.
No corpus text or model response was printed or published.

## Decision

This is a pre-research network failure, not a B1-P1 result and not evidence
about the GPU-preflight repair or model quality. The single-use authorization
was consumed. No kernel edit, second version, retry, resubmission, hot-patch,
B2-P1 run, or continuation was launched.

A future attempt requires a fresh exact-commit, scope-specific owner GO. It must
preserve the first terminal state and may not silently reuse this authorization.
