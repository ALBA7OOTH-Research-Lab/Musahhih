# Musahhih

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/ALBA7OOTH-Research-Lab/Musahhih/blob/main/notebooks/01_nahw_baseline_unsloth.ipynb)

**Musahhih** is an open research project on improving Modern Standard Arabic grammatical error correction with open-weight language models.

The project builds on the **Nahw** benchmark and related Arabic grammatical error correction work. Its first goal is to establish a reproducible baseline on held-out Arabic correction data, then compare LoRA/QLoRA fine-tuning with natural, synthetic, and mixed training corpora.

## Research question

> Can supervised fine-tuning of an open model on existing Arabic grammatical-error-correction data improve MSA correction performance over the untouched model and prompt-only baselines?

## Current scope

Primary task:

- **Grammatical Error Correction (GEC)**

Possible later extensions:

- Grammatical Error Detection (GED)
- Grammatical Error Explanation (GEX), if qualified linguistic evaluation becomes available

The project does not create new linguistic labels without qualified Arabic linguists. It relies on existing expert-written or expert-validated datasets.

## First milestone

Produce a reproducible baseline score from an untouched open model on the held-out **Nahw-Passage** benchmark.

> **Data rule:** `Nahw-Passage` is treated as evaluation data. It must not be used for training if results are reported on it.

### Run the untouched-model baseline

1. Open [`notebooks/01_nahw_baseline_unsloth.ipynb`](notebooks/01_nahw_baseline_unsloth.ipynb) with the Colab badge above.
2. In Colab, select **Runtime → Change runtime type → T4 GPU** (or another available GPU).
3. Run the notebook from top to bottom. The default pilot processes exactly the first 25 test records; the separate 511-record section is disabled by default.
4. Inspect the manual-review table, then download the files from `outputs/` or optionally copy them to Google Drive.

Free Colab GPU availability is not guaranteed. The workflow does not require Colab Pro, paid APIs, or paid storage.

> **Test-only warning:** Never train on Nahw-Passage or use its results to tune prompts, choose checkpoints, or make repeated model-selection decisions.

The pilot writes `outputs/baseline_pilot_predictions.jsonl` and `outputs/baseline_pilot_summary.json`. Generated outputs are ignored by Git.

## Repository structure

```text
.
├── data/
│   └── train.sample.jsonl
├── docs/
│   ├── collaboration_workflow.md
│   ├── dataset_audit.md
│   ├── experiment_naming.md
│   ├── literature_matrix.md
│   ├── papers.md
│   ├── prompt_baseline_protocol.md
│   └── research_plan.md
├── notebooks/
│   └── 01_nahw_baseline_unsloth.ipynb
├── results/
│   ├── b0_full_baseline_audit.md
│   ├── b1_b2_prompt_baseline_validation.md
│   ├── prompt_inference_core_validation.md
│   └── qalb_0.9.1_intake.md
├── scripts/
│   ├── baseline_prompts.py
│   ├── download_nahw.py
│   ├── inspect_nahw.py
│   ├── nahw_baseline_utils.py
│   ├── prepare_b1_prompt_bundle.py
│   ├── prepare_qalb_manifests.py
│   ├── prepare_nahw_eval.py
│   ├── run_gemma3_nahw_baseline.py
│   ├── run_prompt_baseline.py
│   └── train_lora.py
├── tests/
│   ├── test_baseline_prompts.py
│   ├── test_inspect_nahw_cli.py
│   ├── test_nahw_baseline_utils.py
│   ├── test_prepare_b1_prompt_bundle.py
│   ├── test_prepare_nahw_eval_cli.py
│   ├── test_prepare_qalb_manifests.py
│   └── test_run_prompt_baseline.py
├── .github/
│   ├── ISSUE_TEMPLATE/
│   ├── workflows/
│   ├── CODEOWNERS
│   └── pull_request_template.md
├── .gitignore
├── README.md
└── requirements.txt
```

## Quick start

```bash
python -m venv .venv
```

Activate the environment:

