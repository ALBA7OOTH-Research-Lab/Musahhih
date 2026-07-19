# Tibyan F2/F3 manifest audit

Recorded: 2026-07-19

Status: canonical private manifest build and processor-length validation
complete; public audit recorded. The protocol remains NO-GO until independent
methodology review and merged-commit GO. No training or inference is authorized.

## Inputs verified

The authoritative Zenodo file was downloaded to an ignored local path. The
following values matched the earlier intake exactly:

| Item | Observed value |
| --- | --- |
| Archive bytes | 5,614,320 |
| Archive SHA-256 | `a7f318d9c64d7d2c214a5f44ee515b70c7d1ee930178b4b6b00cf5c733b0dfda` |
| Corrected final-file SHA-256 | `5f8fde9319df89419ade12114f14466301cafb181ce807df896fb5de2361c4e4` |
| Erroneous final-file SHA-256 | `e3b72a45abffbf2a63da07912adc0fa0b29a41c495d609aa2b917fc4d58956a6` |
| Paired lines | 6,192 |

The audit decoded the two final files as UTF-8 with BOM handling. It did not
print or commit a corpus line or token.

## Why whole-pair filtering is not viable

A strict rule requiring equal whitespace-token counts and exactly one different
token position retained only 3 pairs:

| Whole-pair classification | Pairs |
| --- | ---: |
| Exactly one token substitution | 3 |
| Identical corrected/erroneous sides | 2 |
| Equal token counts with multiple differences | 1,689 |
| Different token counts | 4,498 |

This cannot support the registered 2,000-record natural reference. The draft
protocol therefore does not treat a whole Tibyan pair as one atomic edit.

## Canonical forced-alignment view

The guarded manifest builder implemented the draft protocol's full unit-cost token
Levenshtein graph and retained a substitution only when its virtual diagonal
node was the sole active node in its alignment layer. This is an exact graph
property: every minimum-cost alignment must traverse that edge. It then required
the erroneous token to occur exactly once in the erroneous passage and retained
at most one seeded substitution per released line pair.

| Aggregate | Count |
| --- | ---: |
| Pairs with at least one forced substitution | 6,167 |
| Forced substitution edges | 179,503 |
| Pairs with at least one forced substitution whose error token is unique | 6,165 |
| Unique-error forced substitution edges | 132,900 |
| Proposed records after at-most-one-per-pair selection | 6,165 |
| Exact-side connected groups | 6,156 |
| Groups containing more than one retained record | 9 |
| Largest connected group | 2 |

The canonical nested selection hashes are:

- F2-P1 2,000 record IDs:
  `f56b749b19b1fbf0427a9f8af14011a19c6107fc82ef39a8e16399f45d3018be`;
- F3-P1 1,000-record synthetic prefix:
  `1e5ad4dca40667197461ac589df25fd1c239f04bb4d093661235b41b8d03ae8f`.

## Canonical overlap and project split

Both full sides of every retained record were compared by exact SHA-256 against
the existing QALB source/correction hash registry and the registered Nahw fields.
The entire connected group would have been excluded on any match.

| Group-level exclusion trigger | Retained records affected |
| --- | ---: |
| QALB test full-side exact match | 0 |
| QALB train/development full-side exact match | 0 |
| Nahw field full-side exact match | 0 |

These are exact checks only. They do not rule out paraphrases, shared guide
sources, similar fragments, or base-model pretraining contamination.

Using the draft 80/20 group-hash bucket rule produced:

| Project split | Records before one-per-group representative rule | Groups |
| --- | ---: | ---: |
| Training | 4,893 | 4,886 |
| Development | 1,272 | 1,270 |

Thus the one-representative-per-group training capacity is 4,886, which
is sufficient for a nested 2,000-record F2 selection and 1,000-record F3
synthetic half.

Private ignored output hashes:

