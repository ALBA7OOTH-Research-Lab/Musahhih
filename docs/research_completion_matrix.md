# Research completion matrix

Status reviewed: 2026-08-01

## Overall decision

The controlled natural-only, synthetic-only, and fixed mixed-data GEC
comparison is complete. The original broader research plan is partially
complete because safety
diagnostics cover F1-P1 but not F2-P1/F3-P1, qualified linguistic error
analysis has not occurred, release clearance is unresolved, and the manuscript
has not been written.

This distinction must remain visible in project status and any paper.

## Claim-by-claim status

| Research question or deliverable | Status | Evidence | Allowed conclusion | Missing work |
| --- | --- | --- | --- | --- |
| Reproducible untouched B0 baseline | Complete | `results/b0_full_baseline_audit.md` | The accepted B0 run achieved 86/511 exact matches on Nahw-Passage. | Do not rerun it to guide later design. |
| Natural-data fine-tuning versus B0 | Complete, staged comparison | `results/f1_p1_final_evaluation_audit.md` | F1-P1 improved exact-match accuracy by 11.55 points in the observed frozen runs. | None for this narrow comparison. |
| Synthetic-only versus mixed training | Complete, preregistered primary comparison | `results/f2_f3_final_evaluation_audit.md` | F3-P1 exceeded F2-P1 by 11.15 points; the frozen interval was 7.05–15.26 points. | None; never repeat because of the result. |
| Natural-only versus synthetic-only | Complete, staged secondary comparison | `results/f2_f3_final_evaluation_audit.md` | F1-P1 exceeded F2-P1 by 7.83 points in the observed runs. | Disclose that F1 results predated the F2/F3 companion freeze. |
| Mixed versus natural-only | Complete, staged secondary comparison | `results/f2_f3_final_evaluation_audit.md` | F3-P1 was 3.33 points higher, but the interval included zero; no difference is established. | Do not describe F3 as proven superior to F1. |
| Fine-tuning versus five-shot B1-P1 | Complete, staged comparisons | `results/b1_p1_final_evaluation_audit.md` | B1-P1 achieved 89/511. F1-P1 and F3-P1 exceeded B1-P1; no difference was established for F2-P1 versus B1-P1. | Do not rerun or tune from B1-P1. Disclose staged timing. |
| Fine-tuning versus expert-style B2-P1 | Complete, staged comparisons | `results/b2_p1_final_evaluation_audit.md` | B2-P1 achieved 108/511. F1-P1 and F3-P1 exceeded B2-P1; no difference was established for F2-P1 versus B2-P1. | Do not rerun or tune from B2-P1. |
| F1-P1 overcorrection | Complete diagnostic | `results/f1_safety_diagnostics_audit.md` | F1-P1 preserved already-correct selected tokens more often than B0. | Do not generalize to all correct Arabic text. |
| F1-P1 general Arabic capability retention | Complete diagnostic | `results/f1_safety_diagnostics_audit.md` | No measured ArabicMMLU difference was established; the interval was −3.2 to +1.9 points. | This is not a formal non-inferiority result. |
| F2-P1/F3-P1 overcorrection and capability retention | Not executed | Proposed issue-#104 protocol | No claim is currently allowed. | Review, freeze, implement, merge, and separately authorize a matched diagnostic. |
| F2-P1/F3-P1 multi-seed robustness | Training complete; evaluation incomplete and frozen for submission | `results/f2_f3_nautilus_multiseed_training_audit.md`; `docs/f2_f3_nautilus_multiseed_evaluation_protocol.md`; `results/f2_f3_nautilus_mps_canary_repair_audit.md` | All five paired A100 training Jobs completed both arms. The first evaluation attempt preserved 3,739/5,110 outputs but produced no metric. Batch 64 changed outputs; five ordinary batch-16 processes underutilized A100; MPS made repeated batch-16 outputs unstable in all five workers and still observed only 27.748% mean utilization. | Report no multi-seed accuracy or variance. Do not spend another pre-submission GPU run on this extension; revisit only under a new post-submission protocol. |
| Qualified error-type analysis | Blocked | `docs/arabic_error_taxonomy_sources.md` | Aggregate exact-match and output-format diagnostics only. | Qualified Arabic linguist, private-review procedure, provenance, and adjudication plan. |
| QALB official test performance | Not executed; optional | `docs/research_plan.md` | No QALB test claim is allowed. | License and scope decision plus a separately frozen protocol and authorization. |
| Reproducible code release | Partially complete | Public repository and passing tests | The current code and aggregate evidence are inspectable. | Add an explicit repository software license before representing the code as openly licensed. |
| Adapter release | Blocked | Private adapter hashes only | Reproducible artifact identity can be reported by hash. | Dataset/base-model/license and institutional review; F1/F3 include QALB-derived training. |
| Paper | Not started | This matrix and consolidated summary | A focused paper can be drafted around the completed core comparison. | Manuscript, tables, figures, references, authorship, and release decisions. |

## Hypothesis status

### H1: fine-tuning outperforms zero-shot and few-shot prompting

Partially supported. F1-P1 and F3-P1 exceeded B0-P1, B1-P1, and B2-P1.
F2-P1 was not established as different from B0-P1, B1-P1, or B2-P1.
B2-P1 exceeded B0-P1 and B1-P1.

### H2: natural data is more sample-efficient than synthetic data

Supported by the staged equal-size F1-P1 versus F2-P1 comparison. F1-P1
achieved 145/511 while F2-P1 achieved 105/511. Because the F1 result predates
the F2/F3 companion freeze, describe this as staged evidence rather than the
primary preregistered contrast.

### H3: mixed natural/synthetic training outperforms synthetic-only training

Supported by the preregistered primary comparison. F3-P1 achieved 162/511
versus F2-P1's 105/511, with a positive paired-bootstrap interval.

### H4: targeted GEC fine-tuning may affect overcorrection or capability

Answered only for F1-P1. F1-P1 reduced the measured overcorrection diagnostic
and showed no established ArabicMMLU change. No corresponding F2-P1/F3-P1
claim is allowed until a separately reviewed diagnostic is completed.

## Submission-scope decision

A focused submission can center on the completed matched supervision-source
comparison if it:

- presents F3-P1 versus F2-P1 as the primary preregistered result;
- presents B0/F1 comparisons as staged secondary evidence;
- does not claim superiority of F3-P1 over F1-P1;
- presents B1-P1 and B2-P1 comparisons as staged;
- does not claim F2-P1/F3-P1 capability retention;
- reports exact-match limitations and the absence of independent linguistic
  validation; and
- keeps private/restricted artifacts out of the public paper package.

Completing F2-P1/F3-P1 safety diagnostics would strengthen the
paper, but each is a new optional execution decision rather than a requirement
to accept the already completed core result.
