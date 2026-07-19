# F1-P1 selected-adapter final evaluation audit

Date reviewed: 2026-07-19

## Accepted result

The single pre-registered F1-P1 run completed all 511 unique Nahw-Passage
correction records with the selected private `checkpoint-250`. It produced 145
exact matches:

- F1-P1 exact-match accuracy: `145 / 511 = 0.2837573385518591` (28.38%)
- untouched B0 exact-match accuracy: `86 / 511 = 0.16829745596868884` (16.83%)
- paired absolute difference, F1-P1 minus B0: `0.11545988258317025`
  (11.55 percentage points)
- invalid or empty responses: 0
- parsing failures: 0
- suspicious/multi-token outputs: 2

This is an actually executed model result, not an estimate. No prompt, parser,
checkpoint, decoding setting, or training record was changed after test access.
There was no adapter test pilot and no repeat final run.

## Frozen paired comparison

Among the 511 aligned records, F1-P1 corrected 81 records that B0 missed, while
B0 corrected 22 records that F1-P1 missed. The pre-registered paired analyses
were recomputed from the downloaded predictions:

- exact two-sided McNemar p-value: `4.06692891792894e-09`
- deterministic 10,000-sample paired-bootstrap 95% percentile interval for the
  accuracy difference: `[0.07827788649706457, 0.15264187866927592]`
- bootstrap seed: 3407

Under this frozen protocol, the selected natural-data adapter improved exact
word correction over the observed untouched B0 run on Nahw-Passage. This does
not establish expert-level Arabic ability, validate linguistic error labels, or
replace the planned synthetic/mixed and capability-retention experiments.

## Artifact and protocol identity

- run ID: `F1-P1__gemma3-4b-it__nahw-passage__s3407__r01`
- Kaggle kernel: `univverssal/musahhih-f1-p1-final-evaluation`, version 1
- approved repository commit: `240ccfe0ae6370e2b7003a41ff4b703390f6f831`
- model revision: `316726ca0bd24aa323bfaf86e8a379ee1176d1fe`
- adapter config SHA-256: `db19ef8bf4852698103dde20cd50b4429ca102ac96980f7939ecc4cff2049c4d`
- checkpoint-selection SHA-256: `898c19d5dcead1f6c8f0ed27b6e8c5c6b9ebaec2f1b2a9909e58d8c9758ee123`
- prepared test SHA-256: `acb3cfd204b35d5415532fbd32a4a5231b553fae329ab8f48e8454609e10279b`
- accepted B0 predictions SHA-256: `6997b6fe5959f5502511ebdd1885d05a89ebaefeb27eefb73520842598f36ebc`
- F1-P1 predictions SHA-256: `8c4d0ca25b48776a08ea02984af6c5c3ec0bc830d2d1a6994e0fb5eef995faa3`
- private run summary SHA-256: `00cba506eec598bfb5168a0dfb26744a882bb058d5b36c97558625b4fa77b979`
- decoding: greedy (`do_sample=false`), temperature not passed,
  `max_new_tokens=32`, seed 3407

The downloaded private artifact was independently checked for 511 unique IDs,
exact alignment with the frozen prepared records, field preservation, prediction
hash, recomputed exact-match counts, and exact reproduction of both paired
statistics. Raw responses and record-level test data remain under ignored
`outputs/` and are not committed.

## Reproducibility and interpretation caveats

F1-P1 ran on a Tesla P100 while the accepted B0 run used a Tesla T4. Both used
the same model revision, 4-bit loading, prompt, parser, decoding settings, and
test file, but hardware-specific generation differences cannot be ruled out.
The accepted B0 audit also records one non-byte-identical greedy response across
its pilot and full run. Therefore the paired comparison describes the two frozen
observed runs; it is not proof of byte-identical generation across hardware.

Exact-word match is deliberately strict and does not measure alternate valid
corrections unless they equal the supplied gold string. The two suspicious
multi-token responses were retained as produced; the parser did not alter them
to improve the score. No expert linguistic review was performed or claimed.

## Decision

Accept F1-P1 as evidence that the selected natural-data feasibility adapter
outperformed untouched B0 on the frozen Nahw-Passage exact-match evaluation.
Close the F1-P1 execution task without a repeat run. Future decisions must use
development data and pre-registered protocols, not these final test outputs.
