# Musahhih

Musahhih is a controlled study of supervision composition for Modern Standard
Arabic grammatical error correction (GEC) with an open-weight language model.
It compares natural, synthetic, and 50:50 mixed training data while keeping the
model, record count, training recipe, prompt interface, and final test fixed.

The manuscript is in [`paper/`](paper/README.md). The repository contains the
corpus-text-free code and aggregate evidence needed to inspect the study; its
restricted datasets, model outputs, adapters, checkpoints, and private logs are
not published.

## Main result

Gemma 3 4B was fine-tuned with QLoRA on three 2,000-record views and evaluated
on the same 511 highlighted-token Nahw-Passage records.

| System | Supervision or setting | Exact-match accuracy |
| --- | --- | ---: |
| B1 | five-shot prompting | 17.42% |
| B2 | expert-style prompting | 21.14% |
| F1 | natural-only fine-tuning | 28.38% |
| F2 | synthetic-only fine-tuning | 20.55% |
| F3 | 50:50 mixed fine-tuning | **31.70%** |

The pre-specified primary comparison is F3 minus F2: **+11.15 percentage
points**, with a 95% paired-bootstrap interval of **7.05 to 15.26 points**.
The mixed-minus-natural interval includes zero, so the study does not establish
that F3 is better than F1.

A separate five-seed robustness cohort preserves the mixed-over-synthetic
direction in every seed. Fixed-checkpoint analyses show the same direction at
both epochs, although natural-development checkpoint selection increases the
measured gap. Auxiliary diagnostics expose a trade-off: F2 changes fewer
already-correct tokens, while F3 scores higher on the selected ArabicMMLU
subset.

## Repository layout

```text
paper/       LaTeX manuscript, bibliography, ACL style, and figures
docs/        study design, dataset audit, and frozen evaluation protocols
results/     reviewed corpus-free summaries used by the manuscript
scripts/     data preparation, training, evaluation, and analysis code
notebooks/   three executable experiment notebooks
tests/       lightweight regression and privacy-boundary tests
data/        public schema/example files only; restricted data are ignored
```

Start with:

- [`paper/main.tex`](paper/main.tex) for the manuscript;
- [`docs/research_plan.md`](docs/research_plan.md) for the experimental design;
- [`docs/dataset_audit.md`](docs/dataset_audit.md) for dataset roles and leakage controls;
- [`results/research_results_consolidated.json`](results/research_results_consolidated.json) for the aggregate values behind the paper; and
- [`results/README.md`](results/README.md) for the evidence index.

## Reproducing the public package

Create an environment and install the public dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
```

Regenerate the paper figures from the consolidated aggregate summary:

```bash
python scripts/generate_paper_figures.py
```

Build the manuscript with XeTeX-compatible `tectonic`:

```bash
tectonic paper/main.tex --outdir paper/build
```

Run the public regression suite:

```bash
python -m compileall -q scripts tests
python -m unittest discover -s tests -q
```

The pinned Nautilus training environment is recorded separately in
[`requirements-nautilus.txt`](requirements-nautilus.txt). Recreating the
private experiments additionally requires lawful access to the upstream
datasets and fresh execution authorization; the commands above do not download
or expose restricted corpus text.

## Data and artifact boundaries

- **Nahw-Passage is test-only.** It was never used for training, prompting,
  checkpoint selection, or development.
- QALB text and QALB-derived records remain private under the applicable data
  terms.
- Tibyan should be obtained from its authoritative release rather than copied
  from this repository.
- ArabicMMLU questions, record-level predictions, raw responses, adapters,
  checkpoints, and private logs are not included.
- The repository publishes only code, protocols, aggregate statistics, and
  corpus-free hashes approved by the artifact audit.

See [`docs/artifact_release_audit.md`](docs/artifact_release_audit.md) for the
complete release matrix. This repository currently has no software license;
public visibility alone does not grant reuse rights.

## Citation

During anonymous review, cite the manuscript by title. Replace `Anonymous`
with the final author list after de-anonymization.

```bibtex
@inproceedings{anonymous2026musahhih,
  title     = {Natural, Synthetic, or Mixed Supervision for Open-Weight Arabic
               Grammatical Error Correction},
  author    = {Anonymous},
  booktitle = {Proceedings of the 6th Workshop on Multilingual Representation
               Learning},
  year      = {2026}
}
```

## References

- [Nahw: A Comprehensive Benchmark of Arabic Grammar Understanding, Error Detection, Correction, and Explanation](https://aclanthology.org/2026.eacl-long.296/)
- [The First QALB Shared Task on Automatic Text Correction for Arabic](https://aclanthology.org/W14-3621/)
- [Tibyan: Balanced and Comprehensive Error Coverage Corpus Using ChatGPT for Arabic Grammatical Error Correction](https://arxiv.org/abs/2411.04588)
- [Gemma 3 Technical Report](https://arxiv.org/abs/2503.19786)
- [ArabicMMLU: Assessing Massive Multitask Language Understanding in Arabic](https://aclanthology.org/2024.findings-acl.334/)
