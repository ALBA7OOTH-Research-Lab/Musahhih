# Dataset audit

Status reviewed: 2026-08-22

## Dataset roles

| Dataset | Source | Released size | Use in this study |
| --- | --- | ---: | --- |
| QALB 2014 L1 | Mohit et al. (2014) | 19,411 train; 1,017 dev; 968 test | 2,000 filtered training records for F1; nested first 1,000 for F3; 975 filtered development records for checkpoint selection. Test is unused. |
| Tibyan | Alrehili and Alhothali (2024) | 6,192 sentence pairs | Deterministic highlighted-token conversion; 2,000 project-training records for F2; nested first 1,000 for F3. |
| Nahw-Passage | Mubarak et al. (2026) | 100 passages; 511 correction records | Single frozen final test for all reported systems. |
| QALB 2015 L2 development | Rozovskaya et al. (2015) | 154 selected records | Matched already-correct-token diagnostic. |
| ArabicMMLU | Koto et al. (2024) | 14,575 questions across 40 tasks | Fixed balanced 1,000-question auxiliary capability diagnostic. |

## Split and leakage controls

- Nahw-Passage is test-only and is excluded from training, prompting,
  checkpoint selection, and development.
- QALB official train, development, and test roles are preserved. QALB test is
  not used anywhere in the study.
- QALB training candidates are filtered against registered QALB test and Nahw
  source hashes before selection.
- Tibyan has no official split. Exact source sides are grouped before a fixed
  hash-based 80:20 project train/development split, preventing identical source
  strings from crossing the project split.
- Tibyan candidates are checked against registered QALB and Nahw hashes. Exact
  overlaps are excluded; hash checks cannot detect paraphrases or unknown
  pretraining contamination.
- The mixed F3 view uses nested subsets of the frozen F1 and F2 orders rather
  than fresh samples.
- All final systems are evaluated on the same 511 ordered record identifiers.

## Transformation rules

QALB natural records retain only a single eligible token replacement with one
non-empty correction token and one occurrence of the erroneous token. Tibyan
sentence pairs are aligned by deterministic minimum edit, retaining one seeded
representative for each eligible source group. The repository does not assign
linguistic error categories to either source.

## Public and private artifacts

Public artifacts may contain release metadata, record counts, deterministic
selection rules, aggregate statistics, and hashes. They must not contain:

- QALB text or transformed QALB records;
- Nahw-Passage records copied from the private prepared input;
- ArabicMMLU questions or answers;
- record-level predictions, prompts, gold values, or model responses; or
- private development metrics, adapters, checkpoints, or logs.

The public scripts read restricted inputs only from ignored paths and write
text-bearing derivatives under ignored directories. Possession or hashing of
an artifact does not authorize redistribution. See
[`artifact_release_audit.md`](artifact_release_audit.md) for the full release
matrix.

## Authoritative sources

- Mohit et al. (2014), [The First QALB Shared Task on Automatic Text Correction for Arabic](https://aclanthology.org/W14-3621/)
- Rozovskaya et al. (2015), [The Second QALB Shared Task on Automatic Text Correction for Arabic](https://aclanthology.org/W15-3206/)
- Alrehili and Alhothali (2024), [Tibyan](https://arxiv.org/abs/2411.04588)
- Mubarak et al. (2026), [Nahw](https://aclanthology.org/2026.eacl-long.296/)
- Koto et al. (2024), [ArabicMMLU](https://aclanthology.org/2024.findings-acl.334/)
