# F2-P1 selected-adapter private development-smoke audit

Recorded: 2026-07-20

Status: passed. One authorized private Kaggle P100 run reloaded the immutable
F2-P1 `checkpoint-125` and completed the frozen deterministic 25-record
QALB-2014 L1 development smoke. No output was empty and the unchanged
conservative parser raised no warnings. This is a pipeline-readiness result,
not a published development score or final-test result.

## Execution identity

- authorization: [issue #82 comment](https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/82#issuecomment-5021082958)
- terminal run: [private Kaggle version 1](https://www.kaggle.com/code/univverssal/musahhih-f2-p1-dev-smoke-d176c6f-r01)
- terminal status: `COMPLETE`
- exact workflow commit:
  `d176c6fa4bacc3ea05419484e2316e9e6201a9bd`
- executed-notebook SHA-256:
  `579f0e0db0f6c26c5df47dd70405a7d79a0935afaa59fd126a3bc80d059fb791`
- private activation-config SHA-256:
  `8fb986bcb13e468619fbc9bd79eb66e489a820eb752025d49346b52bc69d0e66`
- downloaded text-free public-summary SHA-256:
  `50b5ccc47c12e25ebd3744b61cf57eb69e510c7394084e6eaa1c2ce5fbf59647`
- GPU: Tesla P100-PCIE-16GB

## Frozen checkpoint and records

- base model: `unsloth/gemma-3-4b-it-unsloth-bnb-4bit`
- model revision:
  `316726ca0bd24aa323bfaf86e8a379ee1176d1fe`
- selected checkpoint: `checkpoint-125`, loaded unmerged in 4-bit mode
- adapter-model SHA-256:
  `935fdf02c95189934e40629f877d8692d325ef22895cbaa03fdb7390b0cd7b3e`
- adapter-config SHA-256:
  `b07ab34155647961ea1de8fbfff0db8e17d00229da01f2b941a15a78499da986`
- checkpoint-selection SHA-256:
  `39edee5e31d79c791a4ab0b14b7b85b838e28bcc302d9e552f168a03ac870e1b`
- development source: frozen 975-record QALB-2014 L1 development view
- selected records: 25, chosen by the pre-run label-independent identity hash
- selected-record-ID SHA-256:
  `7cf5e1fbced3f28551053abb08d7747ae7eedcd70ca6900be2ea9ce4e58c4527`
- maximum selected input length: 194 tokens; no record was truncated

## Inference and private artifacts

Decoding used seed 3407, `do_sample=False`, no temperature argument, and
`max_new_tokens=256`. All 25 expected rows completed. The raw and parsed
responses, record IDs, exact-match flags, and prompt/gold hashes remain in the
private prediction JSONL, whose SHA-256 is
`5f29061b4510ec678b138fdaf324629ea910ad4682729ffc2544f31d76d31f70`.

Local private verification found exactly 25 valid JSONL rows and 25 unique
record IDs, all required private fields, and a byte hash matching the public
summary. The private summary retained its exact-match count with publication
disabled. Neither the count nor any record-level content was inspected for
tuning or copied into this repository or Notion.

The public aggregate records zero empty outputs and no parser warnings. It does
not contain prompt text, gold corrections, model responses, parsed responses,
record IDs, or the private development exact-match count.

## Runtime and warnings

The final validated stack was Python 3.12.13, PyTorch 2.6.0+cu124, CUDA 12.4,
Transformers 4.56.2, Unsloth 2026.7.3, Accelerate 1.13.0, PEFT 0.19.1, TRL
0.22.2, datasets 4.3.0, bitsandbytes 0.49.2, torchvision 0.21.0+cu124,
xformers 0.0.29.post3, torchao 0.16.0, and NumPy 2.0.2. The conditional heavy
stack installation ran once for 194.386 seconds.

Two non-fatal warnings remain reproducibility caveats. The notebook imported
Transformers before Unsloth, so Unsloth warned that its optimizations might be
reduced. Unsloth also reported that float16 would not work for this Gemma 3
path and selected float32. The terminal run nevertheless completed all 25
records without an empty output or parser warning. No retry was performed.

## Research safeguards and decision

The run did not train, merge or change the adapter, reselect a checkpoint, tune
the prompt or parser, access QALB test or Nahw-Passage, execute F3 or safety
diagnostics, or activate XG. Its summary contains no corpus text. The one-run
authorization is consumed.

Accept the F2-P1 selected adapter as technically reloadable and ready for a
separately governed research decision. This smoke does not establish held-out
correction quality and does not authorize final-test evaluation, another
development run, F3 training, or any other GPU execution.
