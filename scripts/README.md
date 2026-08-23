# Script entry points

- Data preparation: `prepare_nahw_eval.py`, `prepare_qalb_manifests.py`,
  `prepare_f1_natural_records.py`, `prepare_tibyan_f2_f3.py`, and
  `prepare_f2_f3_training_records.py`.
- Training: `train_lora.py` and `run_f2_f3_nautilus_pair.py`.
- Final evaluation: `run_gemma3_nahw_baseline.py`, `run_prompt_baseline.py`,
  `run_f1_adapter_eval.py`, and `run_f2_f3_final_eval.py`.
- Robustness: `run_f2_f3_nautilus_multiseed_eval.py`,
  `run_f2_f3_fixed_checkpoint_eval.py`, and the matching aggregate scripts.
- Behavioral diagnostics: `run_f1_safety_eval.py` and
  `run_f2_f3_safety_eval.py`.
- Paper artifacts: `generate_paper_figures.py`.

Commands that touch restricted inputs fail closed unless their frozen identity
and authorization requirements are satisfied. Public inspection and unit tests
do not require access to private corpus text.
