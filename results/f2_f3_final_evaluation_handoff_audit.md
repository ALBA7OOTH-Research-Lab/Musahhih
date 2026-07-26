# F2-P1/F3-P1 timeout-safe final-evaluation handoff audit

## Scope

This audit records the first terminal state of the single replacement segment
authorized on issue #98. It does not report an F2-P1 score, an F3-P1 partial
score, or any F2/F3 comparison. It does not authorize continuation.

The private Kaggle kernel was
[`univverssal/musahhih-f2-f3-final-timeout-safe-8019450-r02`](https://www.kaggle.com/code/univverssal/musahhih-f2-f3-final-timeout-safe-8019450-r02),
version 1, using workflow commit
`80194505bd00513f4e1661ef10798f79b83ae16b`. Kaggle reported terminal
`COMPLETE`. The evaluator deliberately returned
`incomplete_time_budget` after 34,277 elapsed seconds against its 34,200-second
safe-stop threshold.

## Preserved handoff

The timeout safety mechanism behaved as designed:

- F2-P1 completed all 511 frozen records;
- F3-P1 completed and preserved the first 168 frozen records;
- every private row had been flushed and `fsync`-ed;
- `progress.json` and `public_summary.json` agreed on counts, hashes, workflow
  commit, runtime, and terminal state;
- no metric or partial comparison was included in the handoff summary; and
- the handoff explicitly requires a fresh exact-commit owner GO before any
  continuation.

The private prediction hashes are:

- F2-P1:
  `ca4a6eb2f5e40a60be14f59cdc7365a0f327b41ab0b8f46c8a08c43cfb442753`;
- F3-P1 prefix:
  `420e5f2f8d44230e3b9df516f55bfcc331e9fb5f20b570213f3aa5d851f5ec14`.

## Verification

The private audit verified without printing record text:

- the prepared 511-record Nahw-Passage hash
  `acb3cfd204b35d5415532fbd32a4a5231b553fae329ab8f48e8454609e10279b`;
- the accepted B0 and F1-P1 prediction hashes;
- 511 unique, ordered F2-P1 rows aligned exactly to the frozen input;
- 168 unique, ordered F3-P1 prefix rows aligned exactly to the first 168 frozen
  inputs;
- stored source, prompt, and gold fields matched the frozen prepared rows;
- raw-response, parsed-correction, warning, and exact-match field types were
  valid;
- stored exact-match booleans were consistent with parsed correction versus
  gold correction; and
- the corpus-text-free summary and progress manifests contained no record-level
  fields.

The runtime was one Tesla P100-PCIE-16GB with CUDA 12.4, Python 3.12.13,
PyTorch 2.6.0+cu124, Transformers 4.56.2, Unsloth 2026.7.5, PEFT 0.19.1,
TRL 0.22.2, and Accelerate 1.13.0.

## Privacy and interpretation

Nahw-Passage text, prompts, gold corrections, record IDs, raw model responses,
parsed corrections, warnings, private prediction files, and the run log remain
ignored and unpublished. No result-bearing aggregate was used to decide
whether to continue.

This is a valid recoverable engineering handoff, not a completed matched
evaluation. The preregistered primary and secondary comparisons remain
unavailable until both arms contain all 511 aligned records. Do not continue,
retry, hot-patch, or launch another kernel without a fresh scope-specific owner
GO bound to an exact merged workflow commit.
