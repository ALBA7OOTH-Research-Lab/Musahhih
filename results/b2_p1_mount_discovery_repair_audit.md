# B2-P1 mount-discovery repair audit

Issue #145 removes the fixed Kaggle mount-path assumption that failed issue
#143. After the restored P100 gate passes, the generated wrapper now:

1. recursively lists only files named `nahw_gec_test.jsonl`;
2. requires exactly one candidate;
3. verifies its frozen SHA-256 before parsing; and
4. passes no B1 demonstration bundle.

It does not open or hash the separately attached B1 bundle. The model, prompt,
revision, seed, decoding, 34,200-second safe stop, per-row `fsync`, and atomic
progress contract are unchanged.

Synthetic/static tests verify recursive discovery, uniqueness, hash gating,
runtime-before-input ordering, absence of a fixed mount slug, and absence of a
bundle argument. No Kaggle submission, private corpus access, model load,
inference, or metric occurred.

Merging this repair does not authorize a B2 attempt. A future kernel requires
a fresh exact-commit owner GO.
