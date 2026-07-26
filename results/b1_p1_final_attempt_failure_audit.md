# B1-P1 final-attempt failure audit

## Scope

Issue #109 authorized exactly one private Kaggle P100 segment for the frozen
B1-P1 Nahw-Passage final evaluation at executable commit
`16b4ca3dec6e757b41e233b22bc16cc6a57be4dd`.

The private kernel was
[`alba7oothresearchlab/musahhih-b1-final-timeout-safe-16b4ca3-r01`](https://www.kaggle.com/code/alba7oothresearchlab/musahhih-b1-final-timeout-safe-16b4ca3-r01),
version 1. Kaggle reported terminal `ERROR`.

## Failure

The wrapper failed at approximately 1.07 seconds while invoking the external
`nvidia-smi` command. The executable was unavailable, so the fail-closed P100
runtime gate stopped the process with `FileNotFoundError`.

A follow-up metadata audit found:

- Kaggle stored `enable_gpu: true`;
- Kaggle stored the normalized machine shape `Gpu`;
- the account reported 30.00 GPU-hours remaining; and
- the official Kaggle CLI documentation lists `NvidiaTeslaP100` as a valid
  accelerator identifier.

The evidence therefore does not show an account-eligibility failure or prove
that no CUDA device was assigned. The wrapper stopped before measuring
`torch.cuda.is_available()` or the CUDA device name. The correct diagnosis is a
brittle wrapper preflight that treated the presence of one external executable
as the GPU test.

The failure occurred before:

- repository clone or approved-commit checkout;
- private-input discovery or record access;
- model or processor loading;
- prompt rendering or response generation;
- prediction, progress, or summary creation; and
- metric computation.

The only downloaded private artifact was the kernel log, retained under the
ignored execution directory. Its SHA-256 is
`26c9e08ae4b83bbd2ba8f94708f2f4c5f2d0bcc442bb9dfaaf02004ad8a18f26`.
No corpus text or model response was printed or published.

## Decision

This is an infrastructure failure, not a B1-P1 result and not evidence about
model quality. The single-use authorization was consumed by the submission.
No edit, new kernel version, retry, resubmission, hot-patch, B2-P1 run, or
continuation was launched.

Before any future B1-P1 attempt, replace the external-command assumption with a
reviewed, fail-closed CUDA/device check that does not read private inputs or load
the model. A future submission still requires a fresh exact-commit,
scope-specific owner GO.

Issue #112 implements that repair with a reusable PyTorch CUDA/P100 preflight.
Its implementation and synthetic validation do not authorize another attempt.
