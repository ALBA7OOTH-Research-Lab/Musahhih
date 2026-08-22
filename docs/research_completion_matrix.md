# Research completion matrix

Status reviewed: 2026-08-22

## Overall status

The controlled highlighted-token Arabic GEC study is complete. The manuscript
reports the frozen primary comparison, staged baselines, post-hoc robustness
analyses, and matched auxiliary diagnostics. No further training or final-test
evaluation is required for the current research question.

## Claims and evidence

| Claim | Status | Public evidence | Allowed interpretation |
| --- | --- | --- | --- |
| Untouched-model baseline | Complete | `results/b0_full_baseline_audit.md` | B0 achieved 86/511 exact matches. |
| Five-shot baseline | Complete; staged | `results/b1_p1_final_evaluation_audit.md` | B1 achieved 89/511. |
| Expert-style baseline | Complete; staged | `results/b2_p1_final_evaluation_audit.md` | B2 achieved 108/511. |
| Natural-only fine-tuning | Complete; staged | `results/f1_p1_final_evaluation_audit.md` | F1 achieved 145/511. |
| Mixed versus synthetic-only | Complete; primary | `results/f2_f3_final_evaluation_audit.md` | F3 achieved 162/511 versus F2's 105/511; the paired difference was +11.15 points (95% interval 7.05–15.26). |
| Mixed versus natural-only | Complete; staged | `results/f2_f3_final_evaluation_audit.md` | The +3.33-point interval included zero; superiority is not established. |
| Five-seed robustness | Complete; post-hoc | `results/f2_f3_rtx3090_multiseed_aggregate_audit.md` | F3 exceeded F2 in all five seeds; the mean paired difference was +10.29 points (SD 1.45). |
| Fixed-checkpoint sensitivity | Complete; post-hoc | `results/f2_f3_fixed_checkpoint_sensitivity_audit.md` | F3 exceeded F2 at both matched epochs. Development selection amplified but did not create the direction. |
| First-token sensitivity | Complete; post-hoc | `results/f2_f3_first_token_sensitivity_audit.md` | First-token extraction rescued none of the flagged F2 or F3 outputs; primary scores were unchanged. |
| Behavioral diagnostics | Complete; auxiliary | `results/f1_safety_diagnostics_audit.md`, `results/f2_f3_safety_diagnostics_audit.md` | The systems show a narrow overcorrection/capability trade-off; this is not a broad safety claim. |

## Remaining limitations

- One model family and parameter scale were studied.
- The three training views have equal record counts but different token counts,
  domains, error distributions, and source quality.
- Exact-match accuracy uses one reference and gives no credit to other valid
  Arabic corrections.
- No qualified linguist reviewed the private model outputs, so the paper makes
  no error-type or expert-quality claims.
- B0, B1/B2, F1, and the primary F2/F3 contrast were completed at different
  stages. Only the simultaneously evaluated F3–F2 contrast is primary.
- Restricted data and record-level outputs cannot be redistributed, limiting
  public end-to-end replication.

## Publication boundary

The paper may report the aggregate results above, corpus-free hashes, model and
checkpoint identities, prompts, data-selection rules, and decoding settings.
It must not publish restricted corpus text, benchmark questions, record-level
predictions, raw responses, adapters, checkpoints, private logs, or blinded
development metrics.

Qualified linguistic analysis, an additional model family, a second training
size, or a separately licensed benchmark would extend the study; none is a
missing prerequisite for the completed core comparison.
