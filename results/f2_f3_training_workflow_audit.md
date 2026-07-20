# F2/F3 guarded training-workflow audit

Recorded: 2026-07-20

Status: private record assembly, the guarded workflow, the longest-record
smoke, one F2-P1 two-epoch training run, and one selected-adapter 25-record
private development smoke are complete. The frozen common-development
selection rule chose epoch 1 (`checkpoint-125`), and the later development
smoke reloaded it without changing selection. No final-test score was produced,
and neither Nahw-Passage nor QALB test was accessed. The selected adapter and
record-level responses remain private.

## Frozen private inputs

The adapter rebuilt the registered records into the exact conversation schema
already used by F1-P1. It validated the authoritative private input hashes,
record identities, nested subsets, roles, source provenance, and the absence of
registered exact full-side overlap before writing. It printed only aggregate
metadata.

| View | Records | Aggregate provenance | Private file SHA-256 |
| --- | ---: | --- | --- |
| F2-P1 train | 2,000 | 2,000 Tibyan-corpus | `bbc48dcf78ddff1830661ad749fcc8f9fbfce8206f4f09cd9f4d6501823201d2` |
| F3-P1 train | 2,000 | 1,000 QALB-2014 L1 + 1,000 Tibyan-corpus | `d16decebe559e9a25da41ef59f63ca95e339972e22b9659dfc763e071fbc1546` |
| Common development | 975 | QALB-2014 L1 development | `adfdeb0c2e5730357226ce4e5156c300679629142ea0576d32dea9ac3050a950` |

The F2 record-ID digest is
`f56b749b19b1fbf0427a9f8af14011a19c6107fc82ef39a8e16399f45d3018be`.
The F3 natural and synthetic prefix digests remain
`7a21b02232163752188d7a9cd0f8e9c11f4e3bbbd26d3d3cd6f70df0d7ba7fd2`
and
`1e5ad4dca40667197461ac589df25fd1c239f04bb4d093661235b41b8d03ae8f`.
The prompt-template digest is
`8a195a560ccda30a55a6593f794dc048bcf18f6021dfca2181d3eee2b10a62c9`.

## Workflow safeguards

The Kaggle notebook is deliberately non-executing by default. It no longer
requires editing a code cell to activate a run. With no unique private
`f2_f3_execution_config.json` attached, the selected stage is `disabled`, the
approval fields remain blank, and no GPU stage executes. The ignored config is
created only after GO by `scripts/prepare_f2_f3_execution_config.py`, which
requires an exact 40-character workflow commit, issue #69 comment URL, stage-
specific confirmation, and—only for full training—a private passing smoke-
summary path. The notebook stays disabled when the file is missing and rejects
duplicate, malformed, or inconsistent activation files before repository or
GPU work.

The workflow:

- accepts exactly one of F2-P1 or F3-P1;
- requires one Kaggle NVIDIA P100 and does not fall back to CPU;
- reuses F1-P1's exact model revision, four-bit load, prompt, LoRA, optimizer,
  seed, two-epoch schedule, assistant-only loss, and common development view;
- rejects any formatted training record above 1,024 tokens instead of silently
  truncating or replacing it;
- smokes the longest record for one optimizer step and requires 1 GiB headroom;
- treats the smoke model process as tainted and forbids full training there;
- selects between epoch 1 and epoch 2 only by frozen common-development
  assistant-token loss, with the registered tie rule; and
- never loads a final test or generates evaluation predictions.

## Authorized smoke attempts and repairs

Issue #69 authorized only the F2-P1 longest-record one-step smoke at workflow
commit `c4d26b98264e8067a8584fb20e13e077af151778`. The private Kaggle execution
copy duplicated the activated configuration followed immediately by the
original default configuration in one cell. Python therefore encountered
`print(...)ARM = ...` on line 15 and raised `SyntaxError`.

