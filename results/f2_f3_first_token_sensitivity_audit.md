# F2/F3 first-token sensitivity audit

Date reviewed: 2026-08-02

## Outcome

The single authorized issue-#190 CPU-only audit completed successfully without
retry. It evaluated the reviewer-suggested first-token counterfactual on only
the outputs already flagged `multiple_words`, applying the same rule to F2-P1
and F3-P1.

The counterfactual rescued **0 of F2-P1's 20** flagged outputs and **0 of
F3-P1's 2** flagged outputs. It harmed no originally correct output. Therefore:

- F2-P1 remains `105/511 = 20.55%`;
- F3-P1 remains `162/511 = 31.70%`; and
- F3-P1 minus F2-P1 remains `11.15` percentage points.

Under this exact post-hoc sensitivity, output-format compliance explains none
of the observed primary difference. The frozen primary parser and primary
scores remain unchanged.

## Artifact and execution identity

- executable repository commit:
  `9117d692e7f58810dbe6d974e50dddeed83bd70b`;
- owner authorization record:
  `https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/190#issuecomment-5156944153`;
- private F2-P1 prediction SHA-256:
  `ca4a6eb2f5e40a60be14f59cdc7365a0f327b41ab0b8f46c8a08c43cfb442753`;
- private F3-P1 prediction SHA-256:
  `ccb296e0f091bf28ebe4d7c8b9ed454934f4dade0b5793dcf1b3a5706379c35c`;
- ignored private summary SHA-256:
  `6eec6a4fd2c6b5ca87ce94af29631e8d2e67b1b5418f7f9f85dea6ba0f225586`;
- hardware: local CPU only; and
- number of attempts: one.

## Independent contract checks

Before computing the counterfactual, the audit verified both accepted file
hashes, 511 rows per arm, unique record identities, identical ordered F2/F3
alignment, stored exact-match values, the 105/162 original correct counts, and
the 20/2 `multiple_words` counts. The counterfactual used the first Unicode
whitespace-delimited token of the existing parsed correction and did not read
or change the primary parser.

The public summary contains no record ID, prompt, passage, source token, gold
correction, raw response, parsed response, or record-level warning.

## Safeguards and decision

No GPU, model loading, inference, training, checkpoint selection, repeat
evaluation, prompt change, parser change, QALB test, safety diagnostic,
linguistic labeling, or XG occurred. Private predictions remain ignored and
unpublished.

Accept this as post-hoc robustness evidence, replace the manuscript's
conservative worst-case bound with the exact zero-rescue result, and do not
rerun. The issue-#190 authorization is consumed.
