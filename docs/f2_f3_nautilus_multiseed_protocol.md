# F2/F3 Nautilus multi-seed robustness protocol

Status: preparation only; no execution authorized.

> Execution note (2026-07-30): the first authorized A100 preflight at
> `8ce1cca566c07cb3b544a6c865a0bdc7d3613733` failed before its init container
> started because the pinned checkout-image checksum was only 62 hexadecimal
> characters. No checkout, CUDA operation, private access, model loading,
> training, inference, or metric occurred, and no retry was made. Issue #157
> prepares a repository-only digest repair plus pre-generation validation. A
> replacement preflight requires review, merge, and a fresh exact-commit GO.

> Execution note (2026-07-30): the separately authorized replacement preflight
> at `45fb80f0208bd8a504ef9bb66a9207cb7e09199e` passed the repaired image pull,
> immutable checkout, PyTorch image pull, and dependency installation, then
> failed before CUDA because the main runtime lacked a `git` executable used by
> the runner's redundant commit check. No private access, model loading,
> training, inference, or metric occurred, and no retry was made. Issue #159
> replaces that subprocess with strict detached-HEAD metadata verification. A
> further preflight still requires review, merge, and a fresh exact-commit GO.

> Execution note (2026-07-30): a fresh second replacement on a healthy A100
> node passed detached-HEAD verification and the synchronized exact-A100 CUDA
> operation, then failed before any private access because importing
> bitsandbytes initialized Triton and the minimal PyTorch `runtime` image had no
> C compiler. Issue #161 keeps PyTorch 2.6.0, CUDA 12.4, cuDNN 9, and the frozen
> package stack while switching to the matching official digest-pinned `devel`
> image and adding an explicit compiler gate. Another preflight still requires
> review, merge, and a fresh exact-commit GO.

> Execution note (2026-07-30): the separately authorized compiler-capable
> preflight at `d25725e2e9fba947e2b649664de3b26d52a6b1a2` completed 1/1
> with zero restarts. It validated one `NVIDIA A100-PCIE-40GB`, compute
> capability 8.0, a synchronized CUDA tensor operation, `/usr/bin/cc`, every
> frozen package version, all required imports, FP16, BF16 disabled, and TF32
> disabled. It used no private volume, dataset, model, training, inference, or
> metric. A non-fatal warning showed that TRL was imported before Unsloth.
> Issue #163 makes Unsloth-first ordering explicit and separates private
> CPU-only staging from the five GPU Jobs before training is eligible.

> Execution note (2026-07-30): issue #163's authorized private-staging
> operation created exactly one no-GPU Pod and one 100 GiB RWX PVC, but the
> selected `cephfs` provisioner emitted only repeated `ExternalProvisioning`
> waits. After more than 5.5 minutes, the PVC had no volume or capacity and the
> Pod remained unscheduled. No private byte was uploaded. The Pod and unbound,
> data-free claim were deleted without retry. Issue #165 switches only the
> storage class to the namespace's proven `rook-cephfs` RWX provisioner.

> Execution note (2026-07-30): issue #165's replacement staging passed on a
> 100 GiB `rook-cephfs` RWX claim. The exact F2, F3, and common-development
> hashes and counts passed without corpus text output. A final no-input
> import-order A100 preflight also passed at
> `b01e93d35bf134fc7b547b7dbc17bec185794faf`. The subsequently authorized five
> Jobs all failed before the first optimizer step. Retained logs from seeds
> 3408, 3409, and 3411 showed one common cause: model loading selected BF16 on
> the A100 while the frozen trainer requested FP16, and Unsloth rejected the
> mismatch during `SFTTrainer` construction. Issue #167 forces FP16 model
> loading, adds an exact model-and-trainer construction smoke, and adds durable
> crash/continuation controls. Merge authorizes no execution.

## Purpose and interpretation

This is a post-hoc, prospectively frozen robustness replication prompted by the
completed single-seed F3-P1 versus F2-P1 result. It is not part of the original
preregistration and must not be described as such.

