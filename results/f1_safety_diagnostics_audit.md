# F1-P1 matched safety-diagnostics audit

Recorded: 2026-07-19
Status: complete; independent record-level audit passed

## Result

The single pre-registered matched run completed on one private free Kaggle P100.
Both systems used fresh copies of the same immutable 4-bit base, the same
processor and package stack, and the same frozen records and scoring code.

On the 154-record QALB-2015 L2 development correct-input diagnostic:

- B0 returned the designated token unchanged on `43 / 154 =
  0.2792207792207792` (27.92%);
- F1-P1 returned it unchanged on `78 / 154 = 0.5064935064935064`
  (50.65%);
- the paired difference, F1-P1 minus B0, was
  `0.22727272727272727` (+22.73 percentage points);
- B0 changed/F1-P1 unchanged occurred 56 times, while B0 unchanged/F1-P1
  changed occurred 21 times;
- the exact two-sided McNemar p-value was
  `0.00008215921903007379`; and
- the frozen 10,000-sample paired-bootstrap 95% percentile interval was
  `[0.12337662337662338, 0.33116883116883117]` (+12.34 to +33.12 points).

Equivalently, the observed designated-token overcorrection rate was 72.08% for
B0 and 49.35% for F1-P1. F1-P1 also produced fewer suspicious responses (4
versus 9); neither system produced an empty response.

On the balanced 1,000-record ArabicMMLU capability subset:

- B0 answered `537 / 1000 = 0.537` (53.7%) correctly;
- F1-P1 answered `531 / 1000 = 0.531` (53.1%) correctly;
- the paired difference, F1-P1 minus B0, was `-0.006` (-0.6 points);
- B0 wrong/F1-P1 right occurred 83 times, while B0 right/F1-P1 wrong occurred
  89 times;
- the exact two-sided McNemar p-value was `0.7031386893685864`; and
- the frozen 40-task-stratified 10,000-sample paired-bootstrap 95% percentile
  interval was `[-0.032, 0.019]` (-3.2 to +1.9 points).

The ArabicMMLU result does not show a clear directional difference in this run.
It does **not** prove capability retention or non-inferiority: no non-inferiority
margin was registered, and the interval includes both loss and gain.

## Independent verification

The downloaded private JSONL files were audited without printing record text.
The audit independently verified:

- exactly 154 unique aligned overcorrection IDs and 1,000 unique aligned
  capability IDs for each system;
- every frozen input field, prompt, option list, answer, selected token, source,
  and split matched the corresponding private prepared record exactly;
- every stored ArabicMMLU prediction was the deterministic highest candidate
  logit, with the registered display-order tie rule;
- every unchanged-token outcome followed the frozen conservative parser and
  suspicious-output rule;
- all per-system counts, all 40 descriptive task accuracies, discordant counts,
  McNemar values, and bootstrap intervals were reproduced from raw predictions;
- both systems recorded identical processor token IDs, GPU, sequence length,
  quantization, Python, CUDA, and package metadata; and
- the run used approved commit
  `45fd0640184af7e14abd99124e75923623d770c5` and the recorded GO reference.

Private artifact hashes:

| Artifact | SHA-256 |
|---|---|
| B0 overcorrection predictions | `81fc3910d8012272d191389ed3547c6e9ed0d234beb39f2fd7ecb9db4d6ce6fd` |
| F1-P1 overcorrection predictions | `5ceb4fe380e9c957463f9521490a88381ae556709b48d82ee1ad761f13dac600` |
| B0 capability predictions | `95bd39db97d269b706b303551a332710d4c94e6e2c5f3683329118feb046a34a` |
| F1-P1 capability predictions | `222deeb7983f31b3cd8d8da400b724beeaf3c74b44db14256310da15bc3b93b0` |
| Private run summary | `78762c3541c6ffd71e10e2f4b00a8fac63533eac653cca0ffe4afbc4e3eed2b5` |

## Runtime and safeguards

- kernel: `univverssal/musahhih-f1-p1-safety-diagnostics`, version 1;
- GPU: Tesla P100-PCIE-16GB;
- base: `unsloth/gemma-3-4b-it-unsloth-bnb-4bit`, revision
  `316726ca0bd24aa323bfaf86e8a379ee1176d1fe`;
- adapter: private unmerged `checkpoint-250` with the frozen config and
  selection hashes;
- Python 3.12.13, CUDA 12.4, PyTorch 2.6.0+cu124, Transformers 4.56.2,
  Unsloth 2026.7.3, Accelerate 1.13.0, PEFT 0.19.1, and TRL 0.22.2.

No training, checkpoint selection, adapter merge, Nahw-Passage access, QALB
test access, prompt change, parser change, scoring change, or repeat run
occurred. All record-level artifacts remain private and ignored.

## Limitations and decision

The overcorrection diagnostic uses one mechanically selected token in each
gold-corrected learner sentence and the frozen correction prompt, which labels
that token as erroneous even though the expected behavior is to leave it
unchanged. It is not sentence-level grammatical validation, and the QALB target
may contain alternate or unannotated issues. No team member performed or claims
expert linguistic validation.

ArabicMMLU is a balanced subset rather than the full leaderboard benchmark,
possible base-model pretraining contamination is unknown, and the diagnostic
uses frozen next-token answer-letter logits. The 40 per-task rates are
descriptive because each task has only 25 selected questions.

Accept this run as the registered F1-P1 safety diagnostic. Do not repeat it or
use it to revise F1-P1. The next research gate is the synthetic/mixed study:
resolve its source, overlap, and qualified-linguistic-review requirements and
freeze F2/F3 before generating or training anything.
