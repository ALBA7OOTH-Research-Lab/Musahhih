# Active implementation plan

## Issue #63 — F1 capability-retention and overcorrection protocol

- [x] Close the completed F1-P1 final-evaluation issue and merge its
  corpus-text-free audit.
- [x] Audit current official ArabicMMLU source, license, task format, revision,
  and split counts.
- [x] Identify a QALB development-only correct-input construction independent
  of the F1 checkpoint-selection split.
- [x] Freeze dataset selection, prompts, metrics, matched runtime, and retry
  rules in `docs/f1_capability_retention_protocol.md`.
- [x] Add deterministic preparation/evaluation utilities and synthetic tests.
- [ ] Validate, open a pull request, and obtain GO/NO-GO tied to its merged
  commit before any model inference.

Nahw-Passage and QALB test must not be accessed by this task. XG remains
disabled pending qualified linguistic review.
