# B1-P1/B2-P1 prompt baseline implementation report

Date: 2026-06-25

GitHub issue: https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/2

## Scope implemented

- Added frozen B0/B1/B2 prompt assembly helpers in `scripts/baseline_prompts.py`.
- Added deterministic B1-P1 candidate filtering and private bundle writer in `scripts/prepare_b1_prompt_bundle.py`.
- Added canonical experiment-ID, output-directory, hash-summary, and Nahw final-evaluation gating helpers in `scripts/run_prompt_baseline.py`.
- Added synthetic-fixture tests for prompt snapshots, B1 selection rules, non-overwrite behavior, corpus-text-free summaries, and final-evaluation gating.

## Research safeguards

- B1-P1 and B2-P1 templates are rendered from frozen public protocol text.
- B1 selection uses the frozen content-neutral identity digest rule: `SHA-256(candidate_identity + "|B1-P1")`.
- The B1 private bundle writer refuses to overwrite an existing bundle.
- The run scaffold refuses to overwrite an existing run directory.
- Nahw-Passage execution remains gated behind an explicit `--confirm-final-eval` flag.
- No QALB corpus text, private generated bundle, model output, credential, checkpoint, adapter, or large artifact is committed in this report.

## Validation status

Public synthetic validation is implemented for:

- exact prompt whitespace and ordering;
- filtering non-train, ineligible, multi-token, empty, repeated-token, same-token, out-of-length, and non-`Edit` candidates;
- deterministic candidate ordering and distinct-record selection;
- selected-identity hash calculation;
- private bundle non-overwrite behavior;
- canonical experiment IDs;
- canonical output directory non-overwrite behavior;
- final Nahw-Passage gate; and
- corpus-text-free summary hashes.

Private validation not run in this local session:

- two independent real B1 bundle generations from the licensed QALB archive;
- real expected B1 structural counts against QALB: 3,116 candidate annotations and 458 distinct records;
- real selected identity SHA-256 reproduction against private QALB; and
- model loading or QALB-development generation capture.

Reason: those checks require private licensed QALB artifacts and/or model runtime. The implementation keeps the commands and checks available for a licensed team member without exposing private text in Git.

## Next review focus

Reviewers should inspect:

- byte-for-byte prompt snapshots against `docs/prompt_baseline_protocol.md`;
- B1 candidate filtering and identity hashing;
- private-data boundaries in CLI output and committed files;
- non-overwrite behavior for generated artifacts; and
- whether the run scaffold is sufficient before wiring full model inference.
