# B1-P1 `8710263-r03` final-attempt failure audit

## Scope

Issue #125 authorized exactly one timeout-safe private B1-P1 Nahw-Passage
segment on phone-verified Kaggle account `thgh15`, using repository commit
`87102633e0f1b76a2ee4d83a3e29e20de0da9137`.

The private kernel was
[`thgh15/musahhih-b1-final-8710263-r03`](https://www.kaggle.com/code/thgh15/musahhih-b1-final-8710263-r03),
version 1. Kaggle reported terminal `ERROR`.

## Terminal evidence

The wrapper passed the following gates:

- exact repository checkout;
- single Tesla P100 identity and CUDA availability;
- reviewed dependency/import diagnostic;
- private input SHA-256
  `acb3cfd204b35d5415532fbd32a4a5231b553fae329ab8f48e8454609e10279b`; and
- B1-P1 bundle SHA-256
  `760674f0d6cc85c48b2be18d175b87e2025cd3d01fde31a6e25afaa08f9fc11a`.

At approximately 114.95 seconds, before model loading, the prompt runner
rejected input line 1 because `record_id` was not a string. A corpus-text-free
schema audit of the exact 511-row private input confirmed that every row has
the frozen prepared-Nahw `id` field and no row has the prompt runner's required
`record_id` field. The dataset hash gate proved byte identity but did not prove
consumer-schema compatibility.

No model was loaded. No response, prediction, progress artifact, or metric was
created, and no training occurred.

## Additional preflight defect

The log also contains PyTorch warnings that the P100's `sm_60` CUDA capability
is incompatible with the installed PyTorch 2.10.0+cu128 build, whose supported
capabilities begin at `sm_70`. The current GPU preflight checked CUDA
availability, device count, and P100 identity but performed no CUDA tensor
operation. It therefore passed without establishing that the runtime could
execute on the P100.

This incompatibility did not cause the recorded terminal exception because the
schema guard failed first. It is nevertheless an independent blocker that must
be repaired and exercised before any future private attempt.

## Artifact handling and decision

The private kernel log remains under the ignored execution directory. Its
SHA-256 is
`e8662c52dd615e196a8538592c93e755d85f3a0d10e7075de97e4f4ccd264540`.
No corpus text or model response was printed or published.

This is a pre-inference engineering failure, not a B1-P1 result. The single-use
authorization is consumed. No edit, second kernel version, retry, resubmission,
hot-patch, B2-P1 run, or continuation was launched.

Before a future B1-P1 attempt can be considered, a new repair must:

1. define one canonical private-input schema or an explicitly tested
   deterministic conversion from `id` to `record_id`;
2. validate the exact private artifact against the consumer before submission;
3. require a real CUDA tensor operation on the P100, not only device discovery;
4. receive independent review at an exact merged commit; and
5. receive a fresh scope-specific owner GO.
