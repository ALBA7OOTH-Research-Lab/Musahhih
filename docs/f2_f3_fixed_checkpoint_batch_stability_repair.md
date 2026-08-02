# Fixed-checkpoint batch-stability repair

Status: issue #194 preparation only; no execution is authorized.

## Preserved terminal state

Issue #192 created exactly five fixed-checkpoint Jobs. Seeds 3408, 3410, and
3411 completed. Seeds 3407 and 3409 failed with exit code 1 before test access.
Both retained logs matched only the fixed pre-test signature `RTX 3090
synthetic output equivalence failed`; they showed no OOM, checkpoint, package,
disk, authentication, timeout, or no-progress signature. No retry occurred.

## Repair rationale

The frozen evaluation path is greedy batch-16 decoding. The failed technical
gate additionally required that batch-16 output equal single-record output.
That cross-execution-shape equality is stricter than stability of the actual
frozen path and failed for two adapters before any research input was opened.

The repair keeps batch size 16 and requires two consecutive batch-16 runs on
the same 16 synthetic, non-corpus prompts to be byte-identical. It does not
compare against a single-record path. A mismatch still fails closed before
test staging validation.

## Replacement boundary

Only seeds 3407 and 3409 are eligible. Each replacement starts from record
zero in a new write-once issue-#194 output directory. It validates both retained
epoch checkpoints, evaluates only the unselected F2-P1/F3-P1 checkpoints, and
retains the exact RTX 3090 runtime, prompt, parser, model revision, greedy
decoding, test hash, per-row `fsync`, atomic progress, 11-hour safe stop,
20-minute no-progress guard, 12-hour deadline, and `backoffLimit: 0`.

The completed issue-#192 seeds are never rerun. No source prediction is reused
for either failed seed because both failures preceded test access. A later
CPU-only aggregate must validate the three issue-#192 completions and the two
issue-#194 replacements under a separate gate and GO.

## Authorization

Preparation and merge create no Kubernetes object and authorize no GPU,
private-input access, model load, inference, prediction, metric, training,
retry, continuation, aggregation, QALB test, prompt/parser change, diagnostic,
or XG. The two replacement Jobs require a fresh owner GO naming the exact
merged commit.
