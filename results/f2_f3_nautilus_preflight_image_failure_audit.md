# F2/F3 Nautilus A100 preflight image failure audit

## Scope

Issue #155 authorized exactly one no-input/no-model A100 preflight at merged
commit `8ce1cca566c07cb3b544a6c865a0bdc7d3613733`. The authorization comment is:

`https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/155#issuecomment-5132105855`

The generated one-Job manifest had SHA-256
`e6ec0569457170dc4a27bfafa3dfff135ad38af0545fd92f8129b6b1842a85ee`.

## Terminal outcome

The single Job `aiea-interns/musahhih-f2-f3-preflight` was created. Its pod was
scheduled, then immediately reported `Init:InvalidImageName`. Kubernetes
reported that the pinned `alpine/git:2.47.2` checksum had an invalid digest
length. Inspection confirmed that the merged checksum contained 62 hexadecimal
characters rather than the 64 required by SHA-256.

The init container never started. Therefore no repository checkout, dependency
installation, CUDA operation, private volume, dataset access, model loading,
training, inference, prediction, or metric occurred.

The aggregate failure was recorded on issue #155. The failed Job was then
deleted solely to release its scheduled A100 allocation. No replacement Job
was created and no retry occurred. The authorization is consumed.

## Reviewed repair

Issue #157 replaces the malformed checksum with Docker Hub's published
Linux/AMD64 digest for the same image tag:

`sha256:0d9a3a551058dba37ea77757955d3e834442ccf8540783671cc25c0d97957894`

The authoritative image entry is:
`https://hub.docker.com/layers/alpine/git/2.47.2/images/sha256-0d9a3a551058dba37ea77757955d3e834442ccf8540783671cc25c0d97957894`.

Manifest preparation now rejects every container image that is not pinned by a
full, lowercase, 64-character SHA-256 digest. The regression test covers an
unpinned tag, a 62-character digest, and an uppercase digest.

At repair commit `1429a9bb4336d44c6ecba8bf92b5d91060189e50`,
compilation, formatting, lint, 8 focused tests with 7 subtests, and the full
251-test suite with 72 subtests passed. The repaired one-object preflight
manifest contained one `emptyDir`, zero private-volume mounts, and passed a
Nautilus server dry-run without persistence. Its validation-only manifest
SHA-256 was
`52ec797e114ad30486e6f6c20d4d72d601e62fd9a11c2f1a6200f48ddcf7f184`.

This repair authorizes no cluster object or GPU execution. After review and
merge, one replacement no-input/no-model preflight requires a fresh
exact-commit owner GO. Paired training remains unauthorized.