```bash
# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

Install dependencies and prepare the benchmark:

```bash
pip install -r requirements.txt
python scripts/download_nahw.py
python scripts/inspect_nahw.py
python scripts/prepare_nahw_eval.py
```

### QALB private manifests

Registered QALB users may place the unchanged release ZIP at the ignored path `data/raw/qalb/QALB-0.9.1-Dec03-2021-SharedTasks.zip`, then run:

```bash
python scripts/prepare_qalb_manifests.py
```

The script reads the ZIP directly and writes corpus-text-free metadata and hashes under ignored `data/processed/qalb/`. It preserves within-split duplicates, excludes train/dev records with exact source overlap against QALB test or Nahw, and keeps every QALB test record evaluation-only. Never commit or redistribute the QALB release or these private outputs.

### B1-P1/B2-P1 prompt baseline scaffolding

The frozen prompt-only baselines are implemented as public scaffolding with private
data kept out of Git:

```bash
python -m unittest tests.test_baseline_prompts tests.test_prepare_b1_prompt_bundle tests.test_run_prompt_baseline -q
```

Licensed QALB users can generate the private B1 demonstration bundle only after
creating the text-free QALB manifests above:

```bash
python -m scripts.prepare_b1_prompt_bundle
```

The B1 bundle is text-bearing and is written under ignored `data/processed/qalb/`.
Do not print, commit, attach, or redistribute it. The command fails closed unless
the frozen structural checks match: 3,116 candidate annotations, 458 distinct
records, and selected identity SHA-256
`76edd4c3de4b6cb5a985464faa066dea40faf9b25b8fa2912b3bf9c4750a9e8c`.
By default, the bundle writer refuses output paths outside `data/processed/qalb/`;
the override flag is only for temporary local diagnostics and must not be used
for committed artifacts.

### QALB-development prompt validation input

Before any B1-P1/B2-P1 Nahw-Passage run, a licensed contributor can verify the
deterministic QALB-2014 L1 development selection without writing corpus text:

```bash
python -m scripts.prepare_qalb_dev_prompt_records
```

The default dry run selects 25 technically compatible single-token replacement
annotations and prints only corpus-text-free counts and hashes. It reads the
unchanged QALB ZIP and the private development-selection manifest directly; it
does not use QALB test or Nahw-Passage.

If the team's licensed-data handling procedure permits a temporary transformed
input, deliberately write it under the ignored private directory:

```bash
python -m scripts.prepare_qalb_dev_prompt_records --write-private-output
```

This creates `data/processed/qalb/qalb14_dev_prompt_records.jsonl` and refuses to
overwrite it. The file contains licensed QALB text: do not print, commit, attach,
or redistribute it. Delete or retain it according to the team's approved QALB
data-handling procedure after validation.

Canonical output directories for prompt-baseline runs use:

```text
outputs/<experiment-id>/predictions.jsonl
outputs/<experiment-id>/summary.json
outputs/<experiment-id>/run.log
```

`scripts/run_prompt_baseline.py` refuses to overwrite an existing run directory
and refuses `nahw-passage` unless `--confirm-final-eval` is passed deliberately.
Use QALB development for technical validation before any final Nahw-Passage run.

The private JSONL input contract is one object per line with `record_id`,
`passage`, and `error` strings. `gold_correction` may be a string or null, and
`metadata` may be an object. Keep this text-bearing file under ignored
`data/processed/` (or outside the repository). To create a hash-audited planned
run without loading a model:

```bash
python -m scripts.run_prompt_baseline \
  --protocol-id B2-P1 \
  --evaluation-slug qalb14-dev \
  --input data/processed/qalb/prompt_records.jsonl \
  --prompt-template docs/prompt_baseline_protocol.md
```

Execution is opt-in and requires a pinned Hugging Face revision. B1-P1 also
requires the private bundle created above; B2-P1 rejects a bundle:

```bash
python -m scripts.run_prompt_baseline \
  --protocol-id B1-P1 \
  --evaluation-slug qalb14-dev \
  --input data/processed/qalb/prompt_records.jsonl \
  --prompt-template docs/prompt_baseline_protocol.md \
  --bundle data/processed/qalb/b1_prompt_bundle.json \
  --model-revision <immutable-commit-sha> \
  --execute
