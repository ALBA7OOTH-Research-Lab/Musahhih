# QALB Selection Manifests Design

Date: 2026-06-23
Status: Approved for implementation planning

## Objective

Create deterministic, private selection manifests for QALB 0.9.1 without copying QALB corpus text into generated files or Git. The manifests will identify which unchanged archive records may be used for training and development while keeping all official test records evaluation-only.

## Constraints

- Read QALB directly from the original registered ZIP archive.
- Never modify the archive or its members.
- Never write source sentences, corrected sentences, M2 annotations, or other QALB corpus text into generated manifests.
- Never commit the QALB archive, extracted data, or generated private manifests.
- Preserve the multiplicity of exact duplicate sources within an official training or development split and flag those records instead of removing them.
- Exclude any training or development record whose exact source text appears in an official QALB test split.
- Exclude any training or development record whose exact source text matches a Nahw-Passage passage.
- Do not normalize Arabic text before hashing or overlap comparison.
- Keep every QALB test split evaluation-only.
- Do not create persistent transformed QALB corpus copies without institutional guidance on the supplied license.

## Approaches considered

### Complete registry plus selection manifests — selected

Generate one complete text-free registry and separate eligible train and development selections. This provides an auditable account of every official record and every exclusion while keeping downstream loading simple.

### Selection files only

Generate only train and development selections. This is smaller, but excluded and test records would not have a durable audit trail.

### SQLite index

Store records and selection queries in SQLite. This would support richer exploration but adds unnecessary tooling and makes simple version/hash comparisons less transparent.

## Inputs

The command-line script accepts:

- `--archive`: the original `QALB-0.9.1-Dec03-2021-SharedTasks.zip` path;
- `--nahw-passage`: the original UTF-8 `Nahw-Passage.json` path;
- `--output-dir`: a private, Git-ignored output directory.

Repository defaults point to the existing locations under `data/raw/` and `data/processed/`. Explicit arguments allow tests and team members to use other private locations.

The script requires the archive root `QALB-0.9.1-Dec03-2021-SharedTasks`, its root `README.txt` and `LICENSE.txt`, and these seven split/track groups:

- QALB-2014 L1 train, dev, and test;
- QALB-2015 L1 test;
- QALB-2015 L2 train, dev, and test.

Each group requires its `.sent`, `.cor`, and `.m2` members. Other archive members are ignored.

## Validation and data flow

1. Verify the ZIP has no absolute, traversal, or encrypted members.
2. Compute the SHA-256 of the original archive and every required member.
3. Decode required text members with UTF-8 BOM handling. Invalid UTF-8 is fatal.
4. Parse each `.sent` row as a document ID followed by the exact source text.
5. Parse each `.cor` row as `S ` followed by the exact corrected text.
6. Read the ordered `S ` records from `.m2`.
7. Require equal `.sent`, `.cor`, and M2 source counts, unique document IDs within each split, and exact ordered equality between `.sent` source text and M2 sources.
8. Compute SHA-256 values from the exact UTF-8 source and corrected strings after removing only their file-format prefixes. No linguistic or Unicode normalization is applied.
9. Compare exact source hashes across official splits and against exact Nahw passage hashes.
10. Build the complete registry, then derive train and development selections from eligibility flags.
11. Write all outputs with UTF-8 and LF line endings only after every input and record passes validation.

No output is written when validation fails.

## Record schema

Every JSONL record contains only metadata and derived identities:

- `record_key`: stable release, split, line, and document identifier;
- `release`: `0.9.1`;
- `year`: `2014` or `2015`;
- `track`: `L1` or `L2`;
- `split`: `train`, `dev`, or `test`;
- `document_id`: the original document ID;
- `line_number`: one-based line number in the `.sent` and `.cor` members;
- `sent_member`, `cor_member`, and `m2_member`: archive-relative member paths;
- `source_sha256` and `correction_sha256`;
- `source_codepoints` and `correction_codepoints`;
- `source_equals_correction`;
- `duplicate_source_within_split`;
- `exact_source_overlap_with_qalb_test`;
- `exact_source_overlap_with_nahw`;
- `eligible_for_training`;
- `eligible_for_development`;
- `selection_reason`.

The schema deliberately contains no source, correction, annotation, prompt, or completion field.

## Selection policy

Training records are eligible only when they belong to an official train split and their exact source appears in neither an official QALB test split nor Nahw-Passage. Development records follow the same rule for official dev splits.

Within-split duplicate sources remain present and eligible when no test overlap exists. Every occurrence is marked with `duplicate_source_within_split=true`, allowing later experiments to define a separately versioned deduplication policy without silently changing this official-distribution view.

Test records are never eligible for training or development. Records excluded by multiple protections retain all boolean flags; `selection_reason` uses a deterministic ordered list of reasons.

## Outputs

The output directory contains:

- `qalb_registry.jsonl`: all seven official split/track groups;
- `qalb_train_selection.jsonl`: eligible official training records only;
- `qalb_dev_selection.jsonl`: eligible official development records only;
- `qalb_manifest_summary.json`: schema version, archive/member hashes, Nahw input hash, official and selected counts, duplicate counts, overlap counts, selection policy, and output file hashes.

The summary contains no generation timestamp so identical inputs and code produce byte-identical outputs. Paths recorded in the summary are archive-relative or repository-relative, never machine-specific absolute paths.

For the currently audited QALB archive, the expected high-level counts are 22,938 registry records, 19,720 eligible training records, and 1,171 eligible development records. The training count excludes the one known QALB-2015 L2 train source that exactly overlaps QALB-2015 L2 test. These expectations are validation assertions, not hard-coded substitutes for parsing the archive.

## Error handling

The script exits nonzero with a concise message when an input is missing, unsafe, encrypted, malformed, incorrectly encoded, incomplete, internally misaligned, or inconsistent with the required release layout. It does not attempt to repair corpus text, infer missing rows, normalize Arabic, or continue with partial outputs.

Existing output files may be replaced only after successful validation and complete in-memory generation. Rerunning with identical inputs must produce identical bytes.

## Testing

Tests construct a small synthetic ZIP in a temporary directory; they never embed or copy real QALB records. The suite verifies:

- within-training duplicate records are preserved and flagged;
- a train record matching an official test source is excluded;
- a development record matching a Nahw passage is excluded;
- test records are never selected;
- generated JSONL contains no corpus-text fields or values;
- malformed counts, duplicate IDs, M2 mismatches, invalid UTF-8, and unsafe ZIP paths fail before output;
- LF-only, deterministic output is reproduced on rerun;
- the command-line defaults and explicit paths behave as documented.

The existing repository test suite and `python -m compileall scripts` remain required validation.

## Repository and research documentation

Implementation adds one reusable script under `scripts/` and focused tests under `tests/`. The generated manifests remain under ignored `data/processed/qalb/`. `README.md` and `docs/dataset_audit.md` will document the command, privacy boundary, selection counts, and test-only safeguards without exposing corpus content.

The Musahhih Research Hub task will link to the design and implementation commit and record the final verified counts and hashes.
