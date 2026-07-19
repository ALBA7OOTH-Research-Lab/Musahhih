# Active implementation plan

## Issues #59 and #61 — freeze and execute F1-P1 selected-adapter evaluation

- [x] Confirm the selected checkpoint, immutable base revision, adapter hashes,
  accepted B0 settings, and Nahw-Passage checksum.
- [x] Write the pre-registered evaluation and retry protocol.
- [x] Add a fail-closed adapter evaluator and paired-comparison utilities.
- [x] Test all gates with synthetic fixtures only and validate the selected
  adapter's text-free config/selection hashes against the private audit copy.
- [x] Run repository validation and open pull request #60.
- [x] Obtain GO tied to merged commit
  `240ccfe0ae6370e2b7003a41ff4b703390f6f831`.
- [x] Execute the single authorized 511-record run as Kaggle kernel version 1.
- [x] Independently recompute record alignment, hashes, counts, and paired
  statistics from the downloaded private predictions.
- [ ] Merge the corpus-text-free result audit and close issue #61.

No repeat run or test-driven protocol change is authorized.
