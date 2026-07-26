# Artifact release audit

Status reviewed: 2026-07-26

This audit distinguishes reproducibility from permission to redistribute.
Possessing an artifact, computing its hash, or being able to upload it does not
authorize public release.

## Current decision

Only the existing corpus-text-free code, documentation, aggregate summaries,
and hashes are approved for the current public repository. No adapter,
checkpoint, private prediction, raw response, private log, QALB-derived record,
or transformed QALB artifact is approved for release.

The repository also has no top-level software license. Until the owners add an
appropriate license, do not describe the source code as open-source or imply
permissions beyond viewing the public repository.

## Release matrix

| Artifact class | Current location/status | Current public-release decision | Required action before changing the decision |
| --- | --- | --- | --- |
| Source code and tests | Public repository | Publicly visible, but not explicitly licensed | Owner/legal choice of software license; confirm compatibility with dependencies and any copied code. |
| Protocols and aggregate audits | Public repository | Approved, provided they remain corpus-text-free | Continue privacy, citation, metric-consistency, and credential review. |
| Machine-readable aggregate summaries | Public `results/` | Approved | Preserve hashes, no record-level fields, no private development metrics. |
| Nahw-Passage source/test text | Public upstream benchmark; private prepared copies | Do not republish from this repository without checking upstream terms | Cite and link the authoritative source; review its license before bundling. |
| QALB archive | Private, research-restricted | Prohibited | Additional rights-holder permission and institutional guidance would be required. |
| QALB-derived training/development records | Private and ignored | Prohibited | Institutional/legal determination that the proposed transformation and redistribution are permitted. |
| Tibyan source corpus | Authoritative Zenodo release, CC BY 4.0 | Link to the authoritative release; do not duplicate by default | If redistribution is needed, include attribution, license link, change notice, and upstream checksums. |
| ArabicMMLU questions and selected subset | Private prepared diagnostic; CC BY-NC 4.0 | Do not include questions or answers in this repository | Attribution, non-commercial compliance, and a specific release review. Aggregate results may remain public. |
| B0/F1/F2/F3 record-level predictions | Private and ignored | Prohibited under current policy | Dataset-output licensing, privacy, benchmark-integrity, and upstream-license review. |
| F1-P1 adapter | Private; trained from QALB-derived natural records | Prohibited | QALB license/institutional review, Gemma terms review, model-card documentation, and authors' approval. |
| F2-P1 adapter | Private; trained from Tibyan-derived synthetic records | Not approved | Confirm Tibyan attribution/change obligations, Gemma terms, repository license, model card, and authors' approval. |
| F3-P1 adapter | Private; trained from QALB-derived natural plus Tibyan synthetic records | Prohibited | Resolve both QALB and Tibyan obligations, Gemma terms, model card, and institutional approval. |
| Checkpoints and optimizer states | Private and large | Prohibited | Same adapter review plus storage/security and unnecessary-training-state review. |
| Raw logs and responses | Private and ignored | Prohibited | Corpus leakage and credential review; publish only a newly generated text-free digest if justified. |
| Private development metrics | Deliberately blinded | Prohibited | No release is planned; do not read them merely to complete a table. |

## Adapter-specific considerations

### F1-P1

F1-P1 was trained from a private QALB-derived natural view. QALB 0.9.1 permits
internal research/evaluation use and restricts redistribution and dataset
modification. Publishing adapter weights may raise derivative-artifact
questions that this repository cannot resolve. Keep the adapter private.

### F2-P1

F2-P1 used a deterministic Tibyan-derived synthetic view. Tibyan is CC BY 4.0,
which is more permissive, but adapter release is still not automatically
cleared. The project must review Gemma's applicable terms, preserve Tibyan
attribution and change disclosure, add a repository license, write a model
card, and obtain owner approval.

### F3-P1

F3-P1 combines QALB-derived natural data with Tibyan-derived synthetic data.
The QALB restriction remains controlling for the current conservative release
decision. Keep the adapter private unless qualified institutional review
explicitly clears it.

## Minimum public paper package

The paper package can safely contain:

- exact repository and workflow commits;
- immutable model and dataset identifiers;
- corpus-text-free data counts and selection methods;
- aggregate metrics, paired intervals, p-values, warning counts, and hashes;
- code needed to prepare licensed inputs in an authorized private environment;
- disabled-by-default evaluation/training code;
- privacy, leakage, license, and staged-comparison limitations; and
- links and citations to authoritative upstream datasets.

It must not contain:

- QALB text or transformed QALB records;
- benchmark questions, prompts, gold corrections, or record IDs;
- raw or parsed model responses;
- private predictions, logs, adapters, checkpoints, or credentials; or
- claims that the repository, adapters, or datasets are openly licensed before
  the corresponding license review is complete.

## Required owner decisions

1. Choose whether this repository should receive an explicit software license.
2. Decide whether adapter release is a paper requirement.
3. If yes, obtain institutional/legal review separately for F1-P1, F2-P1, and
   F3-P1 rather than assuming one decision covers all three.
4. Decide whether a public model card may report hashes and training
   methodology while leaving the actual adapters private.
5. Identify the authoritative long-term private storage and access-control
   policy for retained adapters and predictions.
