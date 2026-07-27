# B1-P1/B2-P1 Kaggle runtime probe audit

Date: 2026-07-27

GitHub issue: https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/116

Owner GO:
https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/116#issuecomment-5096508111

## Outcome

The single authorized private runtime probe completed on the phone-verified
Kaggle account `thgh15`. The assigned runtime had exactly one
`Tesla P100-PCIE-16GB`, CUDA was available through PyTorch, and the probe
completed without repository checkout, package installation, private-input
access, model loading, inference, or a metric.

The preinstalled runtime is not yet ready for the frozen B1/B2 inference
backend because Unsloth and bitsandbytes are absent. This is an expected
diagnostic outcome, not a failed kernel.

## Execution identity

- exact executable commit:
  `9572bad1c77b30cf8edef58d1619a94c869c835e`
- probe script SHA-256:
  `bcfd05caa0b7c44f2eca3ed5604152d552701b39dfcbcd7b9edb0bc8d09528d4`
- private kernel:
  `thgh15/musahhih-b1-b2-runtime-probe-9572bad-r01`
- kernel version: 1
- first terminal state: `COMPLETE`
- private downloaded log SHA-256:
  `a957499a3a31644cddf756d84ca15ccd348dae232ea916a975ddb0ecf85b0e6d`

The submitted script was byte-identical to the approved Git object. The kernel
was private, requested a P100, disabled internet, and attached zero datasets,
models, kernels, competitions, or prior outputs.

## Aggregate runtime

| Field | Observed value |
| --- | --- |
| Python | 3.12.13 |
| PyTorch | 2.10.0+cu128 |
| CUDA runtime reported by PyTorch | 12.8 |
| CUDA available | yes |
| visible CUDA devices | 1 |
| GPU | Tesla P100-PCIE-16GB |
| torchvision | 0.25.0+cu128 |
| Transformers | 5.0.0 |
| Accelerate | 1.13.0 |
| PEFT | 0.19.1 |
| NumPy | 2.0.2 |
| Unsloth | absent |
| bitsandbytes | absent |
| xformers | absent |
| TRL | absent |

The probe's aggregate flags confirm:

- network access attempted: false;
- private input accessed: false; and
- model loaded: false.

## Decision

The account and base GPU runtime pass: CUDA, the P100 assignment, and the
preinstalled PyTorch stack are usable. A future bootstrap must preserve that
working PyTorch installation and add only the missing, reviewed inference
layer. It must not repeat issue #114's forced PyTorch reinstall from
`download.pytorch.org`.

Before another B1-P1 attempt, implement and review a dependency-only bootstrap,
then validate it with a no-private, no-model import smoke under a fresh
single-use GO. The final B1-P1 segment requires a separate later GO. This
probe's authorization is consumed.