The preserved aggregate check found zero smoke-summary files. No model was
loaded, no optimizer step ran, and no metric, adapter, or checkpoint was
produced. The failed Kaggle version is named
`failed-preflight-syntax-no-smoke`, and its P100 session was stopped. The GO was
consumed; no retry occurred.

The repair moves deliberate activation into a separately generated, strict,
text-free private JSON file. The public notebook remains disabled and
syntactically unchanged in Kaggle. This is an execution-safety repair only; it
does not change the frozen data, model, training, checkpoint, or evaluation
method.

Issue #69 then authorized the same limited smoke at workflow commit
`e86827d00f5af028927cac6d654f86fcaf6515d1`. The repaired activation config and
repository-commit gates passed. Kaggle mounted the private record file under
its current nested `/kaggle/input/datasets/<owner>/<dataset>/...` layout, while
the notebook still checked the older flat dataset directory. Private record
discovery therefore found zero files and failed before package installation,
model loading, LoRA attachment, trainer construction, or an optimizer step.

The private failed version is named
`failed-preflight-kaggle-mount-layout-no-model`, and its P100 session was
stopped. No smoke summary, metric, adapter, or checkpoint was produced. The GO
was closed conservatively; no runtime symlink, notebook hot-patch, or retry was
used.

The second repair searches recursively under the canonical `/kaggle/input`
root, supports both flat and nested Kaggle mount layouts, and still requires
exactly one file with the expected name. Duplicate Kaggle matches fail closed;
only when Kaggle contains no match does local ignored storage serve as the
development fallback. Existing checksum, schema, count, role, and provenance
validation remains unchanged.

The third authorized attempt used workflow commit
`aa96e9a776f5d04b39cb841ab3df42e149e98b81`. Its repository, activation, and
private-record gates passed, but the then-unconditional PyTorch/CUDA
force-reinstall did not return control after approximately one hour. The
private P100 session was stopped and preserved as
`aa96e9a-r01-preflight-interrupted`. It did not finish dependency validation,
load a model, construct a trainer, run an optimizer step, or create a smoke
summary. The GO was consumed without a retry.

PR #74 replaced that preflight with a metadata-first conditional setup. It
removes `--force-reinstall`, skips the heavy install when the runtime already
matches, otherwise performs one pinned P100-stack installation, and validates
the complete final stack before model loading. It changes no frozen data,
model, prompt, LoRA, optimizer, seed, checkpoint, or evaluation setting.

## Passing F2-P1 smoke

Issue #69 authorized one new private Kaggle P100 batch run at exact workflow
commit `f64edead0367e7659b107e5c4c309ed811d09071`. The run completed the frozen
longest-record one-step smoke and stopped before the separately gated full-
training section.

