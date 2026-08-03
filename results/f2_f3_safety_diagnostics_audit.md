# F2/F3 behavioral-diagnostics terminal audit

Recorded: 2026-08-03

Status: complete; the single issue-#200 execution authorization is consumed

## Outcome

The authorized private Kaggle kernel
`thgh15/musahhih-f2-f3-safety-06c27f2-r01` version 1 reached
`COMPLETE`. An independent local, CPU-only audit then verified the frozen
inputs, original selected adapters, immutable B0/F1 references, all 2,308 new
F2/F3 prediction rows, row alignment, schemas, runtime identity, hashes, and
every reported aggregate without printing corpus text or model responses.

The new evidence shows a trade-off rather than one supervision composition
dominating both diagnostics:

| System | Already-correct token unchanged (154) | ArabicMMLU correct (1,000) |
| --- | ---: | ---: |
| B0, staged reference | 43/154 (27.92%) | 537/1,000 (53.7%) |
| F1-P1, staged reference | 78/154 (50.65%) | 531/1,000 (53.1%) |
| F2-P1, synthetic-only | 97/154 (62.99%) | 487/1,000 (48.7%) |
| F3-P1, mixed | 35/154 (22.73%) | 540/1,000 (54.0%) |

For the primary new F3-minus-F2 comparison, unchanged-token accuracy was
40.26 percentage points lower for F3 (95% paired-bootstrap interval
-49.35 to -31.17 points; 6 F2-wrong/F3-right versus 68
F2-right/F3-wrong; exact McNemar p = 2.14e-14). Equivalently, F3
overcorrected the selected already-correct token substantially more often.

On the balanced ArabicMMLU subset, F3 exceeded F2 by 5.30 points (40-task
stratified paired-bootstrap interval +3.10 to +7.60 points; 97
F2-wrong/F3-right versus 44 F2-right/F3-wrong; exact McNemar
p = 9.48e-6). Synthetic-only F2 therefore had the strongest resistance to
overcorrection in this diagnostic but the lowest measured general-capability
score, whereas mixed F3 retained substantially more capability but changed
already-correct selected tokens more often.

The staged references sharpen but do not broaden that conclusion. F2 preserved
the designated correct token more often than B0 (+35.06 points) and F1
(+12.34), while F3 was not established as different from B0 and preserved it
less often than F1 (-27.92). F2 scored below B0 (-5.00 points) and F1
(-4.40) on ArabicMMLU; F3 was not established as different from either staged
reference. These are auxiliary behavioral diagnostics, not a general safety,
non-inferiority, or expert linguistic evaluation.

## Recomputed identities

| Artifact | SHA-256 |
| --- | --- |
| Terminal public summary | `a25f3474e944f98b17455659ed43dc982f08bd9d825cae8bd61981859031c67b` |
| Terminal progress manifest | `1dc25bf9b5092e998f4b356aa53e6efc8f425271a0d7df3a365c22c33e4ada15` |
| F2 overcorrection predictions | `b122f1087028f2e53b083aed681f7abcfb0cd682255e57baf371b3265d217eca` |
| F2 capability predictions | `c311080bfc7d0bec2fc1c98d24e79cf70ff2893928736bf1e43bf7d5ced7c23d` |
| F3 overcorrection predictions | `22929b966de67e4f38569b0ff4b7be274f22327b26f73e65531d8bfb6cb6f823` |
| F3 capability predictions | `cd0332caf7d8850cb15a98e974b59f8a83fd8d540bec4c18cb353c8ac6953376` |

The exact corpus-text-free terminal summary is published as
`results/f2_f3_safety_diagnostics_summary.json`; its SHA-256 is the terminal
public-summary hash above. The audit also revalidated the frozen input and adapter hashes recorded in
`results/f2_f3_safety_diagnostics_gate_audit.md`. F2 used the original
unmerged `checkpoint-125` adapter and F3 the original unmerged
`checkpoint-250` adapter, both in 4-bit inference.

## Execution provenance

- executable commit: `06c27f28f3462106f820a2fb6c9d6b32277b4bfa`;
- owner GO: issue #200 comment `5159312293`;
- private source dataset:
  `thgh15/musahhih-f2-f3-safety-artifacts-06c27f2-r01`, version 1;
- private kernel: `thgh15/musahhih-f2-f3-safety-06c27f2-r01`, version 1;
- elapsed time: 14,077 seconds;
- accelerator: one `Tesla P100-PCIE-16GB`;
- Python 3.12.13, CUDA 12.4, PyTorch 2.6.0+cu124,
  Transformers 4.56.2, Unsloth 2026.7.3, Accelerate 1.13.0,
  PEFT 0.19.1, and TRL 0.22.2.

## Scope and privacy

No training, checkpoint selection or reselection, Nahw-Passage access, QALB
test access, new data selection, prompt/parser change, linguistic labeling, or
XG occurred. The kernel used per-row `fsync` and an atomic progress manifest.
The public summary contains no corpus text. Predictions, prompts, questions,
target tokens, raw responses, logits, logs, adapters, checkpoints, and private
source files remain in ignored/private storage.

The authorization is consumed. Do not rerun, retry, continue, or use these
diagnostic results to alter the frozen training or final-evaluation decisions.
