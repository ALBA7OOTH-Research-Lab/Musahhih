# F2/F3 Nautilus A100 preflight Git dependency failure audit

## Scope

Issue #157 authorized exactly one replacement no-input/no-model A100 preflight
at merged commit `45fb80f0208bd8a504ef9bb66a9207cb7e09199e`. The authorization
comment is:

`https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/157#issuecomment-5132230550`

The generated one-Job manifest had SHA-256
`2c9a617599d9ad6dc123a8d5d4a61ffc4950eff2722a6c36e8d268fbbd65c0fe`.

## Terminal outcome

The single Job `aiea-interns/musahhih-f2-f3-preflight` reached terminal
`Failed` with zero completions after approximately 2 minutes 5 seconds. It
successfully pulled the corrected checkout image, completed the immutable
exact-commit checkout, pulled the pinned PyTorch runtime, and installed the
frozen dependency layer.

The runner then called `git rev-parse HEAD` before CUDA validation. The pinned
PyTorch runtime does not include a `git` executable, so Python raised
`FileNotFoundError`. The CUDA operation was never attempted. No private volume,
dataset, model, training, inference, prediction, or metric was present or
accessed.

The terminal aggregate failure was recorded on issue #157. The failed Job was
deleted after evidence capture. No replacement Job was created and no retry
occurred. The authorization is consumed.

## Reviewed repair

Issue #159 removes the redundant main-runtime executable dependency. The init
container still performs the immutable clone, detached checkout, exact commit
comparison, and clean-worktree check with pinned Git. The main runner now reads
the resulting detached `.git/HEAD` as ASCII and requires exactly 40 lowercase
hexadecimal characters before comparing it with the approved commit.

Regression coverage verifies success with an empty `PATH` and failure for a
symbolic HEAD, malformed or uppercase commit IDs, and missing HEAD metadata.

This repository-only repair authorizes no cluster object or GPU execution. A
further no-input/no-model preflight requires review, merge, and a fresh
exact-commit owner GO. Paired training remains unauthorized.
