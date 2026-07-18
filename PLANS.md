# Active implementation plan

## Issue #59 — freeze the F1-P1 selected-adapter evaluation

- [x] Confirm the selected checkpoint, immutable base revision, adapter hashes,
  accepted B0 settings, and Nahw-Passage checksum.
- [x] Write the pre-registered evaluation and retry protocol.
- [x] Add a fail-closed adapter evaluator and paired-comparison utilities.
- [x] Test all gates with synthetic fixtures only and validate the selected
  adapter's text-free config/selection hashes against the private audit copy.
- [ ] Run repository validation, open a pull request, and request an independent
  GO/NO-GO review tied to the merged commit.

This task must not execute model inference on Nahw-Passage.
