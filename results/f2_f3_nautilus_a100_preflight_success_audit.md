# F2/F3 Nautilus A100 preflight success audit

## Scope

Issue #161 authorized exactly one no-input/no-model compiler-capable A100
preflight at merged commit `d25725e2e9fba947e2b649664de3b26d52a6b1a2`.
The authorization comment is:

`https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/161#issuecomment-5132592452`

The generated one-Job manifest had SHA-256
`a78849ac95c2b3cc7a006e6144edd28ab3ad45ed42e68df24a758645ee3104f1`.

## Terminal outcome

The Job `aiea-interns/musahhih-f2-f3-preflight` completed 1/1 with zero
restarts. Kubernetes reported approximately 115 seconds of Job execution.

The aggregate corpus-text-free runtime result was:

- Python 3.11.11;
- PyTorch 2.6.0+cu124 and CUDA 12.4;
- exactly one `NVIDIA A100-PCIE-40GB`;
- compute capability 8.0;
- 42,405,855,232 reported GPU-memory bytes;
- synchronized CUDA tensor operation passed;
- C compiler `/usr/bin/cc`;
- every frozen package version matched;
- bitsandbytes, datasets, TRL, and Unsloth imports passed;
- FP16 training selected, BF16 disabled, TF32 matmul disabled, and TF32 cuDNN
  disabled;
- Unsloth compilation disabled.

The manifest had no private volume or input path. No dataset, model loading,
training, inference, prediction, or metric occurred. The completed Job was
deleted after evidence capture. The authorization is consumed.

## Advisory and next gate

Unsloth emitted a non-fatal warning because the audit imported TRL before
Unsloth. Although the Job completed, issue #163 makes Unsloth-first ordering
explicit to avoid degraded optimization or memory behavior in training.

Issue #163 also separates private CPU-only staging from paired training. The
three ignored local files were assembled idempotently with no corpus text
printed:

- F2: 2,000 records, SHA-256
  `bbc48dcf78ddff1830661ad749fcc8f9fbfce8206f4f09cd9f4d6501823201d2`;
- F3: 2,000 records, SHA-256
  `d16decebe559e9a25da41ef59f63ca95e339972e22b9659dfc763e071fbc1546`;
- common development: 975 records, SHA-256
  `adfdeb0c2e5730357226ce4e5156c300679629142ea0576d32dea9ac3050a950`.

This preparation authorizes no private upload or cluster object. CPU-only
staging, a final exact-commit import-order preflight, and paired training
require separate fresh owner GOs.

At preparation commit `94067944708d6462e1da302bd2a70f81910348b4`,
compilation, formatting, lint, 14 focused tests with 10 subtests, and the full
257-test suite with 75 subtests passed. Nautilus server dry-runs accepted:

- a two-object staging manifest containing exactly one RWX PVC and one no-GPU
  Pod, SHA-256
  `28b14f2484be5477d4cbea3230540d6f967f6463a94b4429f9e199c49643b9e1`;
- a five-object training manifest containing exactly five A100 Jobs and no PVC,
  SHA-256
  `2c1233cead2e134b6a70022e3eaa7037252d7a190d6a578e8f6f4b46c77db846`.

No server-dry-run object persisted.
