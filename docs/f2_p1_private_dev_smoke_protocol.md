# F2-P1 selected-adapter private development smoke

Status: frozen for issue #82 before inference.

## Purpose

Verify that the selected private F2-P1 adapter can be reloaded, generate
deterministic corrections, pass the existing conservative parser, and preserve
private artifacts. This is a technical development gate, not checkpoint
selection or final evaluation.

## Fixed inputs

- model: `unsloth/gemma-3-4b-it-unsloth-bnb-4bit`
- model revision: `316726ca0bd24aa323bfaf86e8a379ee1176d1fe`
- selected checkpoint: private `checkpoint-125`
- selected adapter-model SHA-256:
  `935fdf02c95189934e40629f877d8692d325ef22895cbaa03fdb7390b0cd7b3e`
- selected adapter-config SHA-256:
  `b07ab34155647961ea1de8fbfff0db8e17d00229da01f2b941a15a78499da986`
- checkpoint-selection SHA-256:
  `39edee5e31d79c791a4ab0b14b7b85b838e28bcc302d9e552f168a03ac870e1b`
- development view: the frozen 975-record QALB-2014 L1 development file,
  SHA-256 `adfdeb0c2e5730357226ce4e5156c300679629142ea0576d32dea9ac3050a950`
- prompt: the unchanged F1/F2 training prompt, already embedded in each
  validated private record
- parser: `scripts.nahw_baseline_utils.parse_model_response`, unchanged

The notebook must verify all hashes and the selected checkpoint before model
loading. It must not merge the adapter or construct a trainer or optimizer.

## Frozen record selection

Select exactly 25 records without inspecting source text, gold corrections, or
model output. For every development record, compute SHA-256 over:

```text
F2-P1-dev-smoke|3407|<record_id>
```

Sort ascending by that digest and take the first 25. Record the SHA-256 of the
selected record IDs, in execution order with one UTF-8 ID per line.

## Frozen inference

- one free private Kaggle NVIDIA P100 runtime
- 4-bit base-model loading through Unsloth
- selected LoRA checkpoint loaded unmerged
- maximum sequence length: 1,024
- `do_sample=False`
- no temperature argument
- `max_new_tokens=256`
- batch size: one record
- seed: 3,407

Do not change these settings after inspecting any response. Preserve warnings
from the existing parser; do not normalize Arabic letters, hamza forms,
diacritics, punctuation, or spelling.

## Private and public artifacts

The private run must save one JSONL row per record containing the record ID,
hashes of the prompt and gold correction, raw response, parsed response,
parser warnings, and exact-match flag. It may save a private summary containing
the development exact-match count. Neither file may enter Git, Notion, or a
public Kaggle asset.

The public summary may contain only aggregate runtime metadata, fixed model and
checkpoint identities, selected-record and prediction-file hashes, parser
warning counts, empty-output count, execution status, and explicit safety
flags. Do not publish the private development exact-match count or any corpus
text, prompt, gold correction, raw response, or parsed response.

## Execution gate

The committed notebook is disabled by default. The one authorized attempt may
start only after:

1. issue #82's implementation PR passes CI and merges;
2. a private `f2_dev_smoke_execution_config.json` names that exact merge commit;
3. the config cites issue #82's authorization comment and contains the exact
   confirmation `RUN_F2_P1_PRIVATE_DEV_SMOKE_25`; and
4. the private QALB development records and prior training-kernel output are
   attached to a private Kaggle notebook.

Preserve the first terminal state. A completed or result-bearing failed run
consumes the authorization. Do not retry without fresh owner authorization.

## Prohibited uses

Do not train, reselect a checkpoint, tune the prompt or parser, run more than 25
development records, access QALB test or Nahw-Passage, run F3 or safety
diagnostics, activate XG, or publish private records, responses, checkpoints,
or adapter bytes. Smoke results cannot change the F2-P1 checkpoint.

## Passing gate

The gate passes only if all 25 deterministic records produce privately saved
rows, the public summary is text-free, no output is empty, required hashes and
runtime metadata are present, and all final-test/training flags remain false.
Parser warnings are recorded for review but do not by themselves fail the
technical gate. Passing establishes pipeline readiness only, not correction
quality.
