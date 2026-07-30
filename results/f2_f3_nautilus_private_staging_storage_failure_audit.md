# F2/F3 Nautilus private-staging storage failure audit

## Scope

Issue #163 authorized exactly one private-input staging operation at merged
commit `85e00b9fe39e8f7706fefe4fbc9e3ce002c68244`. The authorization
comment is:

`https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/163#issuecomment-5132797565`

The two-object manifest had SHA-256
`12150ff9d7b9afa571a091b9340c115802f779e86c4874143d2089a05a732ef1`.

## Preserved failure state

The manifest created exactly:

- PVC `aiea-interns/musahhih-f2-f3-replication`;
- no-GPU Pod `aiea-interns/musahhih-f2-f3-staging`.

For more than 5 minutes 30 seconds, the PVC remained `Pending` with no volume,
capacity, or access mode reported. Events repeatedly stated that the external
provisioner `rook-ceph.cephfs.csi.ceph.com` had not created a volume. The Pod
therefore remained unscheduled `Pending`.

No private file was uploaded, copied, opened, or written. No GPU, model,
training, inference, prediction, or metric was used. After recording the
failure on issue #163, the unscheduled Pod and unbound, data-free PVC were
deleted. No replacement was created and the authorization is consumed.

## Reviewed repair

Namespace inspection showed existing bound RWX claims, including recent
claims, using `rook-cephfs`. Issue #165 changes only the storage class from
`cephfs` to `rook-cephfs`. It retains the same:

- 100 GiB RWX request and PVC name;
- one no-GPU, no-restart staging Pod;
- write-once empty-directory gates;
- frozen input filenames, SHA-256 values, and counts;
- atomic placement and corpus-text-free completion marker;
- separation from the five GPU training Jobs.

This repository-only repair authorizes no cluster object or private upload.
Replacement staging requires review, merge, and a fresh exact-commit owner GO.

At repair commit `0c77ad655ba09a747f0d25e4ae31e0bf53119c79`,
compilation, formatting, lint, 14 focused tests with 10 subtests, and the full
257-test suite with 75 subtests passed. The corrected two-object manifest used
`rook-cephfs`, contained no GPU request, and passed a Nautilus server dry-run
without persistence. Its validation-only SHA-256 was
`941257ae417668a72c3e1db316abe582d12f39d3061573d71b36ac1ff83207a5`.
