# Active implementation plan

## Issue #67 — freeze Tibyan-derived F2/F3 matched methodology

- [x] Re-verify the authoritative Tibyan archive/final-file hashes and compute a
  corpus-text-free eligibility/duplicate/length audit.
- [x] Define stable record IDs, exact-source connected groups, and a seeded
  Musahhih project split without calling it an official Tibyan split.
- [x] Run private exact-overlap checks against frozen QALB and Nahw registries;
  exclude any test-connected group from modeling eligibility.
- [x] Resolve matched `N`, F2/F3 composition, the common checkpoint-selection
  rule, seeds, budgets, metrics, privacy, attribution, and retry rules.
- [x] Update the synthetic protocol and dataset/experiment documentation with
  aggregate-only evidence and guarded implementation acceptance criteria.
- [ ] Validate, open a methodology PR, obtain independent review and exact-
  commit GO, and synchronize GitHub and Notion before GPU work.

Do not train, generate synthetic records, run model inference, inspect final-test
results, or activate XG/F2/F3 in this task. Corpus text and private data remain
ignored; public artifacts contain only aggregate metadata and hashes.
