# MRL 2026 manuscript-draft audit

Date reviewed: 2026-07-29

## Outcome

Issue #149 produced the first anonymous ACL-format manuscript draft for the
6th Multilingual Representation Learning Workshop at EMNLP 2026:

- source: `paper/main.tex`;
- bibliography: `paper/references.bib`;
- corpus-text-free figure source:
  `scripts/generate_paper_figures.py`; and
- corpus-text-free training-token analysis:
  `scripts/summarize_training_token_budgets.py` and
  `results/training_token_budget_summary.json`; and
- generated review PDF:
  `output/pdf/musahhih-mrl-2026-anonymous-draft.pdf` (ignored, local).

This is an author-review draft, not a submitted or accepted paper. It contains
no author names, affiliations, acknowledgements, identifying repository links,
private corpus text, record-level predictions, model responses, private logs,
checkpoints, adapters, or credentials.

## Format checks

- The MRL 2026 call requires the EMNLP 2025 paper format, anonymized research
  papers of either four or eight content pages excluding references, and one
  additional content page only for accepted camera-ready papers. The draft is
  prepared as a long research paper.
- Official ACL style files were pinned from `acl-org/acl-style-files` commit
  `d5adc823ff0f80f98c80405ca0ab66c68e684409`.
- Two behavior-neutral trailing spaces were removed from the upstream
  bibliography style for repository diff hygiene.
- Review mode produces A4, two-column output with line numbers.
- The abstract contains 172 words, below the 200-word limit.
- The compiled PDF contains seven pages; references begin on page six.
- No overfull box, undefined control sequence, unresolved citation, unresolved
  reference, or LaTeX error appears in the final build log.
- PDF metadata contains no author or lab identity.
- All seven pages were rendered to PNG and visually checked for clipped text,
  overlap, broken tables, unreadable labels, missing glyphs, and float-layout
  defects.
- The required `Limitations` section and optional `Ethical Considerations`
  section occur after the conclusion and before the references, following the
  EMNLP/ARR page-count convention.
- The paper contains no author names, affiliations, acknowledgements,
  deanonymizing repository links, or identifying self-references.

The draft remains below the MRL long-paper limit of eight content pages plus
references. The final workshop template and submission form must be rechecked
before upload because venue instructions may change.

## MRL 2026 submission compliance review

The official workshop call and live OpenReview configuration were rechecked on
2026-08-02.

| Requirement | Status | Evidence |
|---|---|---|
| Research-paper track | Pass | The draft reports completed, original experimental work and is prepared as a long paper rather than a two-page extended abstract. |
| Workshop scope | Pass | The study evaluates adaptation of an open multilingual model to an under-studied, morphologically rich language and directly studies training data composition. |
| Content length | Pass | The conclusion ends on page 6, below the eight-page long-paper limit; Limitations, Ethical Considerations, and references follow. |
| Review template | Pass | The PDF uses the pinned official ACL review style in A4, two-column, line-numbered form. |
| Anonymity | Pass | The PDF and metadata contain no author, affiliation, acknowledgement, lab name, deanonymizing link, or identifying self-reference. |
| Abstract | Pass | 172 words, below the ACL 200-word maximum. |
| Required Limitations section | Pass | A dedicated section titled `Limitations` occurs after the conclusion and before the references. |
| Ethical discussion | Pass | The optional `Ethical Considerations` section follows Limitations and precedes the references. |
| PDF upload constraint | Pass | The rebuilt PDF is approximately 141 KiB, below the live form's 50 MB maximum. |
| Submission deadline | Recorded | The workshop states 2026-08-10 at 23:59 AoE; the live OpenReview deadline encodes 2026-08-11 11:59 UTC. |
| Camera-ready allowance | Not yet applicable | Accepted research papers receive one additional content page. |

The current regular-paper OpenReview form requests title, author profiles,
keywords, an optional TL;DR, abstract, and one PDF, and assigns CC BY 4.0. It
does not currently expose a supplementary-material upload field. Recheck the
live form immediately before submission rather than assuming a separate
anonymous archive can be attached.

## Evidence and claim checks

The manuscript's empirical values are traceable to:

- `results/b1_p1_final_evaluation_audit.md`;
- `results/b2_p1_final_evaluation_audit.md`;
- `results/f1_p1_final_evaluation_audit.md`;
- `results/f2_f3_final_evaluation_audit.md`;
- `results/f1_safety_diagnostics_audit.md`; and
- the F1/F2/F3 corpus-text-free training summaries.

