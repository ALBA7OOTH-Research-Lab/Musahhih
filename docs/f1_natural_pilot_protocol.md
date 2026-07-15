# F1-P1 Natural-Data Fine-Tuning Pilot Protocol

Status: proposed freeze for independent methodology review. No training is
authorized by this document until it is approved and merged.

Issue: https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/26

## Purpose and decision boundary

`F1-P1` is Musahhih's first supervised fine-tuning pilot using licensed natural
Arabic grammatical-error-correction data. It asks whether the same Gemma 3 4B
instruction model used for the untouched baselines can learn the correction
interface from a small, reproducible QALB training view on free Colab hardware.

This is an engineering and feasibility pilot, not the final natural-versus-
synthetic comparison. It does not authorize a Nahw-Passage run, QALB test
evaluation, synthetic generation, or a paper-level effectiveness claim. A later
protocol must freeze the matched `N` used for F1/F2/F3 after the synthetic source
is eligible.

## Frozen research boundaries

- QALB 0.9.1 train supplies supervision under the team's registered internal-
  research access. Its text, transformations, manifests, and model-facing
  records remain private and ignored by Git.
- QALB-2014 L1 development is the only pilot development set.
- Every QALB test split and Nahw-Passage remains evaluation-only. Neither may be
  loaded, prompted, scored, or used for a decision in this pilot.
- No prompt, checkpoint, hyperparameter, or stopping rule may be revised from a
  final-test result.
- The pilot does not create or use linguistic error labels.
- No paid API, Colab Pro feature, or paid storage/compute is required.

## Registered model

Use the same architecture and quantized checkpoint already validated for the
baselines:

| Field | Frozen value |
| --- | --- |
| Model ID | `unsloth/gemma-3-4b-it-unsloth-bnb-4bit` |
| Immutable revision | `316726ca0bd24aa323bfaf86e8a379ee1176d1fe` |
| Model slug | `gemma3-4b-it` |
| Loader | Unsloth `FastModel` |
| Quantization | checkpoint-supplied bitsandbytes 4-bit; do not requantize |
| Task modality | text only; no image inputs |
| Maximum sequence length | 1024 tokens including chat-template tokens |
| Adapter | LoRA; base weights remain frozen |

This checkpoint preserves direct architectural comparability with B0/B1/B2 and
was successfully loaded for inference on a free Colab Tesla T4. That inference
run does not prove that training fits. The official Gemma model card describes
the 4B instruction model and its gated upstream terms, while Unsloth publishes
the selected 4-bit checkpoint and `FastModel` loading route:

- https://huggingface.co/google/gemma-3-4b-it
- https://huggingface.co/unsloth/gemma-3-4b-it-unsloth-bnb-4bit
- https://docs.unsloth.ai/get-started/fine-tuning-llms-guide

The execution summary must resolve the requested revision to the same commit and
record the processor/tokenizer revision. A mismatch is a hard failure.

## Private data view

### Training pool

Read the unchanged archive at
`data/raw/qalb/QALB-0.9.1-Dec03-2021-SharedTasks.zip` together with the verified
private manifest `data/processed/qalb/qalb_train_selection.jsonl`.

The F1-P1 source-document pool is restricted to rows satisfying all of these
predicates:

1. `year == 2014`, `track == "L1"`, and `split == "train"`;
2. `eligible_for_training == true`;
3. no QALB-test or Nahw exact-source overlap flag;
4. no duplicate source group: `duplicate_source_within_split == false`; and
5. source and correction hashes differ.

The last two rules prevent duplicated weighting and exclude already-correct
records from correction training. They are pilot rules, not statements that the
excluded records are unusable in every future study.

Within each eligible document, parse only the official gold M2 actions for
annotator `0`. An action is eligible only when it is a substitution spanning
exactly one M2 source token, has exactly one non-empty whitespace-delimited
correction token, is not a no-op, and its declared offsets resolve exactly to the
stored source token. Insertions, deletions, merges, splits, multi-token
corrections, `noop` actions, malformed offsets, and actions from another
annotator are excluded. Do not use the M2 error-type label for selection,
training, stratification, or claims.

If a document has multiple eligible actions, retain exactly one: compute
`SHA256("F1-P1-edit|3407|" + edit_key)` for each and retain the lowest key. Define
`edit_key` from `record_key`, integer start/end offsets, and the SHA-256 of the
exact correction token. This prevents one highly edited document from receiving
extra weight without exposing licensed text.

