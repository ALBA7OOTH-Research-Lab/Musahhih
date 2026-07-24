# F3-P1 longest-record P100 smoke audit

Recorded: 2026-07-24

Status: complete; engineering memory gate passed

## Authorized scope

The owner authorized exactly one private F3-P1 longest-record, one-step P100
smoke at workflow commit
`6d64f699c04168cc15c045edc86389d5dc81f1bc`. The permanent authorization is
[issue #85 comment 5070956088](https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/85#issuecomment-5070956088),
and execution is tracked in
[issue #88](https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/88).
The authorization was consumed by one submission and does not authorize a
retry or full training.

## Terminal execution

- Private Kaggle kernel:
  `univverssal/musahhih-f3-p1-smoke-6d64f69-r01`, version 1
- Terminal state: `COMPLETE`
- Hardware: Tesla P100-PCIE-16GB
- Workflow commit:
  `6d64f699c04168cc15c045edc86389d5dc81f1bc`
- Activation-config SHA-256:
  `a292369cd92b388f5922151a0a266399b05253a849c18dabaef4cdeb0b1052a4`
- Submitted-notebook SHA-256:
  `07889e18a776b3b0b0aeb5178a0a32e10838ce817d2d175cf864d7fd1137ac77`
- Aggregate-summary SHA-256:
  `e053f2716beadd1ccf43c292f81d4bc199bba0234e8057c5a7dc5d480fed4944`

The repository gate detached to the exact approved workflow commit. The run
validated 2,000 F3-P1 training records with the registered SHA-256
`d16decebe559e9a25da41ef59f63ca95e339972e22b9659dfc763e071fbc1546`
and aggregate provenance of 1,000 QALB-2014-L1 plus 1,000 Tibyan-corpus
records. It also validated 975 common-development records with registered
SHA-256
`adfdeb0c2e5730357226ce4e5156c300679629142ea0576d32dea9ac3050a950`.
No corpus text was copied into the public audit.

## Engineering result

All 2,000 formatted F3 records passed the frozen 1,024-token guard. The
minimum was 84 tokens, the maximum was 668, and the selected longest record
was index 1097. The frozen Gemma 3 4B 4-bit base and fresh LoRA loaded, and
exactly one optimizer step ran.

- Total GPU memory: 17,059,545,088 bytes
- Peak reserved memory: 7,667,187,712 bytes
- Measured headroom: 9,392,357,376 bytes
- Required headroom: 1,073,741,824 bytes
- Gate result: `passed=true`

The runtime used Python 3.12.13, PyTorch 2.6.0+cu124, CUDA 12.4,
Transformers 4.56.2, Unsloth 2026.7.5, Accelerate 1.13.0, PEFT 0.19.1,
TRL 0.22.2, datasets 4.3.0, and bitsandbytes 0.49.2. The conditional base-stack
downgrade ran once in 173.096 seconds and the complete frozen P100 stack
validated before model loading. Unsloth selected float32 for Gemma 3 and
repeated its known `num_items_in_batch` gradient-accumulation warning.

## Artifact-hygiene caveat

Although the notebook did not deliberately export or select an adapter, the
Trainer's automatic save behavior wrote a private temporary `checkpoint-1`
under the smoke output after the single step. It includes an adapter snapshot
and optimizer state. The checkpoint remains private, was not merged, selected,
evaluated, or committed, and must not be treated as an F3 model artifact.
The first terminal state is preserved rather than altered. Before any later
smoke workflow is reused, automatic checkpoint saving should be explicitly
disabled for smoke stages.

## Research interpretation

This result establishes only that the frozen F3-P1 mixed-data workflow can
validate its inputs, load the model, and complete one worst-case optimizer step
within the P100 memory gate. It is not a correction-quality result. Full
training remained disabled; no inference, checkpoint selection, QALB test,
Nahw-Passage, safety-diagnostic rerun, F2 rerun, or XG execution occurred.

A separate reviewed GO/NO-GO decision is required before one F3-P1 two-epoch
training run. That decision must explicitly acknowledge the private temporary
checkpoint side effect and specify whether the full-training execution should
reuse the current workflow commit or first receive a narrow artifact-hygiene
repair.