The replication measures whether the F3-P1 minus F2-P1 result remains stable
across training randomness. It does not authorize a new model, dataset,
training size, prompt, parser, checkpoint rule, task, or test set.

## Frozen cohort

- arms: F2-P1 and F3-P1 only;
- seeds: `3407`, `3408`, `3409`, `3410`, `3411`;
- five Kubernetes Jobs, one per seed;
- exactly one NVIDIA A100 with compute capability 8.0 per Job;
- each Job trains both arms sequentially on the same assigned GPU;
- arm order alternates by seed:
  - 3407: F2 then F3;
  - 3408: F3 then F2;
  - 3409: F2 then F3;
  - 3410: F3 then F2;
  - 3411: F2 then F3.

The frozen Gemma revision, LoRA targets and rank, two epochs, optimizer,
learning rate, effective batch size, sequence length, training record counts,
training-view hashes, common QALB development hash, completion-only objective,
and checkpoint rule remain identical to the completed F2/F3 workflow.
Training remains FP16 even though A100 supports BF16, and TF32 is disabled, so
the replication does not silently change the original P100 precision contract.

Both epoch checkpoints are preserved. The original common-development rule
selects the lower assistant-token loss, with a difference within `1e-6`
selecting epoch 1.

Operational recovery checkpoints are additionally written every 25 optimizer
steps. They do not participate in checkpoint selection and do not change the
optimizer, schedule, batches, examples, loss, evaluation cadence, or the two
epoch-boundary candidates. Their sole role is to cap lost work after an
external Pod or node failure. Epoch checkpoints are never pruned.
Each save also writes a durable identity sidecar hashing the adapter model,
adapter configuration, Trainer state, optimizer, scheduler, and RNG state.

## Cluster contract

The prepared namespace is `aiea-interns`. Read-only inspection on 2026-07-30
showed:

- five non-opportunistic A100 requests allowed and zero in use;
- 200 pods allowed and 12 in use;
- Kubernetes Jobs and PVC creation allowed;
- `cephfs` supports dynamically provisioned shared storage;
- H100, H200, and GH200 quota is zero;
- node listing is forbidden to this user.

The training manifest requests and limits exactly eight CPU cores, 32 GiB
memory, 40 GiB ephemeral storage, and one `nvidia.com/a100`. It uses no
opportunistic priority class. Each Job has `backoffLimit: 0`; eviction, node
failure, nonzero exit, or any other failure does not cause an automatic
research retry.

Every authorized training attempt derives a unique write-once attempt ID from
its GitHub owner-comment URL. The Kubernetes Job name, private log, exit record,
and attempt state use that ID, so a fresh GO cannot overwrite an earlier
failure. The shell wrapper copies complete stdout/stderr to the private PVC,
requires the log write to succeed, atomically records the process exit code,
and calls `sync` before exit.

The private PVC is named `musahhih-f2-f3-replication`, uses `ReadWriteMany`,
and requests 100 GiB on `rook-cephfs`. A separately authorized CPU-only staging Pod
mounts it once to receive the three ignored private files. After write-once
hash/count verification, the staging Pod terminates and is deleted. The
pre-staged PVC is then mounted only by separately authorized training Jobs.

## Execution order and privacy boundary

Private staging and training are separate authorizations. The staging manifest
creates exactly one RWX PVC and one no-GPU Pod. Files are copied to an upload
directory, and a separate readiness marker triggers verification. The Pod
requires the frozen SHA-256 and line count for all three files, atomically
moves them into the input directory, writes a corpus-text-free completion
manifest, and exits. Existing upload or input content causes immediate failure.

Before a training private path is constructed or opened, the runner must:

1. check out the exact approved repository commit in detached mode;
2. validate the issue-comment GO;
3. confirm CUDA is available and exactly one GPU is visible;
4. require an NVIDIA A100 with compute capability 8.0;
5. execute and synchronize a real CUDA tensor operation.

Only then may an authorized training Job validate the exact staging completion
manifest and open the frozen F2, F3, and common development files to validate
their existing hashes, counts, schemas, and provenance. The paired-training
manifest emits only the five Jobs and refuses to create or replace the
pre-staged PVC.