### Deterministic pilot selection

Freeze `N_train = 2,000`. Compute for each eligible row:

```text
selection_key = SHA256("F1-P1|3407|" + edit_key)
```

Sort ascending by the hexadecimal key and take the first 2,000 rows. Here
`edit_key` is the stable text-free edit identifier defined above. Abort if fewer
than 2,000 edits pass, if a document or edit identifier repeats, or if rebuilding
the selection changes its SHA-256. Do not top up after tokenization; an
overlength or invalid selected record makes the run invalid and requires a
protocol amendment.

### Development view

Derive at most one eligible single-token substitution from every eligible
QALB-2014 L1 development document using the same document, M2-action, and
within-document hashing rules. Development may be used for loss measurement and
the frozen checkpoint rule below. It may not supply training examples or
demonstrations.

Before implementation, the private adapter must report only text-free counts,
hashes, length distributions, exclusion counts, and schema results. The exact
post-filter counts and selection hash are not guessed here: execution remains
blocked until the adapter derives and verifies them from the licensed archive.

## Training record and prompt contract

Build records in memory or under ignored `data/processed/qalb/`; never commit or
print them. Each private record contains the unchanged erroneous source passage,
the exact one-token erroneous span, and the exact one-token M2 correction. Use
the already frozen B0 prompt renderer in `scripts/prepare_nahw_eval.py` so the
supervised interface matches the held-out Nahw correction task.

The one-turn user text is exactly:

```text
صحح الكلمة الخاطئة المحددة في النص التالي.
أعد الكلمة المصححة فقط دون شرح أو علامات اقتباس.

النص:
{source}

الكلمة الخاطئة:
{error}
```

The assistant completion is exactly `{correction}`. Apply the selected
checkpoint's recorded Gemma 3 chat template once. Train only on assistant/
completion tokens; user, template, and padding tokens receive label `-100`. Do
not normalize, strip diacritics, alter Arabic letters, or rewrite punctuation.
Preserve the archive's decoded UTF-8 strings exactly after removing only the
QALB file-format identifier prefix already handled by the audited reader.

Reject and invalidate the planned run before loading the model if any formatted
record exceeds 1024 tokens, has an empty side, cannot round-trip through UTF-8,
or has a mismatched manifest hash. The implementation may report aggregate token
lengths but must not log text or token sequences.

## Frozen optimization configuration

| Setting | F1-P1 value |
| --- | --- |
| Seeds | `3407`, `3408`, `3409` when free allocation permits |
| Required minimum | seed `3407`; report single-seed limitation if others cannot run |
| Epochs | 2 exactly |
| Per-device train batch | 1 |
| Gradient accumulation | 16 |
| Effective batch | 16 sequences |
| Learning rate | `2e-4` |
| Scheduler | linear |
| Warmup ratio | `0.03` |
| Optimizer | `adamw_8bit` |
| Weight decay | `0.01` |
| Gradient clipping | `1.0` |
| Precision | BF16 when supported, otherwise FP16; record resolved choice |
| Gradient checkpointing | Unsloth mode enabled |
| Packing | disabled |
| LoRA rank / alpha / dropout | `16` / `32` / `0.0` |
| LoRA bias | `none` |
| LoRA targets | `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj` |
| Embeddings / LM head | not trainable |
| Logging | every 10 optimizer steps, aggregate values only |
| Evaluation | at the end of each epoch |
| Save | end of each epoch plus final adapter |

Set Python, NumPy, PyTorch, CUDA, Transformers, and trainer seeds consistently.
Request deterministic algorithms where supported and record every warning or
nondeterministic kernel. Cross-GPU bitwise identity is not promised.

The validated inference environment used Python 3.12.13, PyTorch 2.11.0+cu128,
Transformers 4.56.2, Unsloth 2026.7.2, and bitsandbytes 0.49.2. These are a
compatibility starting point, not a silent training lock. The implementation PR
must test and pin a mutually compatible full set including Accelerate, PEFT,
TRL, datasets, and CUDA before F1-P1 becomes executable. Any package change after
the first valid seed creates a new protocol revision; it cannot be mixed into
F1-P1 results.

## Checkpoint and development gate

Select between the epoch-1 and epoch-2 checkpoints using lowest mean
assistant-token cross-entropy on the frozen private QALB-2014 L1 development
view. Ties within `1e-6` select epoch 1. Do not use exact-match generation,
QALB test, Nahw-Passage, manual example preference, or category performance for
checkpoint selection.