| Artifact | SHA-256 |
| --- | --- |
| Full private registry | `28ad514fe94a908d9287aa7e31dd696871a5bba77d3c41ecb6d1029784900553` |
| F2 private training selection | `395d0554d8836c08727144ec44e1011cceeb19b6c7f90973655882047c6bdb0a` |
| Project-development selection | `3da7e1c84de879a896e15ea0a4e283b3b67013187c25249ec2e38b8cc80b2ad9` |
| Private aggregate summary | `3623d05081fd418c023a5c84911cb7cbf67db2e27feaf79a34a7bb4f83b51caf` |

The exact QALB registry input hash was
`e0a87eb3b6bdf9d0dca4edd29e4a4ab72b8c6a49d2e29f83aaab496147939691`;
the hash-only Nahw input was
`97d4f5e0b75ff5848ffdff113a74676c0de607d0bb877e1f26c1bde1585a2208`.

## Exact formatted-token length gate

The 2,000 selected records were rendered with the frozen correction prompt,
assistant completion, Gemma chat template, and `GemmaTokenizerFast` from
`unsloth/gemma-3-4b-it-unsloth-bnb-4bit` at requested revision
`316726ca0bd24aa323bfaf86e8a379ee1176d1fe`, using Transformers 4.56.2.
The rendered string was tokenized with `add_special_tokens=False`, matching the
validated F1 notebook's corrected flat-token guard.

| Aggregate | Value |
| --- | ---: |
| Selected records | 2,000 |
| Minimum formatted tokens | 82 |
| Median formatted tokens | 294.5 |
| 95th percentile formatted tokens | 477 |
| Maximum formatted tokens | 836 |
| Records above 1,024 | 0 |

The text-free per-record length digest was
`a518a43d7f7a5de317f039f16b30e80587539b0a7da7ca0acd35fba3726ab5b1`.
The longest record ID was
`tibyan-14623621-ca2116f4fb4c9c0513cce1eeb7be93d98eeea2ee68989ff7ea5c8590bd1500aa`.
Only tokenizer/configuration files were loaded; no model weights, GPU, forward
pass, generation, or training was used.

## F3 natural-prefix verification

The already authorized F1-P1 private adapter was rerun against the unchanged
QALB archive and frozen manifests without printing text. It reproduced the
registered 2,000-record selection hash
`03588f135e82575f8de9030b948d6b59cd14e3ca9c218207b0f33885d1f8e2d1`.
The ordered record-ID digest for all 2,000 rebuilt private records was
`cad5f75e3e81d8623df8add6aacad8716c49b12e3dde277b8a2fceea62265530`;
the ordered first-1,000 prefix proposed for F3 was
`7a21b02232163752188d7a9cd0f8e9c11f4e3bbbd26d3d3cd6f70df0d7ba7fd2`.
Thus the natural half is a nested frozen prefix, not a new sample selected after
viewing F1 outcomes.

## Remaining gates

- Independently review the implementation and reproduce every aggregate and
  canonical output hash.
- Review the automatic-alignment limitation and the post-F1 staged design.
- Obtain GO for the exact merged protocol/implementation commit before any GPU
  smoke, training, model inference, or final-test access.

The build was executed with:

```bash
python scripts/prepare_tibyan_f2_f3.py \
  --archive "data/raw/tibyan/Data (1).rar" \
  --corrected "data/raw/tibyan/extracted/Data/Final-Data-after-human-annotation/Tibyan Correct.txt" \
  --erroneous "data/raw/tibyan/extracted/Data/Final-Data-after-human-annotation/Tibyan Incorrect.txt" \
  --output-dir data/processed/tibyan_f2_f3
```

Eight synthetic-fixture tests cover forced substitutions, insertion/deletion
rejection, repeated-token ambiguity, connected groups, test-overlap exclusion,
corpus-text-free summaries, and nested selection.

No training, generation, model loading, inference, checkpoint selection, paid
service, expert linguistic review, or final-test scoring occurred in this audit.
The project-generated `XG` operator remains disabled.