Nahw-Passage and QALB test are not mounted, addressed, opened, or accepted by
the training runner. No inference or metric is part of this issue.

The PVC, private inputs, model cache, checkpoints, trainer state, logs, and
activation manifests remain private and Git-ignored. Public output is limited
to corpus-text-free configuration and reviewed aggregate audits.

## Write-once behavior

Each seed has a stable private output root plus write-once per-GO attempt
records. Existing state is never deleted or overwritten. The runner writes:

- `00_started.json`;
- `attempts/<owner-comment-id>/00_started.json`;
- `attempts/<owner-comment-id>/98_failed.json` on a Python failure, containing
  only phase, exception class, a message hash, and aggregate state;
- one completion record after each arm;
- `attempts/<owner-comment-id>/99_complete.json` after the pair;
- `99_pair_complete.json` only after both arms finish.

Every epoch checkpoint must contain a hashed adapter model and adapter
configuration. A fresh-GO continuation validates the exact commit, seed,
private-input identities, completed-arm markers, checkpoint identities, and
Trainer state before skipping a completed arm or resuming the newest compatible
25-step checkpoint. It never resumes automatically. A failed or incomplete Job
remains preserved and still requires a separate owner decision and fresh GO.

## Authorization separation

Merge of the preparation code authorizes nothing.

Private CPU-only staging requires a fresh comment of the form:

> GO: authorize exactly one private-input staging operation for Musahhih issue
> #163 at exact merged commit `<40-hex-commit>`: create the reviewed 100 GiB
> RWX PVC and one no-GPU staging Pod, upload only the frozen F2, F3, and common
> development JSONL files, verify only their exact hashes and counts without
> printing corpus text, preserve the first terminal state, and do not retry.

One no-input/no-model A100 preflight requires a fresh comment of the form:

> GO: authorize exactly one no-input/no-model Nautilus A100 preflight for
> Musahhih issue #155 at exact merged commit `<40-hex-commit>`, using zero
> datasets, zero model loading, zero training, zero inference, and zero metric.
> Preserve the first terminal state and do not retry.

After issue #167 merges, one no-private exact model/trainer smoke requires a
fresh comment of the form:

> GO: authorize exactly one no-private Nautilus A100 FP16 model-and-trainer
> construction smoke for Musahhih issue #167 at exact merged commit
> `<40-hex-commit>`. It may load only the frozen Gemma revision, construct the
> frozen FP16 LoRA model, completion-only collator, and `SFTTrainer` on the
> built-in synthetic smoke row, and execute zero optimizer steps. Mount no PVC
> or corpus; run no training, inference, prediction, or metric. Preserve the
> first terminal state and do not retry.

Only after private staging and the FP16 model/trainer smoke both pass may the
owner separately authorize the replacement five-job training wave:

> GO: authorize exactly five Nautilus A100 Jobs for Musahhih issue #155 at
> exact merged commit `<40-hex-commit>`, one Job for each seed 3407–3411. Each
> Job may train only the frozen F2-P1 and F3-P1 pair in its prescribed order,
> for two epochs per arm, using only the frozen training views and common QALB
> development set. Preserve both epoch checkpoints and private logs. Do not
> mount or access Nahw-Passage or QALB test; do not run inference or metrics;
> do not tune any setting. Resume only exact-commit, hash-verified compatible
> private progress; do not retry or replace a failed Job without another fresh
> GO.

The no-input smoke GO cannot authorize training. The training GO cannot
authorize later evaluation. Any selected-checkpoint or fixed-epoch evaluation
requires a separate reviewed protocol, exact-commit GO, and issue after all ten
training runs are frozen.

## Planned reporting

If all ten runs complete and a later evaluation is separately authorized, the
paper should report every seed result, per-arm mean and standard deviation,
each paired F3-minus-F2 difference, and the mean, standard deviation, and range
of those five differences. The original seed-3407 result remains the primary
completed experiment; this cohort is labeled post-hoc robustness evidence.