After selection, run deterministic greedy generation on a separately frozen
25-record development smoke subset selected by
`SHA256("F1-P1-dev-smoke|3407|" + edit_key)`. This checks only that all records
complete, raw outputs are retained privately, and the parser/artifact pipeline
works. It does not select the checkpoint or alter settings. Record
`do_sample=false`, no temperature argument, and `max_new_tokens=256`.

## Free Colab execution gate

The target is a free Colab NVIDIA T4 with approximately 15 GiB VRAM, but free
GPU assignment and runtime duration are not guaranteed. Before the first valid
run, the implementation must perform a one-batch forward/backward/optimizer
smoke test using the longest selected record and report peak allocated/reserved
VRAM. Require at least 1 GiB headroom after the optimizer step. An out-of-memory
error, unsupported dtype, incompatible package set, or insufficient headroom
keeps F1-P1 blocked; do not reduce length, rank, or batch settings inside the
same protocol.

No training feasibility or duration is claimed until that GPU test succeeds.
Save resumable adapter/checkpoint state frequently enough for Colab interruption,
but a resumed run must retain the same run ID, hashes, seed, and settings and
must record the interruption.

## Private artifacts and reproducibility

Use run IDs such as:

```text
F1-P1__gemma3-4b-it__qalb14-dev__s3407__r01
```

Store ignored artifacts under `outputs/<experiment-id>/`:

- `training_summary.json`: protocol/run status, timestamps, Git SHA, all input
  and selection hashes, exact settings, resolved revisions, package/runtime/GPU
  metadata, step counts, losses, peak memory, warnings, and deviations;
- `metrics.jsonl`: aggregate step/epoch metrics without corpus text;
- `dev_predictions.jsonl`: private record IDs, source/gold hashes, raw response,
  parsed response, warnings, and scores; this file contains model output and may
  reconstruct licensed text, so it stays private;
- `adapter/` and checkpoint directories: private model artifacts governed by the
  base-model and QALB terms;
- `run.log`: sanitized operational events only; and
- SHA-256 inventory covering every artifact.

Never store QALB text in W&B, TensorBoard services, Hugging Face Hub, GitHub,
Notion, shared Drive folders, or console logs. Google Drive export is optional
and must use a team-approved private location without embedding credentials.

## Pilot go/no-go

F1-P1 is valid only if all of the following hold:

1. independent methodology review approved the merged protocol commit;
2. institutional/license guidance permits this transient private training view
   and private adapter retention;
3. the adapter reproduces the registered archive/manifest hashes and passes all
   privacy, split, overlap, duplicate, unchanged-pair, UTF-8, and length checks;
4. the pinned package set and longest-record GPU smoke test pass on the target;
5. training reaches the fixed two-epoch budget without a protocol deviation;
6. the frozen loss rule selects a checkpoint and the 25-record development smoke
   run completes with auditable private artifacts; and
7. no QALB test or Nahw-Passage data was loaded or consulted.

This gate establishes only that a natural-data pilot can be executed
reproducibly. Improvement is exploratory at this stage and is not a reason to
change F2/F3 or final-test decisions. Failure artifacts are preserved privately
with status `invalid`; never overwrite or silently repair a run.

## Required implementation work after approval

Open a separate issue to:

1. implement and test the private QALB training adapter using synthetic fixtures;
2. replace the generic `scripts/train_lora.py` template with a guarded Unsloth
   F1 runner or add a narrowly named runner;
3. create a beginner-readable Colab workflow with deliberate execution gates;
4. pin the tested dependency set and verify the longest-record GPU smoke test;
5. validate artifact privacy and resumability; and only then
6. execute seed 3407, followed by 3408 and 3409 only when free compute permits.

The current `scripts/train_lora.py` is not approved for F1-P1: it defaults to a
different model, lacks a pinned revision and Unsloth 4-bit loader, does not mask
prompt tokens explicitly, does not enforce private manifest/split safeguards,
and lacks immutable run IDs, hashes, memory gates, sanitized artifacts, and the
frozen checkpoint rule. It must not be run on QALB as-is.

## What this protocol does not claim

- No fine-tuning or GPU training smoke test has been run under F1-P1.
- No F1-P1 metric, runtime, memory measurement, or adapter exists.
- No QALB test or Nahw-Passage result was used.
- No expert linguistic validation or Arabic error categorization is claimed.
- No private corpus text or credentials are included in this document.
