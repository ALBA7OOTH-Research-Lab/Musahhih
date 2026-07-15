# F1-P1 QLoRA workflow static validation

Date: 2026-07-15

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

Repository validation passed with 87 `unittest` tests and 40 subtests, script
compilation, and `git diff --check`.

## Not executed

No CUDA model load, LoRA attachment, token-length pass over private records,
forward/backward step, GPU-memory measurement, training, checkpoint selection,
generation, or adapter export was executed locally. Therefore this report makes
no claim about Kaggle GPU compatibility, VRAM use, runtime, loss, or correction
quality. Those claims require the deliberate free-Kaggle smoke and later approved
run.
