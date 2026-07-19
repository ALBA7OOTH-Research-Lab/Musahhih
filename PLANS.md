# Active implementation plan

## Issue #65 — execute matched F1 safety diagnostics

- [x] Record project-owner GO for merged protocol commit
  `45fd0640184af7e14abd99124e75923623d770c5`.
- [x] Create a separate execution issue with exact inputs, hashes, runtime,
  run ID, approval, privacy, and retry rules.
- [x] Verify private Kaggle inputs and run the evaluator without `--execute`.
- [x] Execute the single matched B0/F1-P1 P100 run exactly once if preflight
  passes; preserve any failure as required by the frozen protocol.
- [x] Download private artifacts and independently recompute hashes, alignment,
  counts, paired statistics, and safeguards without logging corpus text.
- [x] Commit a corpus-text-free result audit, run repository validation, open a
  result PR, merge it, and synchronize GitHub and Notion.

Do not use Nahw-Passage or QALB test, and do not train, tune, select, merge,
retry from a score, or activate XG/F2/F3 in this task.
