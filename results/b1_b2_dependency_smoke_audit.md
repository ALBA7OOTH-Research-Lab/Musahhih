# B1-P1/B2-P1 dependency smoke audit

Date: 2026-07-28

Issue: https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/119

Owner GO:
https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/119#issuecomment-5096605001

## Outcome

The single authorized private dependency smoke completed on Kaggle account
`thgh15`. Public-PyPI installation returned zero, Unsloth and bitsandbytes both
imported, and the exact base runtime was unchanged:

- PyTorch 2.10.0+cu128;
- torchvision 0.25.0+cu128;
- NumPy 2.0.2;
- CUDA 12.8; and
- one Tesla P100.

The smoke nevertheless reported `ready: false` because the global
`python -m pip check` command returned one. Its output was intentionally
captured but only hashed, so this run cannot establish whether the conflict is
in the B1/B2 inference layer or an unrelated preinstalled Kaggle package. Do
not start final inference from this result.

## Installed inference layer

- Unsloth 2026.7.2
- unsloth_zoo 2026.7.2
- bitsandbytes 0.49.2
- Transformers 4.56.2
- TRL 0.23.0
- xformers 0.0.34
- Accelerate 1.13.0
- PEFT 0.19.1

## Identity and safeguards

- executable commit:
  `3b28f99f4bbfe889ffaf56b1063ebfdc23a6ae72`
- submitted script SHA-256:
  `3ce026f1abedee1c83d023ba19354daeb66f587d25f2c082d9e884e029a1bc9c`
- private kernel:
  `thgh15/musahhih-b1-b2-dependency-smoke-3b28f99-r01`, version 1
- first terminal state: `COMPLETE`
- private log SHA-256:
  `00fc32a62347755b0dca0656c2f2e4588c33a0dd28b91a47f60089396f943d9f`
- install stdout/stderr were not published; their hashes are preserved in the
  private aggregate report
- zero datasets, models, kernels, competitions, or prior outputs were attached
- no private input, model load, inference, training, or metric occurred

The authorization is consumed. A diagnostic repair must expose only sanitized
package-conflict lines and requires a fresh GO. B1-P1 final inference remains
unauthorized until that conflict is classified.