The manuscript presents F3-P1 minus F2-P1 as the sole pre-specified primary
contrast. It labels comparisons involving B1, B2, or F1 as staged, does
not claim F3-P1 superiority over F1-P1, does not claim general capability
retention, and does not claim expert linguistic validation or state of the
art.

The historical B0-P1 Nahw evaluation and every comparison derived from it were
removed from the manuscript because that run alone used T4 hardware. Every
displayed final-evaluation system now used P100 hardware. The B0 control in the
retained F1 safety section is a separate artifact regenerated beside F1-P1
within one matched P100 run; it is not the excluded T4 result.

The reviewer-response revisions add corpus-text-free clarifications:

- the primary paired interval remains conditional on seed 3407, while the
  completed post-hoc five-seed cohort reports every seed, arm means and sample
  standard deviations, and paired-difference mean, spread, and range;
- the exact post-hoc first-token sensitivity rescues 0/20 flagged F2-P1
  outputs and 0/2 flagged F3-P1 outputs, leaving both scores and the primary
  difference unchanged;
- the frozen common-development rule selected F2-P1 epoch 1 after loss
  increased from 0.5975 to 0.6116 and F3-P1 epoch 2 after loss decreased from
  0.3730 to 0.3441;
- exact formatted-token totals are 312,644 for F1-P1, 522,756 for F2-P1, and
  416,746 for F3-P1 per epoch; and
- corresponding F2/F3 safety diagnostics remain absent and no comparison is
  claimed.

The related-work revision adds two primary-source-verified references: recent
Arabic data-derived text editing, whose method contribution is complementary
to this study's supervision-composition question, and contextual synthetic GEC
augmentation work documenting error-distribution mismatch and noisy labels.
The discussion now leads with the empirical result and consolidates repeated
protocol caveats without weakening the distinction between the primary and
secondary comparisons.

The paper uses ``pre-specified'' rather than ``preregistered'' for the primary
contrast. The protocol was committed and frozen before test access, but the
manuscript does not rely on a public registration record that anonymous
reviewers can independently inspect.

Across seeds 3407--3411, the post-hoc cohort gives F2-P1 mean 21.68% (sample
SD 0.71 points), F3-P1 mean 31.98% (SD 1.15), and mean paired difference
+10.29 points (SD 1.45; range +8.61 to +12.52). F3-P1 exceeds F2-P1 in every
seed. The manuscript keeps the original seed-3407 P100 run as primary and
labels the A100-training/RTX-3090-evaluation cohort as post-hoc robustness
evidence.

The separately authorized first-token audit used the accepted private
seed-3407 prediction hashes and published only corpus-text-free aggregate
counts. It loaded no model, ran no inference, and did not change the parser or
primary result.

The token totals were computed from the byte-identical frozen private training
records with Transformers 4.56.2 and the pinned Gemma tokenizer revision.
The analysis loaded no model weights or test records, performed no training or
inference, and emitted only aggregate counts, distributions, and hashes. F2-P1
contains 25.4% more formatted tokens than F3-P1, so greater token exposure
cannot explain the primary F3-P1 advantage.

`results/research_results_consolidated.json` was updated to include the
accepted B1-P1 and B2-P1 final results and the reviewed staged comparisons used
by the manuscript figure.

## Citation checks

Every current bibliography entry was verified against a primary source:

- ACL Anthology records and DOIs for Nahw, Beyond English, the Arabic GED/GEC
  investigation, Arabic data-derived text editing, contextual GEC data
  augmentation, both QALB shared tasks, ARETA, ArabicMMLU, and AraT5;
- the official NeurIPS proceedings record and DOI for QLoRA; and
- official arXiv records and DataCite DOIs for Tibyan and Gemma 3.

No SciSpace-suggested or model-invented citation was accepted. Bibliography
expansion remains an author-review task; all additions require the same
primary-source verification.

## Validation

- `python -m pytest -q`: 304 tests, 78 subtests, and 2 expected skips passed
  after merging the current main branch.
- `python -m compileall scripts`: passed.
- pinned-tokenizer aggregate generation and idempotent rerun: passed.
- JSON parse of `results/research_results_consolidated.json`: passed.
- `git diff --check`: passed.
- Manuscript identifier/credential scan: no match.
- Final LaTeX compilation with Tectonic: passed.

## Remaining work before submission

- author and affiliation decisions;
- substantive author review of framing and interpretation;
- final artifact-availability wording, with an anonymous supplement only if
  the live workshop form later exposes a permitted upload field;
- final ACL policy and MRL OpenReview form review;
- camera-ready AI-assistance disclosure if the paper is accepted; and
- final proofreading by every listed author.

No additional training, inference, or benchmark access is required for this
manuscript draft.
