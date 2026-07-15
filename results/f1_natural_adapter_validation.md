# F1-P1 natural-record adapter validation

Date: 2026-07-15

The privacy-guarded adapter completed a text-free dry run against the team's
unchanged, licensed QALB 0.9.1 archive and verified private manifests. It did not
write model-facing records, load a model, run inference, or train.

| Check | Result |
| --- | --- |
| Registered archive SHA-256 | `c14764b01439618bdcebda04bd5b9365cd70a1fbc58607f1bd18cf357514e503` |
| Training manifest SHA-256 | `9c9a054120d884a26d1b700501020452211df7b24de7e64476615d4a85d5dca2` |
| Development manifest SHA-256 | `563b12a75789ce0865ab341614935d855ab42086fae6e0cdaa26ba17f4de26c8` |
| Frozen training records selected | 2,000 |
| Eligible development records | 975 |
| Training selection SHA-256 | `03588f135e82575f8de9030b948d6b59cd14e3ca9c218207b0f33885d1f8e2d1` |
| Development selection SHA-256 | `510d81f828d1a58d62ea73615cdde09831adab1c84abfd01d79d587c6192fcbe` |
| Corpus text written or printed | No |

The adapter excluded 561 training-manifest rows and 157 development-manifest
rows under the frozen document predicates. Among remaining documents, 633
training rows and 39 development rows had no eligible annotator-0 single-token
substitution. These are mechanical eligibility counts, not linguistic-category
statistics or expert validation.

QALB test and Nahw-Passage remained evaluation-only. Text-bearing output remains
disabled unless the operator deliberately supplies both private-write and
license-guidance confirmation flags.
