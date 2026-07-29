# B2-P1 expert-style final-evaluation audit

## Result

The single authorized repaired B2-P1 run completed all 511 unique, ordered
Nahw-Passage records:

- exact-match accuracy: `108 / 511 = 0.21135029354207435` (21.14%);
- invalid or empty parsed outputs: 0; and
- suspicious or multi-token outputs: 6.

All six suspicious outputs were incorrect. Their text remains private. B2-P1
used the frozen expert-style prompt and no demonstration bundle.

## Staged paired comparisons

All reference artifacts matched their accepted hashes. With 10,000
paired-bootstrap samples and seed 3407:

| Comparison | Difference | 95% interval | Exact McNemar p |
| --- | ---: | ---: | ---: |
| B2-P1 minus B0-P1 | `0.043052837573385516` | `[0.019569471624266144, 0.0684931506849315]` | `0.0009406740282429382` |
| B2-P1 minus B1-P1 | `0.03718199608610567` | `[0.007827788649706457, 0.06653620352250489]` | `0.018337087779101986` |
| F1-P1 minus B2-P1 | `0.07240704500978473` | `[0.033268101761252444, 0.1095890410958904]` | `0.00029596019615458444` |
| F2-P1 minus B2-P1 | `-0.005870841487279843` | `[-0.050880626223091974, 0.03913894324853229]` | `0.8624034912671916` |
| F3-P1 minus B2-P1 | `0.10567514677103718` | `[0.06653620352250489, 0.14481409001956946]` | `2.519412514630621e-07` |

B2-P1 exceeded B0-P1 and B1-P1. F1-P1 and F3-P1 exceeded B2-P1. No
difference was established between F2-P1 and B2-P1.

These are staged comparisons because the systems were executed at different
times. Do not describe them as one simultaneously preregistered experiment.

## Execution identity

- issue: #147;
- private kernel: `thgh15/musahhih-b2-final-8a13d56-r02`, version 1;
- terminal state: `COMPLETE`;
- exact commit: `8a13d56b1a38bdad20e264ae358cf842c41d0909`;
- completed-progress elapsed time: 22,153 seconds;
- GPU: Tesla P100-PCIE-16GB;
- model: `unsloth/gemma-3-4b-it-unsloth-bnb-4bit`;
- immutable revision:
  `316726ca0bd24aa323bfaf86e8a379ee1176d1fe`;
- seed: 3407; and
- decoding: greedy, no temperature argument, maximum 32 new tokens.

The exact input, prompt, model, revision, seed, decoding, and no-bundle
identities matched the reviewed contract.

## Artifact audit

- input SHA-256:
  `acb3cfd204b35d5415532fbd32a4a5231b553fae329ab8f48e8454609e10279b`;
- aggregate prompt SHA-256:
  `2647715e2a11f4a9121c80cb9fe1b296ffc76c17f4242338e3779cc8bf9b8d7c`;
- private predictions SHA-256:
  `72990dd12b00b6db70e56737abac95c9c0367b3bedc0dd745cf1751fa9a5f115`;
- private summary SHA-256:
  `e6d47715dc02dc8b30a09e040dd39057c5aede4102775a191c0301def237f672`;
- private progress SHA-256:
  `61f2b1c960749b0b37005c6a5f0316446cf2c9c993329b186fb36468325a4a49`;
- private run-log SHA-256:
  `8742cecc01c515a58062688d4407c1dc6e8e6d35ac46d2354fc3d5f3116c190d`;
- wrapper SHA-256:
  `b2df183de5d181a54c4018c88649202d2fb1c8ba9c36ed9f5e16cb8b7457c354`;
  and
- metadata SHA-256:
  `0d2a6103359acf3b146de318f7d3ab1530638f98ac1e757a5b6bf249c3817a79`.

The audit reproduced record order, prompt hashes, parser outputs, exact-match
booleans, counts, and paired statistics without printing corpus text.
Predictions, prompts, raw responses, gold values, and logs remain private.

## Decision

Accept B2-P1 as the frozen expert-style prompt-baseline result. The issue #147
authorization is consumed. Do not rerun or tune any decision from this result.
