# F2/F3 guarded training-workflow audit

Recorded: 2026-07-19

Status: private record assembly and static workflow implementation complete.
No model was loaded, no optimizer step ran, no inference ran, and neither
Nahw-Passage nor QALB test was accessed. A later exact-commit GO on issue #69 is
required before the GPU smoke or full training may be enabled.

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

The Kaggle notebook is deliberately non-executing by default. Both execution
flags, both stage confirmations, the approved workflow commit, and its issue
comment reference are blank. A smoke or full run requires an exact 40-character
workflow commit plus a GO comment under issue #69. Full training additionally
requires a preserved passing smoke summary for the same arm and commit from a
fresh runtime.

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

## What this audit does not establish

Static checks cannot establish current Kaggle P100 availability, runtime
installation compatibility, peak VRAM, training stability, epoch losses,
checkpoint existence, adapter quality, or benchmark performance. Those facts
must come from separately approved, preserved executions. No score is reported
here.
