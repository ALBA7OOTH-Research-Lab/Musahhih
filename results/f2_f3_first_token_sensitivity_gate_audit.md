# F2/F3 first-token sensitivity gate preparation audit

## Outcome

Issue #188 prepares a deterministic, fail-closed, CPU-only audit for the two
accepted seed-3407 private prediction files. It answers the specific reviewer
question about F2-P1's 20 multi-token outputs while applying the same
counterfactual to F3-P1's 2 flagged outputs.

No private prediction was opened and no test-derived sensitivity result was
computed during preparation.

## Implemented controls

The prepared audit:

- hard-gates both accepted prediction SHA-256 values;
- requires 511 rows per arm, unique identities, and identical ordered
  alignment;
- reproduces the accepted original correct totals and multi-token counts;
- checks the stored exact-match and `multiple_words` warning contracts;
- changes only the score counterfactual for already flagged outputs;
- applies the first-whitespace-token rule symmetrically to F2-P1 and F3-P1;
- emits only corpus-text-free aggregate evidence; and
- creates its summary write-once with `fsync`.

All failures identify only the arm, contract, and row position. They do not
print private record identities or text.

## Research boundary

This is explicitly post-hoc robustness analysis. It cannot replace the frozen
parser or primary result, and it cannot be used to tune prompts, parsing,
models, checkpoints, or training data. It requires no model and no GPU.

Preparation authorizes no private-file access or execution. After merge, one
fresh exact-commit owner GO is required for a single read-only local audit.