```

Predictions contain private prompts and model responses and therefore remain
ignored under `outputs/`. The runner records input, template, bundle, prompt,
and prediction hashes plus runtime metadata. A failed inference keeps a partial
prediction file and marks the run `invalid`; reruns must use a new experiment ID.

Authenticate with Hugging Face if the selected model is gated:

```bash
huggingface-cli login
```

Run a small baseline:

```bash
python scripts/run_gemma3_nahw_baseline.py --limit 25
```

Predictions and metrics are written to `outputs/`.

## Planned experiments

The frozen `F1-P1` natural-data protocol is documented in
[`docs/f1_natural_pilot_protocol.md`](docs/f1_natural_pilot_protocol.md). Its
private QALB adapter defaults to a text-free validation run:

```bash
python scripts/prepare_f1_natural_records.py
```

Writing text-bearing records is deliberately disabled unless the user supplies
both `--write-private-records` and `--confirm-license-guidance`. Such outputs
remain under ignored `data/processed/`; never commit, print, or redistribute
them. This command does not train a model or access QALB test/Nahw results.

After the private adapter gate, import
[`notebooks/02_f1_natural_qlora.ipynb`](notebooks/02_f1_natural_qlora.ipynb) into
a free Kaggle Notebook, enable a GPU accelerator and Internet, and attach QALB
inputs only through a private Kaggle Dataset. Run cells in order. The notebook requires a deliberate
one-batch GPU smoke test with at least 1 GiB headroom before its separately
confirmed full-training cell can run. CPU is not a supported training fallback;
full training is disabled by default.

F1-P1 training, private development selection, and its single pre-registered
Nahw-Passage evaluation are now complete. The selected `checkpoint-250` reached
145/511 exact matches (28.38%), compared with 86/511 (16.83%) for untouched B0.
The independently checked, corpus-text-free result and important hardware/
reproducibility caveats are recorded in
[`results/f1_p1_final_evaluation_audit.md`](results/f1_p1_final_evaluation_audit.md).
Do not rerun or revise F1-P1 based on this test result.

The matched B0/F1-P1 overcorrection and general Arabic capability diagnostic is
complete. Its QALB-2015 development and balanced ArabicMMLU selections,
metrics, runtime, privacy rules, and execution gate were pre-registered in
[`docs/f1_capability_retention_protocol.md`](docs/f1_capability_retention_protocol.md).
F1-P1 showed better unchanged-token behavior than B0 on this diagnostic (50.65%
versus 27.92%); on the balanced ArabicMMLU subset it scored 53.1% versus 53.7%
for B0, with a paired interval spanning both loss and gain. See the cautious,
corpus-text-free audit in
[`results/f1_safety_diagnostics_audit.md`](results/f1_safety_diagnostics_audit.md).
Do not rerun these diagnostics or interpret the capability result as proof of
non-inferiority.

The next matched F2/F3 gate uses the authoritative Tibyan release rather than
the still-disabled project-generated XG operator. The frozen
[Tibyan F2/F3 protocol](docs/tibyan_f2_f3_protocol.md) defines a deterministic
highlighted-token alignment, exact-source group split, private QALB/Nahw
hash-overlap exclusions, a 2,000-record synthetic arm, and a nested 1,000-record
synthetic half for the 50:50 mixed arm. The canonical manifest build is recorded
without corpus text in
[the manifest audit](results/tibyan_f2_f3_manifest_audit.md). All 2,000 selected
records passed the pinned Gemma 1,024-token guard. The methodology and exact
compositions received GO at merged commit
`8ca3014e6b3659e2e8c3ffc519b0255e9af6b7a6`; this authorized guarded workflow
implementation only. The non-executing-by-default Kaggle workflow is
[`notebooks/04_f2_f3_qlora.ipynb`](notebooks/04_f2_f3_qlora.ipynb). A new
exact-commit GO is still required before a GPU smoke or full-training run. Do
not edit the Kaggle notebook to activate it. After GO, generate a strict,
text-free private activation file with:

```bash
python scripts/prepare_f2_f3_execution_config.py \
  --arm F2-P1 \
  --stage gpu-smoke \
  --approved-workflow-commit <40-character-commit> \
  --approval-reference <issue-69-comment-url> \
  --confirmation RUN_F2_F3_LONGEST_RECORD_SMOKE \
  --output data/processed/f2_f3_execution_configs/<run-name>/f2_f3_execution_config.json
```

Create a new directory for every authorized stage; the helper never overwrites
an existing config. Attach only the current file through a private Kaggle
Dataset. The notebook fails closed when the file is missing, duplicated,
malformed, or inconsistent with the selected stage. The config contains no
corpus text, but remains Git-ignored. No final-test evaluation is part of that
notebook.

Two approved F2-P1 smoke attempts have stopped at preflight without loading a
model or running an optimizer step. The current repair supports Kaggle's nested
`/kaggle/input/datasets/<owner>/<dataset>/...` mounts while retaining unique-
file and checksum gates. A fresh exact-commit GO on issue #69 is required
before another GPU attempt; no prior GO authorizes a retry.

1. Untouched-model zero-shot baseline
2. Prompt-only baselines
3. Natural-data LoRA/QLoRA fine-tuning
4. Synthetic-data LoRA/QLoRA fine-tuning
5. Mixed natural + synthetic fine-tuning
6. Held-out GEC evaluation
7. General Arabic capability-retention checks

See [`docs/research_plan.md`](docs/research_plan.md) for the full experimental design.
The registered run IDs are defined in
[`docs/experiment_naming.md`](docs/experiment_naming.md), and the frozen B0/B1/B2
prompt protocols are defined in
[`docs/prompt_baseline_protocol.md`](docs/prompt_baseline_protocol.md).

## Team workflow

Use the Musahhih Research Hub in Notion for roadmap and status, and GitHub issues
and pull requests for execution. Each active task should have one owner, one
branch, and one PR so human contributors and AI agents do not overwrite each
other. See [`docs/collaboration_workflow.md`](docs/collaboration_workflow.md).

## Foundation

This project builds on:

- [Nahw: A Comprehensive Benchmark of Arabic Grammar Understanding, Error Detection, Correction, and Explanation](https://aclanthology.org/2026.eacl-long.296/)
- [Official Nahw repository](https://github.com/qcri/nahw-arabic-grammar-benchmark)

## Status

Early research and baseline implementation. No model-performance claims are made yet.
