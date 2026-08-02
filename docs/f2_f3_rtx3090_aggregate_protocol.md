# F2/F3 RTX 3090 five-seed aggregate audit

Status: issue #185 repository preparation only; no PVC access or metric
computation authorized.

## Frozen source

The audit reads only the five completed issue-#183 evaluation attempts under
`/private/evaluations/issue-183`, source attempt `5155890101`, produced at
evaluation commit `e004e625a00c9c1c6fac7e2dbc0e7bc450fbad17`. Seeds
3407–3411 all completed both F2-P1 and F3-P1 on exact RTX 3090 hardware with
exit code zero and zero restarts. Training, checkpoint selection, inference,
and test access are finished and must not be repeated.

## CPU-only audit

One write-once CPU Job must, before reporting a number:

1. require all five complete summaries with exact attempt, commit, test hash,
   batch-16, RTX 3090, and passed pre-test-gate identities;
2. hash and parse all ten private prediction JSONL files;
3. require exactly 511 unique ordered record IDs and Boolean exact-match values
   in every file;
4. require identical paired order within each seed and identical record order
   across all five seeds;
5. recompute every correct count, accuracy, discordant count, exact McNemar
   p-value, and deterministic 10,000-sample paired-bootstrap interval;
6. require every recomputed value to equal its private seed summary; and
7. compute every seed result, per-arm mean/sample SD, and F3-minus-F2
   mean/sample SD/minimum/maximum.

Only corpus-text-free aggregates and hashes may leave the PVC. Predictions,
record IDs, prompts, gold corrections, raw responses, adapters, and logs remain
private. Sample SD uses denominator n-1; the cohort is post-hoc robustness
evidence and does not replace the original seed-3407 primary result.

## Authorization boundary

Preparation and merge authorize no Kubernetes object, PVC read, metric,
training, inference, retry, QALB test, or XG. After merge, one fresh issue-#185
owner GO naming the exact commit may authorize exactly one no-GPU aggregate
Job with `backoffLimit: 0` and a one-hour deadline. Failure is terminal and may
not be retried without another reviewed gate and GO.
