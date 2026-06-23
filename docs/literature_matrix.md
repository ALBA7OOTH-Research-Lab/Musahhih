# Literature Matrix

| Work | Main contribution | Data | Training / method | Evaluation | Limitation relevant to us |
|---|---|---|---|---|---|
| Nahw (2026) | Four-part Arabic grammar benchmark: GU, GED, GEC, GEX | 5K natural MCQs; 100 passages with 511 errors; 10K synthetic MCQs | Fine-tunes Gemma-3-4B-it only for GU | Accuracy, F1, correction accuracy, expert GEX ratings | Improvement experiment centers on MCQ grammar understanding, not a full fine-tuned GEC system |
| Beyond English (2023) | Evaluates prompted LLMs and fully fine-tuned models for Arabic GEC | QALB-2014 and QALB-2015 | Prompting, few-shot/expert prompting, synthetic-data fine-tuning | QALB correction F1 | Focused on standard QALB data; not designed around Nahw's grammar hierarchy |
| Advancements in Arabic GED/GEC (2023) | Strong Arabic GED/GEC models and multitask experiments | QALB and ZAEBUC-related data | Arabic pretrained models, morphology, multitask setups | Shared-task metrics | Does not answer Nahw's natural-versus-synthetic extension using a modern open instruction model |
| QALB 2014/2015 | Standardized Arabic text-correction tasks | Native and non-native Arabic writing | Shared task, many systems | Official shared-task scorer | Error distribution is heavily orthographic; grammar is not the dominant category |
| Tibyan | Large, balanced synthetic Arabic GEC corpus validated by linguists | Approximately 600K tokens; multiple error families | ChatGPT-assisted generation plus expert validation | Corpus analysis with ARETA | Synthetic artifacts and access/version details must be verified before use |
| ARETA | Automatic Arabic error-type annotation | Arabic learner/correction corpora | Rule/morphology-based automatic annotation | Error-type F1 | Useful for analysis, but automatic labels are not equivalent to expert gold labels |

## Candidate gap

Nahw demonstrates that open models are weak on practical Arabic grammar and shows that fine-tuning helps GU. It explicitly leaves GED, GEC, and GEX fine-tuning as future work. A focused extension is to fine-tune an open model for **GEC**, compare natural, synthetic, and mixed training data, test on held-out Nahw-Passage and standard GEC benchmarks, and measure whether general Arabic capabilities are retained.
