# QALB-development prompt-input validation

Date: 2026-07-11

GitHub issue: https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/12

## Scope

The archive-backed preparation path selects technically compatible, single-token
QALB-2014 L1 development annotations for the frozen B1-P1/B2-P1 runner. The
default command is a dry run: it reads the unchanged licensed archive and the
existing private development-selection manifest but writes no corpus text.

This adapter is for implementation validation only. It does not define a new
benchmark, change a frozen prompt, access QALB test, access Nahw-Passage, run a
model, or train an adapter.

## Licensed local dry run

Command:

```bash
python -m scripts.prepare_qalb_dev_prompt_records
```

Observed corpus-text-free metadata:

- QALB archive SHA-256: `c14764b01439618bdcebda04bd5b9365cd70a1fbc58607f1bd18cf357514e503`
- private development-manifest SHA-256: `563b12a75789ce0865ab341614935d855ab42086fae6e0cdaa26ba17f4de26c8`
- selected technical-validation records: 25
- selected record-identity SHA-256: `bef8240e7d45dd38d16c3af46601ad9ee3d5a21e50de8cddd194e284e25a7df8`
- skipped before reaching the limit: 22 non-single-token replacements and 9
  records whose erroneous token was not unique in its sentence
- text-bearing output written: no

The selection preserves archive order, requires an eligible QALB-2014 L1
development manifest row, verifies source hashes and archive member identity,
requires an unambiguous one-token replacement, and preserves source/error/gold
strings without Arabic normalization.

## Public validation

- `python -m compileall -q scripts tests`: passed.
- `python -m unittest tests.test_prepare_qalb_dev_prompt_records -q`: 3 passed.
- `python -m unittest discover -s tests -q`: 69 passed.
- `git diff --check`: passed.

Tests use synthetic ASCII fixtures. No QALB text is embedded in the test suite.

## Remaining gate

A licensed contributor must deliberately create the ignored private input only
if the team's QALB handling procedure permits that temporary transformed copy,
then run planned B1-P1/B2-P1 capture and GPU inference on QALB development. Keep
private prompts, predictions, and responses ignored. Nahw-Passage remains
unavailable until that technical gate passes.