- approval: [exact GO comment](https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/69#issuecomment-5018574045)
- result audit: [issue #69 comment](https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/69#issuecomment-5018689524)
- run: [private Kaggle version 1](https://www.kaggle.com/code/univverssal/musahhih-f2-p1-smoke-f64edea-r01)
- model: `unsloth/gemma-3-4b-it-unsloth-bnb-4bit`
- model revision: `316726ca0bd24aa323bfaf86e8a379ee1176d1fe`
- hardware: Tesla P100-PCIE-16GB
- selected record: index 1287, 836 tokens; all 2,000 records were at or below
  the frozen 1,024-token limit
- optimizer steps: exactly 1
- peak reserved memory: 8,019,509,248 bytes
- measured headroom: 9,040,035,840 bytes
- required headroom: 1,073,741,824 bytes
- memory gate: passed
- downloaded private summary SHA-256:
  `800c29215c8803fdfaf4f530609b93c96d8b767ad83eb4fc8f92ac649e6df08c`
- activation-config SHA-256:
  `8da7e35709bd6900f55b25b54ffe85664e92be27932461fdb4a93cc66ce2bf12`
- executed-notebook SHA-256:
  `3a9393d987821bea69edd93c406951c7ee3aa6f2298c40978c0546bdf5cacdb8`

Kaggle initially exposed PyTorch 2.10.0+cu128 and torchvision 0.25.0+cu128.
The conditional heavy setup ran once for 166.773 seconds, then validated
PyTorch 2.6.0+cu124, torchvision 0.21.0+cu124, xformers 0.0.29.post3, torchao
0.16.0, NumPy 2.0.2, and CUDA 12.4. The text-free summary records
`contains_corpus_text=false`.

The run also preserved three compatibility warnings for later review: an
unused torchaudio 2.10.0+cu128 package conflicts with the frozen PyTorch
version; staged installation emitted temporary resolver warnings before the
required final stack validated; and Unsloth warned that Gemma 3 does not accept
`num_items_in_batch`, so gradient-accumulation equivalence remains a
reproducibility caveat.

## First F2-P1 full-training attempt

After review, issue #69 separately authorized one F2-P1 two-epoch training run
at the same workflow commit as the passing smoke. Private Kaggle version 1,
`univverssal/musahhih-f2-p1-full-f64edea-r01`, loaded the strict full-training
config and then failed closed at repository preflight.

- approval: [exact full-training GO](https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/69#issuecomment-5018840589)
- execution audit: [issue #77](https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/77)
- approved workflow commit:
  `f64edead0367e7659b107e5c4c309ed811d09071`
- repository commit cloned from current `main`:
  `1b2fc818ee043a7247d6ff00f6432f2a47d07674`
- execution-config SHA-256:
  `87a45e4c3f2af045f4ce4af582c27b19fd01d79999ea1ee8f7d32b668d9e87e7`
- prior smoke-summary SHA-256:
  `800c29215c8803fdfaf4f530609b93c96d8b767ad83eb4fc8f92ac649e6df08c`
- terminal error: `F2F3TrainingGateError: Approved workflow commit mismatch`

The notebook cloned the repository's default branch but did not check out the
approved immutable commit before computing `ACTUAL_WORKFLOW_COMMIT`. The public
smoke-audit merge had legitimately advanced `main` after the smoke. The exact-
commit gate therefore rejected the run as designed.

The failure occurred before private-record discovery or validation, dependency
installation, CUDA/model loading, LoRA/trainer construction, an optimizer
step, epoch evaluation, checkpoint or adapter creation, generation, or final-
test access. No training summary, metric, or score exists. The GO was consumed,
and no hot-patch or retry occurred.

Issue #78 adds a clean-repository fetch and detached checkout of the exact
approved workflow commit before verification. Because that repair creates a
new workflow commit, it must pass a fresh same-commit F2-P1 smoke before another
full-training run can be considered.

## Completed F2-P1 full training

PR #79 merged the immutable-checkout repair at
`ea4766ee205922c9fd4cb1af0357cca19bcfd59b`. The owner then explicitly waived
an additional post-repair smoke and authorized exactly one F2-P1 full-training
attempt. This exception is recorded rather than presented as the originally
recommended gate sequence. The repaired execution wrapper checked out the
already smoke-tested workflow commit
`f64edead0367e7659b107e5c4c309ed811d09071` before any private-data or GPU work.

- approval: [owner authorization and smoke waiver](https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/69#issuecomment-5018921893)
- execution audit: [issue #80](https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/80)
- private run: [Kaggle version 1](https://www.kaggle.com/code/univverssal/musahhih-f2-p1-full-ea4766e-r02)
- execution-wrapper commit:
  `ea4766ee205922c9fd4cb1af0357cca19bcfd59b`
- checked-out workflow commit:
  `f64edead0367e7659b107e5c4c309ed811d09071`
- execution-config SHA-256:
  `5049d23719295768c7329cd316b8d0ed6d4f7901621a76440d42458e751b00cb`
- executed-notebook SHA-256:
  `c32d977799b76915ebedcfec4001cae56cd3461755de10c1a142e868f60908b5`
- prior passing-smoke summary SHA-256:
  `800c29215c8803fdfaf4f530609b93c96d8b767ad83eb4fc8f92ac649e6df08c`
- hardware: Tesla P100-PCIE-16GB
- training: 2,000 F2-P1 records, two epochs, 250 optimizer steps, effective
  batch size 16
- development: 975 QALB-2014 L1 development records
- epoch 1 development assistant-token loss: `0.5975050330162048`
- epoch 2 development assistant-token loss: `0.611619234085083`
- frozen selection rule: lowest common-development assistant-token loss; ties
  within `1e-6` choose epoch 1
- selected checkpoint: `checkpoint-125`
- selected private adapter size: 131,252,288 bytes
- selected private adapter SHA-256:
  `935fdf02c95189934e40629f877d8692d325ef22895cbaa03fdb7390b0cd7b3e`
- checkpoint-selection file SHA-256:
  `39edee5e31d79c791a4ab0b14b7b85b838e28bcc302d9e552f168a03ac870e1b`

The run validated the registered F2-P1 train and common-development record
counts and hashes before loading the model. Its text-free selection record
sets `contains_corpus_text=false`, `nahw_passage_used=false`, and
`qalb_test_used=false`. The private checkpoints and adapter were not committed.
The public aggregate record is
[`f2_p1_full_training_summary.json`](f2_p1_full_training_summary.json).

The final stack was Python 3.12.13, PyTorch 2.6.0+cu124, CUDA 12.4,
Transformers 4.56.2, Unsloth 2026.7.3, Accelerate 1.13.0, PEFT 0.19.1, TRL
0.22.2, datasets 4.3.0, bitsandbytes 0.49.2, torchvision 0.21.0+cu124,
xformers 0.0.29.post3, torchao 0.16.0, and NumPy 2.0.2.

The three smoke-era compatibility caveats persisted: Kaggle retained an unused
torchaudio 2.10.0+cu128 package, staged installation emitted temporary resolver
warnings before final validation, and Unsloth warned that Gemma 3 does not
accept `num_items_in_batch`, making exact gradient-accumulation equivalence a
reproducibility caveat.

## Passing F2-P1 private development smoke

Issue #82 authorized one private development-only run after its guarded
workflow merged at `d176c6fa4bacc3ea05419484e2316e9e6201a9bd`. Private
Kaggle version 1 completed all 25 label-independent deterministic QALB-2014 L1
development records with zero empty outputs and no parser warnings.

The run verified `checkpoint-125`, the adapter-model, adapter-config, and
checkpoint-selection hashes before loading. It used greedy decoding, no
temperature argument, `max_new_tokens=256`, and seed 3407. The selected record-
ID SHA-256 is
`7cf5e1fbced3f28551053abb08d7747ae7eedcd70ca6900be2ea9ce4e58c4527`;
the private prediction JSONL SHA-256 is
`5f29061b4510ec678b138fdaf324629ea910ad4682729ffc2544f31d76d31f70`.
The private development exact-match count was not published or used to change
the experiment.

See [`f2_p1_dev_smoke_audit.md`](f2_p1_dev_smoke_audit.md) and the byte-identical
text-free [`f2_p1_dev_smoke_summary.json`](f2_p1_dev_smoke_summary.json). The
run accessed no final test and performed no training, checkpoint change, F3,
safety diagnostic, or XG execution. Its one-attempt authorization is consumed.

## What this audit does not establish

The completed stages establish two-epoch F2-P1 training, two frozen-development
loss measurements, deterministic checkpoint selection, existence of the
selected private adapter, and successful reload/generation/parsing on 25
private development records. Development loss and the technical smoke are not
held-out correction scores and do not establish adapter quality on a final
test. Full F2 evaluation, F3 training, QALB test, Nahw-Passage, safety-
diagnostic reruns, and XG were not executed.
