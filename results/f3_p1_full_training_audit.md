# F3-P1 full-training audit

Recorded: 2026-07-25

Status: complete; one authorized two-epoch training run reached its first
terminal state and selected private `checkpoint-250`.

## Authorization and execution

The owner authorized exactly one private F3-P1 two-epoch Kaggle P100 run at
workflow commit
`6d64f699c04168cc15c045edc86389d5dc81f1bc` in
[issue #90 comment 5072918313](https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/90#issuecomment-5072918313).
Execution was tracked in
[issue #91](https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/91).
Private Kaggle kernel
`univverssal/musahhih-f3-p1-full-6d64f69-r01`, version 1, reached
`COMPLETE`. Submission consumed the authorization; no retry or hot-patch
occurred.

- activation-config SHA-256:
  `774d881d31166c2de47817242cd0c91969ceae19c75e0d19061ac82dabfae713`
- submitted-notebook SHA-256:
  `07889e18a776b3b0b0aeb5178a0a32e10838ce817d2d175cf864d7fd1137ac77`
- prior passing-smoke summary SHA-256:
  `e053f2716beadd1ccf43c292f81d4bc199bba0234e8057c5a7dc5d480fed4944`
- checked-out repository commit:
  `6d64f699c04168cc15c045edc86389d5dc81f1bc`
- hardware gate: exactly one Tesla P100-PCIE-16GB

The full-training session was fresh. It loaded the immutable base-model
revision `316726ca0bd24aa323bfaf86e8a379ee1176d1fe` in four-bit mode and
attached a fresh LoRA. The prior smoke checkpoint was not attached or loaded;
only the aggregate passing-smoke summary was supplied.

## Frozen private inputs

Before model loading, the workflow required and validated:

| View | Records | Provenance | SHA-256 |
| --- | ---: | --- | --- |
| F3-P1 training | 2,000 | 1,000 QALB-2014-L1 + 1,000 Tibyan-corpus | `d16decebe559e9a25da41ef59f63ca95e339972e22b9659dfc763e071fbc1546` |
| Common development | 975 | QALB-2014-L1 development | `adfdeb0c2e5730357226ce4e5156c300679629142ea0576d32dea9ac3050a950` |

No private record was copied into this audit or the public summary.

## Training and checkpoint selection

The terminal private trainer state records 250 of 250 optimizer steps and two
epochs. Both registered epoch checkpoints exist.

| Epoch | Step | Common-development assistant-token loss | Evaluation runtime |
| ---: | ---: | ---: | ---: |
| 1 | 125 | `0.37296223640441895` | 715.5916 seconds |
| 2 | 250 | `0.3441389799118042` | 701.3763 seconds |

The frozen rule selects the lower common-development loss, with differences
within `1e-6` choosing epoch 1. It therefore selected private
`checkpoint-250`.

- checkpoint-selection JSON SHA-256:
  `b4d1deda9b01b82b07abd2a21e999f92e132604ca0c8463830edd8d43dedfa81`
- selected adapter bytes: `131252288`
- selected adapter SHA-256:
  `95bd333caac28e08b40fcafe7bc033f323188e817d7c16ecbe7745b34c1b44dc`
- selected adapter-config SHA-256:
  `917893c00ea8f02f784ce21db4448b774e6a892fede6f484da18606bca884c21`
- public aggregate-summary SHA-256:
  `b5ce341e4faedfa93045763eaaf1dd9837075d7b50c38dbd863d19d60ba80ed4`

Both checkpoints and the selected adapter remain private and Git-ignored.
Development loss is a checkpoint-selection quantity, not final grammatical
correction performance.

## Runtime and reproducibility caveats

Control flow required the frozen CUDA 12.4 P100 core stack before model
loading: PyTorch 2.6.0, torchvision 0.21.0, xformers 0.0.29.post3,
torchao 0.16.0, and NumPy 2.0.2. Transformers 4.56.2, datasets 4.3.0,
and TRL 0.22.2 were explicitly pinned. The selected adapter records PEFT
0.19.1.

Kaggle's output API preserved the checkpoints and selection record but did not
preserve the notebook's printed complete package-version block; the downloaded
notebook log is empty. Exact versions of unpinned higher-level packages in this
terminal run are therefore not durably recoverable. The passing same-commit
F3 smoke used Unsloth 2026.7.5 and emitted the known Gemma 3
`num_items_in_batch` gradient-accumulation warning. These are reproducibility
caveats and must not be silently replaced by inferred version claims.

The earlier private smoke `checkpoint-1` was isolated to its smoke-specific
output. The full-training run created only the required epoch checkpoints in a
fresh training path and did not resume from any checkpoint.

## Research interpretation and safeguards

This run establishes completion of the frozen F3-P1 training and deterministic
development-loss checkpoint selection. It does not establish final correction
quality. No generation, selected-adapter inference, QALB test, Nahw-Passage,
safety-diagnostic execution, F1/F2 rerun, prompt or parser tuning, checkpoint
reselection, synthetic-data change, or XG activation occurred.

The selected adapter, both checkpoints, detailed trainer state, and all private
data remain private. The public
[`f3_p1_full_training_summary.json`](f3_p1_full_training_summary.json) contains
only corpus-text-free aggregate evidence.
