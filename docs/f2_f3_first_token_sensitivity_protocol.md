# F2/F3 first-token sensitivity protocol

Status: prepared, not executed.

## Question

The accepted seed-3407 primary evaluation retained every generated correction
under the frozen conservative parser. F2-P1 produced 20 outputs flagged
`multiple_words`; F3-P1 produced 2. This post-hoc sensitivity asks exactly how
many scores would change if the first whitespace-delimited token were used for
those already flagged outputs.

This is not a new parser, a corrected primary metric, or a basis for changing
any model or experiment decision. The accepted exact-match result remains the
primary result.

## Frozen counterfactual

For each arm independently:

1. verify the private prediction file against its accepted SHA-256;
2. verify exactly 511 unique rows, stored exact-match booleans, warning
   semantics, and ordered F2/F3 record alignment;
3. leave every unflagged row unchanged;
4. only when `multiple_words` is already present, split the existing
   `parsed_correction` on Unicode whitespace and use element zero;
5. compare that token with the existing private gold string using the same
   byte-exact equality as the primary evaluation; and
6. report only aggregate rescue, harm, adjusted-correct, accuracy, and paired
   difference counts.

The operation is applied symmetrically to F2-P1 and F3-P1. It does not inspect
linguistic categories or choose among alternative parsing rules.

## Exact private inputs

- F2-P1 predictions: 511 rows, SHA-256
  `ca4a6eb2f5e40a60be14f59cdc7365a0f327b41ab0b8f46c8a08c43cfb442753`;
- F3-P1 predictions: 511 rows, SHA-256
  `ccb296e0f091bf28ebe4d7c8b9ed454934f4dade0b5793dcf1b3a5706379c35c`.

The audit must reproduce the accepted original totals of 105 F2-P1 and 162
F3-P1 exact matches and the accepted warning counts of 20 and 2 before it
computes the counterfactual.

## Public/private boundary

Permitted public output is limited to file hashes, row counts, original and
counterfactual aggregate correct counts and accuracies, rescue/harm counts,
and F3-minus-F2 aggregate differences. The output must not contain a record ID,
passage, prompt, source token, gold correction, raw response, parsed response,
or individual warning row.

The source predictions remain ignored and private. The script prints no
record-level value, including on failure.

## Authorization boundary

Repository preparation and synthetic tests do not authorize reading the
private prediction files. One local CPU-only execution requires a fresh owner
GO naming the exact merged commit, both input hashes, and the sole permitted
output location. It authorizes no GPU, model loading, inference, training,
checkpoint selection, prompt/parser change, repeat evaluation, QALB test,
safety diagnostic, or XG operation.
