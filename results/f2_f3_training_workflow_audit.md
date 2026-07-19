# F2/F3 guarded training-workflow audit

Recorded: 2026-07-19

Status: private record assembly and static workflow implementation complete.
Two authorized F2-P1 smoke attempts stopped during fail-closed preflight: the
first on a malformed private execution copy, and the second on an obsolete
flat Kaggle input-mount assumption. Neither reached model loading or an
optimizer step. No inference ran, and neither Nahw-Passage nor QALB test was
accessed. A repaired workflow and a fresh exact-commit GO on issue #69 are
required before another GPU attempt.

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

## What this audit does not establish

Static checks cannot establish current Kaggle P100 availability, runtime
installation compatibility, peak VRAM, training stability, epoch losses,
checkpoint existence, adapter quality, or benchmark performance. Those facts
must come from separately approved, preserved executions. No score is reported
here.
