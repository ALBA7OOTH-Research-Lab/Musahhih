# Results index

This directory contains reviewed, corpus-text-free evidence only. Private
predictions, prompts, model responses, checkpoints, adapters, and logs are not
published.

## Paper data

- [`research_results_consolidated.json`](research_results_consolidated.json):
  single machine-readable source for manuscript tables and figures.
- [`training_token_budget_summary.json`](training_token_budget_summary.json):
  formatted-token counts for the equal-record training views.

## Final evaluations

- [`b0_full_baseline_audit.md`](b0_full_baseline_audit.md)
- [`b1_p1_final_evaluation_audit.md`](b1_p1_final_evaluation_audit.md)
- [`b2_p1_final_evaluation_audit.md`](b2_p1_final_evaluation_audit.md)
- [`f1_p1_final_evaluation_audit.md`](f1_p1_final_evaluation_audit.md)
- [`f2_f3_final_evaluation_audit.md`](f2_f3_final_evaluation_audit.md)

## Robustness and diagnostics

- [`f2_f3_rtx3090_multiseed_aggregate_audit.md`](f2_f3_rtx3090_multiseed_aggregate_audit.md)
- [`f2_f3_fixed_checkpoint_sensitivity_audit.md`](f2_f3_fixed_checkpoint_sensitivity_audit.md)
- [`f2_f3_first_token_sensitivity_audit.md`](f2_f3_first_token_sensitivity_audit.md)
- [`f1_safety_diagnostics_audit.md`](f1_safety_diagnostics_audit.md)
- [`f2_f3_safety_diagnostics_audit.md`](f2_f3_safety_diagnostics_audit.md)

## Data and training provenance

- [`qalb_0.9.1_intake.md`](qalb_0.9.1_intake.md)
- [`tibyan_dataset_intake.md`](tibyan_dataset_intake.md)
- [`tibyan_f2_f3_manifest_audit.md`](tibyan_f2_f3_manifest_audit.md)
- [`f2_f3_training_workflow_audit.md`](f2_f3_training_workflow_audit.md)
- [`f2_f3_nautilus_multiseed_training_audit.md`](f2_f3_nautilus_multiseed_training_audit.md)

JSON summaries beside these audits provide the corresponding exact counts,
hashes, and aggregate values. Historical failed-run and infrastructure-repair
records remain recoverable from Git history but are intentionally absent from
the publication-facing tree.
