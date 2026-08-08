# Qualified professor manuscript-review audit

Date resolved: 2026-08-08

## Scope

Issue #206 incorporates the written and embedded annotations supplied by a
professor of Arabic on the anonymous MRL 2026 manuscript. The reviewed PDF has
SHA-256
`e40c538f2840faf4e809e5e27fbaf953d86f437705fd80f12c759cf4d73b1c51`.
This was a manuscript review, not a review of private predictions. It therefore
does not authorize linguistic error labels or an expert-quality claim about
model outputs.

## Resolutions

| Review point | Manuscript resolution |
|---|---|
| Abstract is overloaded with statistics and implementation details | Rewritten around the problem, controlled method, three headline system results, principal conclusion, behavioral trade-off, and scope limits. Confidence intervals, p-values, seed variance, and checkpoint details remain in later sections. |
| Define the model terminology | Introduces “large language models (LLMs)” and consistently describes Gemma as an open-weight instruction-tuned LLM. |
| Explain the task for the reader | Adds an explicitly author-created Arabic highlighted-token example with an English translation and clarifies that the model returns only the replacement token. No restricted corpus example is reproduced. |
| Give datasets their own section and table | Renames the section, adds release source/reference/size/study-use columns for QALB 2014, Tibyan, Nahw-Passage, QALB 2015 L2 development, and ArabicMMLU, and preserves split boundaries. |
| Explain why only Gemma 3 4B is used | Adds a model-choice subsection covering open weights, multilingual instruction tuning, Arabic task support, 4-bit QLoRA feasibility on a free 16 GB GPU, experimental control, and the resulting generalization limit. |
| Show behavior across fine-tuning/checkpoints | Adds a corpus-text-free plot of the original F1/F2/F3 development loss at epochs 1 and 2, marking the checkpoint selected by the frozen rule. The existing fixed-checkpoint test sensitivity remains in the results. |
| Resolve “Exact Match” versus “Accuracy” | Defines the single task metric as exact-match accuracy (EM), explains its percentage interpretation and normalization boundary, changes the main table header to `EM (%)`, and distinguishes ArabicMMLU multiple-choice accuracy. |
| Consolidate technical and GPU details | Adds one implementation-and-hardware subsection, removes repeated hardware statements from result captions and diagnostics, and replaces the visible frozen-input hash with a pointer to the public audit. Methodologically necessary hash-based sampling and overlap checks remain. |
| Explain staged comparisons | Adds the actual timeline: F1 preceded the Tibyan study, F2/F3 formed the simultaneous primary contrast, and B1/B2 were later prompt-only baselines. It explains why the one-access policy precluded a cosmetic rerun. |
| Explain private-artifact verification | Clarifies that licensed custodians can recompute aligned aggregates with the public code, hashes establish audited identities, and hashes do not reveal rows or permit unlicensed rescoring. |
| Summarize prompts and use consistent prompt terminology | Replaces “prompt engineering/selection” with “prompt design,” reproduces the exact non-corpus Arabic instructions and English meaning, explains B1’s five-demo structure and B2’s no-demo structure, and withholds restricted inserted examples/passages. |
| Strengthen quantitative related work | Adds representative QALB-2014 M2 F0.5 results from the verified Kwon et al. study and explicitly warns that full-sentence edit scores are not comparable to token exact-match accuracy. |

## Privacy and claim boundary

The new Arabic task illustration is author-created and is not copied or
adapted from QALB, Nahw, Tibyan, ArabicMMLU, or any private prediction. The
paper still states that no qualified linguist reviewed the private model
outputs and makes no expert linguistic error-analysis claim. No training,
inference, benchmark access, metric recomputation, checkpoint selection,
prompt/parser change, or diagnostic was run for this revision.
