# F2/F3 five-seed RTX 3090 aggregate audit

## Outcome

The single authorized issue-#185 CPU Job completed successfully without retry.
It audited all ten private prediction files from the five completed issue-#183
evaluations: 511 rows per arm and seed, 5,110 record-arm outputs in total.

Every file passed its recorded SHA-256 and row-count gate. The audit also
validated unique record IDs, identical F2/F3 order within each seed, identical
order across all seeds, exact-match recounts, and full recomputation of each
seed's discordant counts, exact McNemar test, and deterministic paired
bootstrap interval. No corpus text, record ID, prediction, prompt, gold value,
or model response was published.

## Results

| Seed | F2-P1 synthetic-only | F3-P1 50:50 mixed | F3 minus F2 |
| ---: | ---: | ---: | ---: |
| 3407 | 105/511 (20.55%) | 169/511 (33.07%) | +12.52 pp |
| 3408 | 112/511 (21.92%) | 161/511 (31.51%) | +9.59 pp |
| 3409 | 111/511 (21.72%) | 155/511 (30.33%) | +8.61 pp |
| 3410 | 115/511 (22.50%) | 169/511 (33.07%) | +10.57 pp |
| 3411 | 111/511 (21.72%) | 163/511 (31.90%) | +10.18 pp |

Across seeds, F2-P1 averaged 21.68% (sample SD 0.71 percentage points) and
F3-P1 averaged 31.98% (sample SD 1.15 points). The paired F3-minus-F2
difference averaged +10.29 points (sample SD 1.45; range +8.61 to +12.52).
F3-P1 exceeded F2-P1 in every seed.

## Interpretation

The direction and magnitude of the mixed-over-synthetic result are stable
across these five training seeds. This directly weakens the explanation that
the original 11.15-point primary result arose solely from a fortunate F3 seed
or unfortunate F2 seed.

This cohort remains post-hoc robustness evidence. Training used the completed
A100 five-seed wave, while all recovery inference used uniform RTX 3090
hardware. The original seed-3407 matched P100 evaluation remains the
preregistered primary result; the recovered cohort neither replaces it nor
turns the hardware recovery into a preregistered experiment.

The aggregate authorization is consumed. Do not repeat training, inference,
or aggregation or tune any decision from these outcomes.
