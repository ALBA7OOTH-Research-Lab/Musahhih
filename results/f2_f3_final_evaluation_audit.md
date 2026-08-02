# F2-P1/F3-P1 matched final-evaluation audit

Date reviewed: 2026-07-26

## Accepted result

The authorized timeout-safe continuation completed the frozen matched
Nahw-Passage evaluation. F2-P1 and F3-P1 each contain 511 unique, ordered test
records:

- F2-P1 exact-match accuracy: `105 / 511 = 0.2054794520547945` (20.55%);
- F3-P1 exact-match accuracy: `162 / 511 = 0.31702544031311153` (31.70%);
- primary paired difference, F3-P1 minus F2-P1: `0.11154598825831702`
  (11.15 percentage points);
- F2-P1 invalid/empty responses and parsing failures: 0; and
- F3-P1 invalid/empty responses and parsing failures: 0.

F2-P1 produced 20 multi-token warnings and F3-P1 produced 2. These outputs
were retained exactly as produced. This is an executed frozen-test result, not
an estimate. No prompt, parser, checkpoint, decoding setting, training data, or
experiment decision changed after test access.

A separately authorized post-hoc sensitivity later applied the first
whitespace-delimited token only to those already flagged outputs, symmetrically
for both arms. It rescued 0/20 F2-P1 outputs and 0/2 F3-P1 outputs, leaving both
scores and the 11.15-point difference unchanged. See
`results/f2_f3_first_token_sensitivity_audit.md`. This did not alter the frozen
parser or primary result.

## Frozen primary comparison

Among the 511 aligned records, F3-P1 corrected 89 records that F2-P1 missed,
while F2-P1 corrected 32 records that F3-P1 missed. The preregistered paired
analyses were reproduced exactly from the private predictions:

- exact two-sided McNemar p-value: `2.149916251790228e-07`;
- deterministic 10,000-sample paired-bootstrap 95% percentile interval:
  `[0.07045009784735812, 0.15264187866927592]`; and
- bootstrap seed: 3407.

Under this frozen exact-match protocol, the mixed natural/synthetic F3-P1
adapter outperformed the size-matched synthetic-only F2-P1 adapter on the
observed Nahw-Passage run.

## Staged secondary comparisons

The accepted B0 and F1-P1 results predated the frozen F2/F3 companion study.
They are therefore staged secondary comparisons, not part of a simultaneously
preregistered four-arm experiment:

| Comparison | Difference | 95% paired-bootstrap interval | Exact McNemar p |
| --- | ---: | ---: | ---: |
| F2-P1 minus B0 | `0.03718199608610567` | `[-0.007827788649706457, 0.0821917808219178]` | `0.12101372565511773` |
| F3-P1 minus B0 | `0.1487279843444227` | `[0.10763209393346379, 0.1898238747553816]` | `3.1933211380352095e-12` |
| F2-P1 minus F1-P1 | `-0.07827788649706457` | `[-0.12524461839530332, -0.03131115459882583]` | `0.0013699461049548254` |
| F3-P1 minus F1-P1 | `0.033268101761252444` | `[-0.003913894324853229, 0.07045009784735812]` | `0.09656519729770464` |

The intervals for F2-P1 minus B0 and F3-P1 minus F1-P1 include zero. These
results should not be described as evidence of a difference under the frozen
paired analysis. F3-P1 exceeded the observed B0 run, while F2-P1 was below the
observed F1-P1 run.

## Execution and artifact identity

- experiment ID: `F2-F3__gemma3-4b-it__nahw-passage__s3407__r01`;
- completion kernel:
  `univverssal/musahhih-f2-f3-final-cont-8019450-r03`, version 1;
- approved repository commit:
  `80194505bd00513f4e1661ef10798f79b83ae16b`;
- owner GO:
  `https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/98#issuecomment-5083063424`;
- prepared test SHA-256:
  `acb3cfd204b35d5415532fbd32a4a5231b553fae329ab8f48e8454609e10279b`;
- accepted B0 predictions SHA-256:
  `6997b6fe5959f5502511ebdd1885d05a89ebaefeb27eefb73520842598f36ebc`;
- accepted F1-P1 predictions SHA-256:
  `8c4d0ca25b48776a08ea02984af6c5c3ec0bc830d2d1a6994e0fb5eef995faa3`;
- private F2-P1 predictions SHA-256:
  `ca4a6eb2f5e40a60be14f59cdc7365a0f327b41ab0b8f46c8a08c43cfb442753`;
- private F3-P1 predictions SHA-256:
  `ccb296e0f091bf28ebe4d7c8b9ed454934f4dade0b5793dcf1b3a5706379c35c`;
- private corpus-free summary SHA-256:
  `0fcc52f430f190fe3e7271327503c8afb163bbccc4d296e75d04c065b16a7eb6`;
- decoding: greedy (`do_sample=false`), temperature not passed,
  `max_new_tokens=32`, seed 3407; and
- runtime: Tesla P100-PCIE-16GB, CUDA 12.4, Python 3.12.13,
  PyTorch 2.6.0+cu124, Transformers 4.56.2, Unsloth 2026.7.5,
  PEFT 0.19.1, TRL 0.22.2, and Accelerate 1.13.0.

The continuation verified and copied the immediately preceding private
timeout-safe handoff. F2-P1 remained byte-identical to its completed 511-record
artifact; F3-P1 resumed after its preserved 168-record prefix rather than
regenerating completed records.

## Independent verification

The downloaded private artifacts were audited without printing corpus text or
model responses. The audit verified:

- exact hashes for the prepared test and accepted B0/F1-P1 references;
- 511 unique IDs and exact frozen-input order for each F2/F3 arm;
- exact preservation of record identity, source, prompt, and gold fields;
- exact private row schemas and valid response, parse, warning, and score types;
- stored exact-match booleans against parsed correction and frozen gold;
- independently recomputed arm counts and warning counts;
- exact reproduction of all five preregistered paired comparisons; and
- agreement among private prediction files, `progress.json`, and the
  corpus-text-free `public_summary.json`.

Private predictions, Nahw-Passage text, prompts, gold corrections, model
responses, parsed corrections, warnings, adapters, and run logs remain ignored
and unpublished.

## Interpretation and decision

Exact-word match is deliberately strict and does not credit alternate valid
corrections unless they equal the supplied gold string. No expert linguistic
review was performed or claimed. The observed comparisons describe these
frozen runs and do not establish general Arabic proficiency.

Accept the completed F2/F3 comparison and close the execution task without a
repeat run. The continuation authorization is consumed. Do not use these test
results to tune prompts, parsing, checkpoints, training data, or experimental
decisions, and do not run another final evaluation.
