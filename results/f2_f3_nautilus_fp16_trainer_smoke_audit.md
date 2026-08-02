# F2/F3 Nautilus FP16 trainer smoke audit

## Scope

Issue #167 authorized exactly one no-private Nautilus A100 model-and-trainer
construction smoke at merged commit
`22a3384be0bda39dec6833fc0cce7d3976385203`. The authorization comment is:

`https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/167#issuecomment-5136387095`

The generated one-Job manifest had SHA-256
`f3a0e1798f855b115d9aa4d7f7bc768690f21869f2cb86888b28785fd70d7faf`.
It requested one A100, set `backoffLimit: 0`, used only an `emptyDir`
repository volume, and passed no input or output root.

## Terminal outcome

The first and only Job,
`aiea-interns/musahhih-f2-f3-fp16-trainer-smoke-a36387095`, reached
`Complete` with one succeeded Pod, zero failures, zero restarts, and container
exit code zero. Kubernetes recorded the Job from
`2026-07-30T21:22:25Z` through `2026-07-30T21:24:43Z`, or 138 seconds.

The corpus-text-free runtime evidence reported:

- Python 3.11.11;
- PyTorch 2.6.0+cu124 and CUDA 12.4;
- exactly one `NVIDIA A100-PCIE-40GB`, compute capability 8.0, with
  42,405,855,232 reported memory bytes;
- synchronized CUDA operation and required imports passed;
- the exact frozen Gemma revision loaded;
- the LoRA model, completion-only collator, and `SFTTrainer` constructed;
- the synthetic smoke row retained at least one assistant-token label; and
- zero optimizer steps.

There was no PVC or corpus mount, no private record, and no training,
inference, prediction, or metric. The completed Job was deleted only after its
terminal evidence was preserved in issue #167. The authorization is consumed,
and no retry occurred.

## Precision interpretation

The frozen trainer selected FP16 (`fp16=true`, `bf16=false`) with TF32
disabled. The model configuration passed the explicit `torch.float16` guard,
so the prior BF16-model/FP16-trainer mismatch did not recur and
`SFTTrainer` construction succeeded.

Unsloth also logged that Gemma 3 cannot keep direct float16 weights and
internally switched the weights to float32. This is compatible with its
FP32-master-weight/FP16-training path, but it means the public evidence should
not describe the stored weights themselves as FP16. The smoke executed zero
optimizer steps by authorization, so it proves construction of the repaired
training stack, not completion of a backward or optimizer step.

## Next gate

This smoke does not authorize replacement training. The five frozen paired
seed Jobs require a separate fresh owner GO naming the exact executable
commit. Each Job remains write-once, uses `backoffLimit: 0`, persists its
complete log and failure record, saves recovery checkpoints every 25 optimizer
steps, and requires a fresh GO plus exact identity validation for any
continuation.
