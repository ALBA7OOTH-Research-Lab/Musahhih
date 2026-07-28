# B1/B2 input-contract and executable-P100 preflight repair audit

## Scope

Issue #127 repairs the two pre-inference defects exposed by issue #125. The
exact implementation commit is
`cb65e2f3143179d34034b661116220a011ffdddd`.

This repair does not authorize Kaggle submission, model loading, private
inference, training, metrics, B2-P1, or a B1-P1 retry.

## Private-input contract

`run_prompt_baseline.load_prompt_records` now:

- continues to accept canonical `record_id`;
- deterministically treats the frozen prepared-Nahw `id` field as the record
  identity when `record_id` is absent;
- rejects empty or non-string identities;
- rejects rows where both fields exist but disagree; and
- preserves duplicate-ID rejection.

`scripts/check_b1_b2_private_input.py` requires the frozen input SHA-256 before
loading the schema and emits only aggregate contract evidence.

A local corpus-text-free validation of the exact ignored artifact passed:

- SHA-256:
  `acb3cfd204b35d5415532fbd32a4a5231b553fae329ab8f48e8454609e10279b`;
- records: 511;
- unique resolved record IDs: true; and
- corpus text printed: false.

The private input bytes and frozen order did not change.

## Executable CUDA preflight

`require_single_p100_runtime` still fails closed unless PyTorch reports CUDA,
exactly one device, and a P100. It now additionally allocates a tensor on
`cuda`, executes an addition and reduction, synchronizes the device, and checks
the scalar result. Any allocation, kernel-image, execution, synchronization,
or result failure becomes a corpus-free `RunSafetyError` before private-input
access.

This closes the discovery-only logic defect. It has synthetic coverage for a
successful operation and a P100 kernel-execution failure. It has not yet been
executed on Kaggle hardware; actual P100 compatibility remains unproven until a
separately authorized no-input runtime smoke passes.

## Validation

- `python -m compileall scripts tests`
- 31 focused tests plus 16 subtests passed
- 226 full-suite tests plus 65 subtests passed
- exact ignored-artifact contract validation passed without printing corpus
  text

The next permissible execution is a no-dataset, no-model P100 preflight smoke
under a fresh exact-commit owner GO after this repair is merged. A passing
smoke would still not authorize B1-P1 inference.
