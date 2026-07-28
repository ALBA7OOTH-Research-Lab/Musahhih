# B1-P1 five-shot final-evaluation audit

## Result

The single authorized B1-P1 run completed all 511 unique, ordered
Nahw-Passage records:

- B1-P1 exact-match accuracy: `89 / 511 = 0.17416829745596868`
  (17.42%);
- invalid or empty parsed outputs: 0; and
- multi-token or otherwise suspicious-format outputs: 16.

All 16 suspicious-format outputs were incorrect under the frozen parser and
exact-match rule. Their raw text remains private.

## Staged paired comparisons

Every reference prediction file was byte-identical to its accepted hash.
Using 10,000 paired-bootstrap samples and seed 3407:

| Comparison | Difference | 95% paired-bootstrap interval | Exact McNemar p |
| --- | ---: | ---: | ---: |
| B0-P1 minus B1-P1 | `-0.005870841487279843` | `[-0.033268101761252444, 0.021526418786692758]` | `0.7754496546815659` |
| F1-P1 minus B1-P1 | `0.1095890410958904` | `[0.07240704500978473, 0.14677103718199608]` | `1.590532847378614e-08` |
| F2-P1 minus B1-P1 | `0.03131115459882583` | `[-0.011741682974559686, 0.07436399217221135]` | `0.18122406088142373` |
| F3-P1 minus B1-P1 | `0.14285714285714285` | `[0.10176125244618395, 0.18395303326810175]` | `6.968772941670867e-11` |

B1-P1 was not established as different from the accepted B0-P1 zero-shot
run. F1-P1 and F3-P1 were higher than B1-P1 in these staged comparisons.
F2-P1 was numerically higher, but its paired interval included zero.

These comparisons are staged: B0/F1 and F2/F3 were completed before B1-P1.
They must not be described as one simultaneously preregistered experiment.

## Execution identity

- issue: #139;
- approval:
  `https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/139#issuecomment-5103481369`;
- private kernel: `thgh15/musahhih-b1-final-0c34d18-r04`, version 1;
- terminal state: `COMPLETE`;
- exact commit: `0c34d1846cebc81ea847d8c2c352c353f8988d46`;
- elapsed time: 22,612 seconds (6 h 16 min 52 s);
- GPU: one Tesla P100-PCIE-16GB;
- model: `unsloth/gemma-3-4b-it-unsloth-bnb-4bit`;
- immutable model revision:
  `316726ca0bd24aa323bfaf86e8a379ee1176d1fe`;
- seed: 3407;
- decoding: greedy, no temperature argument, maximum 32 new tokens; and
- runtime: PyTorch 2.6.0+cu124, Transformers 4.56.2, Unsloth 2026.7.3.

The frozen input, B1 bundle, prompt, model, revision, seed, and decoding
identities all matched the reviewed execution contract.

## Artifact audit

- frozen input SHA-256:
  `acb3cfd204b35d5415532fbd32a4a5231b553fae329ab8f48e8454609e10279b`;
- B1 bundle SHA-256:
  `760674f0d6cc85c48b2be18d175b87e2025cd3d01fde31a6e25afaa08f9fc11a`;
- aggregate prompt SHA-256:
  `cd89f88bf9d78e624a209c609fbd5ac24c2ed548bf681a19c6e2591e4f363df8`;
- private predictions SHA-256:
  `b239b429ab99f2692d1e17cf5f6ebe47fbb94e6e3007ccf5df4143b86dfdccf2`;
- private summary SHA-256:
  `45db8e3e68862e157e31bcf5f5fcce679e26efd46b4afe60d536fdc1c1e22905`;
- private progress SHA-256:
  `edc8da5ddaa7c1d3cd7eb711964fc45bcedf16062705a4df98ca27214018e0ea`;
- private run-log SHA-256:
  `8742cecc01c515a58062688d4407c1dc6e8e6d35ac46d2354fc3d5f3116c190d`;
- submitted wrapper SHA-256:
  `0c80ace914273969bc11f8fe0868a182c388676f6f98ea2517dd65078a3bb519`;
  and
- submitted metadata SHA-256:
  `2bf215ab3c179a2352226bcb749b70116a6313088327c2cb8feb1d350ccc9438`.

The audit reproduced the 511-record order and identity, prompt rendering and
hashes, parser outputs, exact-match booleans, aggregate counts, and paired
statistics without printing corpus text.

Predictions, prompts, raw responses, gold values, and logs remain ignored and
private.

## Decision

Accept B1-P1 as the frozen five-shot prompt-baseline result. The issue #139
authorization is consumed. Do not rerun B1-P1 or tune prompts,
demonstrations, parsing, model choices, or any experiment decision from this
test result.

B2-P1 remains unevaluated and unauthorized.
