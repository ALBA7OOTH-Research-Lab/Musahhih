# F1-P1 QLoRA workflow static validation

Date: 2026-07-16

Issue: https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/32

## Validated locally

- `notebooks/02_f1_natural_qlora.ipynb` parses as notebook format 4.
- All 22 cells are ordered and every code cell parses as Python.
- Code cells have no stored execution counts or outputs.
- GPU smoke, full training, and private development smoke flags default to
  `False`.
- The full-training gate requires both the exact confirmation string and a
  passing text-free memory summary with at least 1 GiB headroom.
- A runtime that performs the optimizer smoke step is marked contaminated and
  cannot run F1-P1; the user must restart and load the prior smoke summary.
- Private JSONL validation returns only filename, hashes, counts, and maximum
  serialized length—not prompts or completions.
- The epoch checkpoint rule uses development assistant-token loss and resolves a
  tie within `1e-6` in favor of epoch 1.
- QALB test and Nahw-Passage are not workflow inputs.

The P100 compatibility amendment pins PyTorch 2.6.0/CUDA 12.4,
xFormers 0.0.29.post3, torchvision 0.21.0, torchao 0.16.0, NumPy 2.0.2, and
the runtime's already-loaded Pillow version
before the first PyTorch import when the assigned GPU is a P100. It immediately executes and
synchronizes a CUDA tensor probe. The separate private archive Dataset restores
the exact registered ZIP name before the existing checksum gate.

Gemma 3 response-only masking now runs through Unsloth's vision-aware data
collator, with completion-only loss and the frozen user/model turn markers.
The workflow checks the collated labels directly before any training step;
private text is not printed. This change follows the failure observed after
successful model load and LoRA attachment in Kaggle smoke run v9.

Kaggle smoke run v10 reached the one-step trainer but TorchInductor attempted
to use Triton, which does not support the P100's CUDA capability 6.0. The P100
bootstrap now sets Unsloth's compile-disable switch before any Unsloth import
and records the resolved eager-mode state. Other GPU paths retain their normal
Unsloth compilation behavior.

Repository validation passed with 94 `unittest` tests, script
compilation, and `git diff --check`.

## Not executed

Kaggle kernel version 11 completed the deliberate one-step optimizer smoke on
a Tesla P100. Peak reserved memory was 6,266,290,176 bytes and measured
headroom was 10,793,254,912 bytes, so the frozen 1 GiB gate passed. The exact
text-free artifact is `results/f1_p1_gpu_smoke_summary.json`.

The complete two-epoch pilot, checkpoint selection, private development
generation, adapter export, and every final-test evaluation were not executed.
No correction-quality score or full-training feasibility claim is made here.
