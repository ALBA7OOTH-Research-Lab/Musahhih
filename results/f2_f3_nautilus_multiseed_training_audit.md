# F2/F3 Nautilus multi-seed training terminal audit

## Scope

Issue #167 authorized exactly five replacement Nautilus A100 Jobs at merged
commit `108888dcf0ad34c49157b47e2561c406c5463bf8`, one for each seed from
3407 through 3411. The authorization comment is:

`https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/167#issuecomment-5136464333`

The five-object manifest had SHA-256
`e89a02d9380048c2ed435b19ba5598ac35ee67e5a4467d91216d450170279e24`.
Every Job requested one A100, used `backoffLimit: 0`, derived a unique
write-once attempt identity from the authorization-comment ID, and mounted
only the previously verified private F2/F3 training and common-development
PVC. Nahw-Passage and QALB test were absent from the manifest.

## Terminal outcome

All five Pods reached `Succeeded` with container exit code zero and zero
restarts. The cluster later garbage-collected the Job objects, while the
retained Pods and their log APIs preserved terminal evidence. No Job was
retried, replaced, or continued.

| Seed | Frozen arm order | Training-container interval (UTC) | Seconds | Node |
| --- | --- | --- | ---: | --- |
| 3407 | F2-P1, F3-P1 | 2026-07-31 00:34:55–07:52:11 | 26,236 | `tu.gp-engine.greatplains.net` |
| 3408 | F3-P1, F2-P1 | 2026-07-31 00:34:54–07:42:13 | 25,639 | `tu.gp-engine.greatplains.net` |
| 3409 | F2-P1, F3-P1 | 2026-07-31 00:33:40–07:33:41 | 25,201 | `gpn-fiona-mizzou-4.rnet.missouri.edu` |
| 3410 | F3-P1, F2-P1 | 2026-07-31 00:34:02–08:30:36 | 28,594 | `rci-nrp-gpu-02.sdsu.edu` |
| 3411 | F2-P1, F3-P1 | 2026-07-31 00:33:16–09:22:52 | 31,776 | `sdsmt.gp-argo.greatplains.net` |

Each final corpus-free summary reported `status: complete`, both prescribed
arms in order, and `contains_corpus_text: false`. Therefore both two-epoch
training arms and the frozen common-development checkpoint-selection workflow
returned normally for every seed. The retained log streams, as returned by
the Kubernetes log API and normalized to UTF-8 with a terminal newline, had
these SHA-256 identities:

- seed 3407: `16a83fea77972d5164cee8fc771e574a127df96cb012c203374e6adfb630bf16`;
- seed 3408: `574571aa24611fbfa3cc5cc44687ac21642ccd9f43c7b45e00cb851b1f84b4b5`;
- seed 3409: `d42a898915e7b393f970620654d912211af8912cacdfa403d509cbf74fa90886`;
- seed 3410: `fddc7967b940a9d94327b5eae9d1a97286f60aa75d3053da1c771fac72798726`;
- seed 3411: `9ec604d8192ee0688ab737016ea39dd1aebbdc7e41a43a7b1e4e09d970e0f54b`.

Private adapters, epoch checkpoints, recovery checkpoints, checkpoint
selection records, development losses, and full logs remain on the retained
PVC and are not published.

## Scientific boundary and next gate

These Jobs performed training and common-development checkpoint selection
only. They did not access Nahw-Passage or QALB test and did not run inference,
produce predictions, or compute a final evaluation metric. Consequently no
multi-seed accuracy, variance, or F3-minus-F2 claim is yet allowed.

The five-Job authorization is consumed. Any private artifact audit or frozen
multi-seed evaluation/aggregation requires a separately reviewed protocol and
a fresh scope-specific owner GO. Training must not be repeated or tuned from
this terminal outcome.
