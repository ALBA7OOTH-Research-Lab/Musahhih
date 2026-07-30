# F2/F3 Nautilus A100 preflight compiler failure audit

## Scope

Issue #159 authorized exactly one second-replacement no-input/no-model A100
preflight at merged commit `72d6effbc7cff5a1c2acc63f63cb1795d48ea502`. The
authorization comment is:

`https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/159#issuecomment-5132491364`

The generated one-Job manifest had SHA-256
`ad4cd86a078f363d22c1f9928680759c9145239b95cf8e351d13ec571bf2479a`.

## Terminal outcome

The single Job `aiea-interns/musahhih-f2-f3-preflight` reached terminal
`Failed` with zero completions after approximately 2 minutes 32 seconds on
`sdsmt.gp-argo.greatplains.net`. It passed the immutable checkout, Git-free
detached-HEAD attestation, exact A100 identity and compute-capability gate, and
synchronized CUDA tensor operation.

The subsequent full runtime import gate failed when importing bitsandbytes
initialized Triton. Triton attempted to build its CUDA helper, but the official
minimal PyTorch `runtime` image had no C compiler and raised
`Failed to find C compiler`.

The manifest had no private volume or input path. No dataset, model loading,
training, inference, prediction, or metric occurred. The terminal aggregate
failure was recorded on issue #159, the failed Job was deleted after evidence
capture, no replacement was created, and the authorization is consumed.

## Reviewed repair

Issue #161 retains PyTorch 2.6.0, CUDA 12.4, cuDNN 9, FP16, the frozen package
versions, and all experiment settings. It changes only the official base image
variant from `runtime` to the matching compiler-capable `devel` image, pinned
to Docker Hub's published Linux/AMD64 digest:

`pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel@sha256:0cf3402e946b7c384ba943ee05c90b4c5a4a05227923921f2b0918c011cfaf56`

The authoritative image entry is:
`https://hub.docker.com/layers/pytorch/pytorch/2.6.0-cuda12.4-cudnn9-devel/images/sha256-0cf3402e946b7c384ba943ee05c90b4c5a4a05227923921f2b0918c011cfaf56`.

The runner now requires a discoverable C compiler before the unchanged
bitsandbytes/Unsloth import gate. Regression coverage checks both a present
compiler and a fail-closed compiler-free runtime.

This repository-only repair authorizes no cluster object or GPU execution. A
further no-input/no-model preflight requires review, merge, and a fresh
exact-commit owner GO. Paired training remains unauthorized.
