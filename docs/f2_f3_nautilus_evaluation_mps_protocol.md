# F2/F3 Nautilus NVIDIA MPS canary repair

Status: issue #179 repository preparation only; no execution authorized.

## Preserved issue #177 outcome

The single authorized five-worker batch-16 canary at commit
`12f0aacad99f9d18445de746809ab64eb923f32b` failed only its final utilization
gate. Its 1,201.278-second sampling window contained 974 valid GPU samples and
zero sampler failures. Mean A100 utilization was 11.762%, below the required
40%. Peak GPU-memory and host-memory fractions were 0.526697 and 0.322968.
The Pod exited one with zero restarts and was not retried.

The utilization check occurs only after five complete worker summaries pass
the equal-output, batch-16 soak, and per-row durability contract. That control
flow establishes that these gates passed, but the parent failure summary did
not duplicate the underlying worker fields. This is explicitly a code-path
inference, not a separately copied worker-summary audit.

No Nahw-Passage or QALB test was mounted or accessed. No evaluation,
prediction, metric, training, retry, continuation, or XG occurred.

## Root cause addressed

Five ordinary CUDA processes retain separate scheduling contexts. NVIDIA's
Multi-Process Service (MPS) provides a shared server context so kernels and
memory copies from independent client processes can overlap, reducing context
switching when individual processes underfill the GPU. This matches the
observed pattern: safe memory headroom but low aggregate utilization.

Primary references: NVIDIA's
[MPS overview](https://docs.nvidia.com/deploy/mps/latest/index.html),
[quick start](https://docs.nvidia.com/deploy/mps/latest/quick-start.html), and
[tools/environment reference](https://docs.nvidia.com/deploy/mps/latest/appendix-tools-and-interface-reference.html).

Issue #179 changes only the GPU process scheduler. It preserves the selected
adapter, five workers, batch size 16, synthetic prompts, greedy decoding,
24-batch soak per worker, output-hash equivalence, per-row `fsync`, sampling,
80 GB A100 requirement, resource requests, timeouts, and failure boundaries.

## MPS gate

The container must, before validating a private adapter:

1. find `nvidia-cuda-mps-control` in the pinned CUDA development image;
2. create a unique local pipe directory and private write-once log directory;
3. set `CUDA_MPS_ACTIVE_THREAD_PERCENTAGE=20` for five equal clients;
4. start exactly one same-UID MPS control/server pair;
5. require exactly five connected client PIDs after all workers load;
6. run the unchanged synthetic soak and utilization/memory gates; and
7. always issue `quit` to the MPS controller on shell exit.

The canary passes only if all five worker summaries also record the MPS pipe
and 20% client allocation, their reference output hashes are equal, all 1,920
synthetic generations and durability writes complete, mean utilization is at
least 40%, peak GPU memory remains below 85%, and peak host memory remains
below 80%.

MPS control/server logs remain private. The public summary includes only
counts, percentages, booleans, runtime identities, and hashes; it contains no
prompt, output, adapter, or corpus text.

## Authorization boundary

Preparation and merge authorize no Kubernetes object, GPU allocation, model
load, test access, inference, prediction, metric, training, retry,
continuation, QALB test, or XG. One MPS canary requires a fresh issue-#179
owner comment naming the exact merged commit. A passing canary still does not
authorize the real evaluation continuation or aggregation.
