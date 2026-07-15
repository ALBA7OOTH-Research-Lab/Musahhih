# B1-P1/B2-P1 QALB-development GPU validation

Date: 2026-07-11

GitHub issue: https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/14

Fix pull request: https://github.com/ALBA7OOTH-Research-Lab/Musahhih/pull/15

## Outcome

Both frozen protocols completed all 25 private QALB-2014 L1 development
records on a free Colab Tesla T4. These are technical development-gate results,
not final Nahw-Passage results.

| Protocol and run | Exact match | Empty/invalid | Multi-token or suspicious |
| --- | ---: | ---: | ---: |
| `B1-P1__gemma3-4b-it__qalb14-dev__s3407__r03` | 7/25 (28%) | 0 | 1 |
| `B2-P1__gemma3-4b-it__qalb14-dev__s3407__r01` | 13/25 (52%) | 0 | 0 |

B1 attempts `r01` and `r02` are preserved privately as invalid zero-record
runs. Their failure exposed an implementation defect: the runner loaded an
Unsloth pre-quantized checkpoint through plain Transformers, which did not
restore required bitsandbytes quantization metadata. PR #15 changes the backend
to Unsloth `FastModel`. A pinned 4-bit smoke generation then succeeded before
the complete runs above.

## Frozen configuration

- Model: `unsloth/gemma-3-4b-it-unsloth-bnb-4bit`
- Revision: `316726ca0bd24aa323bfaf86e8a379ee1176d1fe`
- Seed: 3407
- Greedy decoding; sampling disabled; maximum 32 new tokens
- B1 uses the frozen five-example private bundle; B2 uses no demonstrations
- Input SHA-256: `e6c43baef47e2180081debabddff4f5bca463c0769335fcbc5f4166f86ea093c`
- Public protocol SHA-256: `5c0bff3ebfbf5a9d8a300fa881237c7faba1913d28add296c420ce4cede7746c`
- B1 private bundle SHA-256: `760674f0d6cc85c48b2be18d175b87e2025cd3d01fde31a6e25afaa08f9fc11a`
- B1 aggregate prompt SHA-256: `e245ef230e9d66e66145b5bb2a627617bede3b4d5523e3528a0562ae00b6079b`
- B2 aggregate prompt SHA-256: `fe77b96bb24ddfb26c564a566502d0691fb0cd502bd425b67fd6589b5169b1ef`

Runtime: Python 3.12.13, PyTorch 2.11.0+cu128, CUDA 12.8,
Transformers 4.56.2, Unsloth 2026.7.2, and bitsandbytes 0.49.2 on a Tesla T4
with 14.56 GiB total GPU memory.

## Research safeguards

- QALB test data was not used.
- Nahw-Passage was not opened or run during this validation.
- No training, adapter attachment, prompt optimization, or checkpoint selection
  occurred.
- Private QALB text, raw responses, predictions, and licensed data remain in
  ignored private Colab output paths and are not included in this report.
- The failed runs were not overwritten and no score was inferred from them.

## Gate decision

The B1-P1 and B2-P1 technical gate passes. After PR #15 is merged and the
private artifacts are exported from the temporary Colab runtime, the next
research action is the single preregistered B1-P1 and B2-P1 Nahw-Passage run.
The final test must not be used to revise prompts or select between protocols.
