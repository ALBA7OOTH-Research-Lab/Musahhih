# QALB 0.9.1 intake report

Date: 2026-06-23

## Provenance and handling

- Release: `QALB-0.9.1-Dec03-2021-SharedTasks`
- Archive size: 94,288,190 bytes
- Archive SHA-256: `c14764b01439618bdcebda04bd5b9365cd70a1fbc58607f1bd18cf357514e503`
- Archive inventory: 277 ZIP entries, including 220 files; 424,377,838 uncompressed bytes
- Safety check: no absolute paths, path traversal entries, or encrypted entries
- Local raw location: `data/raw/qalb/` (ignored by Git)

The license grants no-fee use and copying solely for internal research and evaluation. It does not grant redistribution, sublicensing, dataset modification, assignment, or commercial rights. Raw QALB data therefore remains private and untracked. The original archive, `README.txt`, and `LICENSE.txt` are retained locally without modification. Processing should use manifests that reference unchanged records; obtain institutional guidance before creating persistent transformed corpus copies.

For routine work, the original `.sent`, `.cor`, and `.m2` files were extracted byte-for-byte. Large `.column` feature files, submitted-system outputs, and archival documents were not extracted; they remain available inside the original ZIP.

## Split integrity

| Split | Records | Unique IDs | Duplicate source records | M2 annotation lines |
|---|---:|---:|---:|---:|
| QALB-2014 L1 train | 19,411 | 19,411 | 105 | 306,757 |
| QALB-2014 L1 dev | 1,017 | 1,017 | 1 | 16,659 |
| QALB-2014 L1 test | 968 | 968 | 3 | 16,378 |
| QALB-2015 L1 test | 920 | 920 | 12 | 13,299 |
| QALB-2015 L2 train | 310 | 310 | 0 | 13,206 |
| QALB-2015 L2 dev | 154 | 154 | 0 | 7,293 |
| QALB-2015 L2 test | 158 | 158 | 0 | 6,647 |

Checks performed directly against the supplied ZIP and again against the selected extraction:

- every `.sent`, `.cor`, and `.m2` file decodes as UTF-8 with BOM handling;
- source, corrected, and M2 document counts agree within every split;
- ordered `.sent` source text exactly matches ordered M2 `S` records;
- every document ID is unique within its official split;
- no exact QALB source document matches any of the 100 unique Nahw-Passage passages.

There are 22,938 records and 22,816 unique source strings across the seven distributed split/track combinations. The difference includes documented duplicates within splits and one exact cross-split duplicate.

## Leakage finding

One source string occurs in both QALB-2015 L2 train and test under different document IDs. The source and corrected text are identical, meaning it is an already-correct record. To identify it without publishing corpus text:

- source UTF-8 SHA-256: `32f52ef800b5292b2b3df1e0dfe6ba5b6254d25a32dbad12909dcd8e1f144e5b`
- source length: 34 Unicode code points
- train ID: `S941_T1_M_Pre_NNAS_S_C_002.ar`
- test ID: `S257_T2_M_Pre_NNAS_W_C_002.ar`

The official raw files must remain unchanged. Before any training run, a private selection manifest must exclude the train-side record at load time and record that decision. All QALB test splits remain strictly evaluation-only.

## Decision

QALB 0.9.1 is accepted for internal research preparation subject to its license. No QALB model training or benchmark evaluation was run during this intake.
