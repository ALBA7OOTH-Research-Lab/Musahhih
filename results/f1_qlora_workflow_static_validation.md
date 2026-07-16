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
xFormers 0.0.29.post3, torchvision 0.21.0, torchao 0.12.0, NumPy 2.0.2, and
the runtime's already-loaded Pillow version
before the first PyTorch import when the assigned GPU is a P100. It immediately executes and
synchronizes a CUDA tensor probe. The separate private archive Dataset restores
the exact registered ZIP name before the existing checksum gate.

Repository validation passed with 93 `unittest` tests, script
compilation, and `git diff --check`.

## Not executed

Kaggle version 5 assigned a P100 and completed private record preparation, but
the pre-amendment PyTorch build failed during model loading because it omitted
`sm_60` kernels. No optimizer step, GPU-memory summary, training, checkpoint
selection, generation, or adapter export ran. The amended dependency stack has
not yet passed the deliberate Kaggle smoke, so this report makes no feasibility,
runtime, loss, or correction-quality claim.
