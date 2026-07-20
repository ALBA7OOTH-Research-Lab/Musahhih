# F2/F3 guarded training-workflow audit

Recorded: 2026-07-20

Status: private record assembly and the guarded workflow are complete. After
three preserved pre-result infrastructure attempts and reviewed repairs, the
fourth authorized F2-P1 smoke completed exactly one optimizer step on the
longest validated record and passed the frozen P100 memory gate. No inference
ran, no benchmark score was produced, and neither Nahw-Passage nor QALB test
was accessed. Independent review and a separate exact-commit GO are required
before one F2-P1 full-training run.

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

## What this audit does not establish

The passing smoke establishes current P100 setup compatibility and measured
memory feasibility for one worst-case optimizer step. The preflight failure
does not establish two-epoch stability, epoch losses, checkpoint existence,
adapter quality, or benchmark performance. No score is reported here. Full F2
training, F3,
development generation, QALB test, Nahw-Passage, safety-diagnostic reruns, and
XG were not executed.
