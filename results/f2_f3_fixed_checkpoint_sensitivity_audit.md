# F2/F3 fixed-checkpoint sensitivity audit

## Outcome

Issue #196's single authorized CPU-only Job completed with exit code zero and
zero restarts. It validated the retained training checkpoint identities, 20
unique private prediction files, every 511-row count, the frozen test identity,
prediction hashes, schemas, record order, and source statistics before
assembling the three checkpoint policies. No GPU, model loading, inference,
training, checkpoint selection, or reselection occurred in the audit.

| Checkpoint policy | F2 mean (SD) | F3 mean (SD) | F3 minus F2 mean (SD) |
| --- | ---: | ---: | ---: |
| Fixed epoch 1 | 21.68% (0.71) | 27.79% (0.42) | +6.11 (0.91) pp |
| Fixed epoch 2 | 25.40% (0.81) | 31.98% (1.15) | +6.58 (1.53) pp |
| Dev-selected | 21.68% (0.71) | 31.98% (1.15) | +10.29 (1.45) pp |

F3-P1 exceeded F2-P1 in every seed under both matched fixed-epoch policies.
The fixed-epoch paired differences ranged from +5.28 to +7.44 points at epoch
1 and +4.50 to +8.81 points at epoch 2. The natural-development rule selected
epoch 1 for every F2 replica and epoch 2 for every F3 replica. It therefore
increased the mean observed separation from roughly 6 points under matched
epochs to 10.29 points, but it did not create the direction of the result.

This analysis is post-hoc sensitivity evidence. It does not replace the
pre-specified original seed-3407 P100 comparison, and it does not establish
that the natural-development checkpoint rule is neutral with respect to effect
magnitude.

## Provenance and privacy

- aggregate executable commit:
  `c96bbeec2c9ff460c84983086006c7c4bcc78a52`;
- owner GO: issue #196 comment `5158544312`;
- selected source: issue #183 attempt `5155890101`;
- unselected completed source: issue #192 attempt `5157509573`;
- unselected repair source: issue #194 attempt `5158062318`;
- Job: `musahhih-f2-f3-fixed-aggregate-a58544312`;
- Job interval: 2026-08-02 14:33:53--14:40:20 UTC;
- common ordered-record SHA-256:
  `367db53167eed2ef918aa1e44f3622938a7db19268b0867146a044ca1054296d`.

The machine-readable public summary records the reviewed source-summary hashes
and all aggregate values. Predictions, record identifiers, corpus text, model
responses, private logs, adapters, checkpoints, and development losses remain
private. Its SHA-256 is
`e6367ecbe47421a54314fc66d6e0bf26f57bed58c585ca7d8360bb6828f5b21f`.

## Authorization boundary

The single aggregate authorization is consumed. Do not rerun the aggregate or
use these results to change prompts, parsing, training, checkpoint selection,
or the primary analysis. QALB test and XG remain outside scope.
