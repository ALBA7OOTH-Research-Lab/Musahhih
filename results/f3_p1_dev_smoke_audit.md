# F3-P1 selected-adapter private development-smoke audit

Recorded: 2026-07-25

Status: passed. One authorized private Kaggle P100 run reloaded the immutable
F3-P1 `checkpoint-250` and completed the frozen deterministic 25-record
QALB-2014 L1 development smoke. No output was empty and the unchanged
conservative parser raised no warnings. This is a pipeline-readiness result,
not a published development score or final-test result.

## Execution identity

- authorization: [issue #93 comment](https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/93#issuecomment-5077818701)
- terminal run: [private Kaggle version 1](https://www.kaggle.com/code/univverssal/musahhih-f3-p1-dev-smoke-2982a2e-r01)
- terminal status: `COMPLETE`
- exact workflow commit:
  `2982a2ed62f0d59e51eacbbddb02a03994c73e4b`
- executed-notebook SHA-256:
  `89d58bd8983cf2232f8ca2d0b4f7165df6fb93f6f552cf4aeddce565fb12720b`
- private activation-config SHA-256:
  `08030eed5842a323d17d913e400b22fd12432e5928dc8d876cc52684dbefc7ae`
- downloaded text-free public-summary SHA-256:
  `f0e2f24d201aa241f64acbab147561316f4b443fa08f0f732f5356c3fcc8c3c7`
- GPU: Tesla P100-PCIE-16GB

## Frozen checkpoint and matched records

- base model: `unsloth/gemma-3-4b-it-unsloth-bnb-4bit`
- model revision:
  `316726ca0bd24aa323bfaf86e8a379ee1176d1fe`
- selected checkpoint: `checkpoint-250`, loaded unmerged in 4-bit mode
- adapter-model SHA-256:
  `95bd333caac28e08b40fcafe7bc033f323188e817d7c16ecbe7745b34c1b44dc`
- adapter-config SHA-256:
  `917893c00ea8f02f784ce21db4448b774e6a892fede6f484da18606bca884c21`
- checkpoint-selection SHA-256:
  `b4d1deda9b01b82b07abd2a21e999f92e132604ca0c8463830edd8d43dedfa81`
- development source: frozen 975-record QALB-2014 L1 development view
- selected records: the exact same 25 deterministic records used for F2-P1
- selected-record-ID SHA-256:
  `7cf5e1fbced3f28551053abb08d7747ae7eedcd70ca6900be2ea9ce4e58c4527`
- maximum selected input length: 194 tokens; no record was truncated

## Inference and private artifacts

Decoding used seed 3407, `do_sample=False`, no temperature argument, and
`max_new_tokens=256`. All 25 expected rows completed. The raw and parsed
responses, record IDs, exact-match flags, prompt/gold hashes, private summary,
and private development metric remain private. The private prediction JSONL
SHA-256 is
`d76a4f7dd1dbf760caad40bd01fd00ca65afa7f02d33176c0df7d6e9cda39198`.

Local corpus-text-free verification counted exactly 25 prediction rows and
confirmed that the byte hash matches the public summary. The prediction rows
and private summary were not printed or parsed, and the private development
metric was not read or published.

The public aggregate records zero empty outputs and no parser warnings. It does
not contain prompt text, gold corrections, model responses, parsed responses,
record IDs, or the private development exact-match count.

## Runtime

The validated stack was Python 3.12.13, PyTorch 2.6.0+cu124, CUDA 12.4,
Transformers 4.56.2, Unsloth 2026.7.5, Accelerate 1.13.0, PEFT 0.19.1, TRL
0.22.2, datasets 4.3.0, bitsandbytes 0.50.0, torchvision 0.21.0+cu124,
xformers 0.0.29.post3, torchao 0.16.0, and NumPy 2.0.2. The conditional heavy
stack installation ran once for 169.398 seconds.

## Research safeguards and decision

The run did not train, merge or change the adapter, reselect a checkpoint, tune
the prompt or parser, access QALB test or Nahw-Passage, execute F1/F2 or safety
diagnostics, or activate XG. Its public summary contains no corpus text. The
one-run authorization is consumed and no retry was performed.

Accept the F3-P1 selected adapter as technically reloadable. This smoke does
not establish held-out correction quality, publish a private development
metric, or authorize final-test evaluation, another development run, safety
diagnostics, training, F1/F2, or XG.
