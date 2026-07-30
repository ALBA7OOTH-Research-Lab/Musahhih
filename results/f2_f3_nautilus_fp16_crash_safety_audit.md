# F2/F3 Nautilus FP16 and crash-safety repair audit

## Scope

Issue #167 repairs the repository workflow after issue #155's five authorized
A100 Jobs failed before their first optimizer step. This is a corpus-text-free
implementation audit. No cluster object, model, private input, training,
inference, prediction, or metric was produced while preparing the repair.

## Confirmed failure

Retained logs for seeds 3408, 3409, and 3411 showed the same exception during
`SFTTrainer` construction: Gemma loaded in BF16 on the A100 while the frozen
trainer requested FP16. The earlier preflight had checked CUDA, packages,
imports, compiler availability, and precision flags, but it had not loaded the
model or constructed the trainer. Therefore it could not detect the runtime
model-dtype decision.

All five Jobs were preserved as terminal failures without retry. The retained
tracebacks occurred before `trainer.train()`. No optimizer step, epoch
checkpoint, selected checkpoint, inference, prediction, or metric was
produced.

## Repair

The repository now:

- passes `torch.float16` explicitly to the frozen Gemma model loader;
- fails before trainer construction unless the loaded model configuration is
  exactly FP16;
- adds a distinct no-private `fp16-trainer-smoke` stage that loads the exact
  model revision, constructs the exact LoRA model, completion-only collator,
  and `SFTTrainer` on one built-in synthetic row, and executes zero optimizer
  steps;
- derives every Job and private attempt identity from its fresh GitHub
  owner-comment ID, preventing an authorized replacement from overwriting a
  prior attempt;
- copies complete stdout/stderr to a write-once private PVC log, fails closed
  if `tee` fails, atomically records the process exit code, and synchronizes
  storage before Pod exit;
- writes a corpus-text-free failure record containing only the phase, completed
  arms, exception class, and a SHA-256 of the exception message;
- saves operational recovery checkpoints every 25 optimizer steps without
  pruning either epoch-boundary checkpoint or changing the checkpoint-selection
  rule, and writes a durable SHA-256 sidecar covering the adapter, Trainer,
  optimizer, scheduler, and RNG state for every checkpoint; and
- permits continuation only after a fresh GO and exact validation of the
  commit, seed, private-input identities, completed-arm records, checkpoint
  identities, and Trainer state.

Automatic Kubernetes retry remains disabled with `backoffLimit: 0`.
Nahw-Passage and QALB test remain absent from every training and smoke
manifest.

## Scientific boundary

The repair does not switch the experiment to BF16. It preserves the original
P100-compatible FP16 contract. The 25-step recovery saves are operational
artifacts only: they do not change the model, data, optimizer, learning-rate
schedule, batch size, examples, losses, evaluation cadence, two epoch
candidates, or common-development selection rule.

## Validation

- `python -m compileall scripts`: passed.
- `python -m unittest tests.test_f2_f3_nautilus -v`: 22 tests passed.
- `python -m unittest discover -s tests -v`: 265 tests passed.
- Generated `fp16-trainer-smoke` manifest: one Job, corpus-text-free.
- Generated paired-training manifest: five unique seed Jobs,
  corpus-text-free.
- Kubernetes client dry-run accepted all six generated Job objects.
- `git diff --check`: passed.

The exact A100 model/trainer behavior cannot be proven locally. After review
and merge, the only eligible execution is one separately authorized,
no-private, zero-optimizer-step FP16 model/trainer smoke. Replacement training
requires another later exact-commit owner GO.
