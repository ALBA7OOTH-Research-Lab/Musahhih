# F2/F3 Nautilus multi-seed preparation audit

Recorded: 2026-07-30

Status: preparation complete; no cluster object or research execution created.

## Scope

Issue #155 prepares a post-hoc, prospectively frozen five-seed robustness
replication for F3-P1 versus F2-P1. The seed set is 3407–3411. Five paired
Kubernetes Jobs each train both arms sequentially on one A100, with alternating
arm order.

This work does not authorize or execute a Job, PVC, private-input access, model
load, optimizer step, training, inference, Nahw-Passage access, QALB test
access, metric, retry, or continuation.

## Read-only cluster findings

The authenticated Nautilus context uses namespace `aiea-interns`. Read-only
inspection found:

- permission to create Jobs and PVCs;
- an A100 quota of five requests, with zero used at inspection time;
- H100, H200, and GH200 quota of zero;
- a 200-pod quota, with 12 used at inspection time;
- `cephfs` available for dynamic shared storage;
- no permission to list cluster nodes.

The preparation used an external Nautilus guide only as a read-only operational
reference. No file, command, data, resource, or output in its source project
was changed or executed.

## Frozen execution design

- five seeds: 3407, 3408, 3409, 3410, 3411;
- five concurrent Jobs, one seed and one GPU per Job;
- two matched arms per Job on the same A100;
- three seeds run F2 first and two run F3 first;
- exact NVIDIA A100 identity and compute capability 8.0 required;
- real CUDA tensor operation and synchronization before private access;
- FP16 forced and TF32 disabled;
- original model revision, LoRA, optimizer, data hashes, two epochs,
  common-development selection rule, and checkpoint retention preserved;
- both epoch checkpoints retained and hashed;
- append-only atomic completion evidence;
- `backoffLimit: 0`, write-once seed roots, and no automatic retry;
- no Nahw-Passage or QALB-test path in the Jobs.

The training image is pinned to:

`pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime@sha256:77f17f843507062875ce8be2a6f76aa6aa3df7f9ef1e31d9d7432f4b0f563dee`

The immutable-checkout image is pinned to:

`alpine/git:2.47.2@sha256:062a01ad7a0eb17cff382bc5e26086b4d710e56dfdf001109a49b6d9bd378c`

## File identities

- protocol:
  `283f44328ffaded0bac23b10ec32ad48ac8b2e159fe12a86c638628ef8187e88`;
- package requirements:
  `694b23bae3199dc393b0a1307c51a0eebdec26ffa70d34a0f12bc6032b7af637`;
- activation/A100 utilities:
  `e753c988f4204463b30597d6a8f463cba21960b7fa2a7e6d7b11bee95c849472`;
- manifest generator:
  `84b38cdff5f2052b97d9c194cce21a0d5f8208505d25eee1b696bd6e837d0ee2`;
- paired runner:
  `0a10de592e8c0203269a0d0f84a5c3d91be95e50d8151dd8b177c7a06ba9a65f`;
- focused tests:
  `6427d9b8382a218a2334019f68bebadac182d9ee38568779b350edbdcc3ce0f5`.

## Validation

- `python -m compileall scripts`: passed.
- `python -m unittest tests.test_f2_f3_nautilus -v`: 7 passed.
- `python -m unittest discover -s tests -p 'test_*.py' -q`: 250 passed.
- Kubernetes client dry-run: one preflight Job plus one PVC and five training
  Jobs accepted.
- Kubernetes server dry-run: the same seven objects were accepted by Nautilus
  admission without persistence.
- Job requests equal limits for CPU, memory, ephemeral storage, and A100.
- Init-container requests equal limits.
- Static tests found no Nahw or QALB-test address in generated Jobs.
- `git diff --check`: passed.

## Remaining gates

After merge, one fresh owner GO may authorize exactly one no-input/no-model
A100 preflight. It must preserve the first terminal state without retry.

Only after a passing preflight may a separate exact-commit owner GO authorize
the five paired training Jobs. That GO does not authorize evaluation. Any later
selected-checkpoint or fixed-epoch evaluation requires a new issue, reviewed
protocol, frozen completed adapter identities, and separate GO.
