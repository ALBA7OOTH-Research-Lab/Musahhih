# Private Arabic linguistic-review package audit

Date prepared: 2026-07-29

## Status

The owner explicitly requested a concise Arabic package populated with the
actual frozen review material. Issue #153 records the private scope and access
boundary.

The private package contains all 511 aligned F2-P1/F3-P1 Nahw-Passage records.
It presents only:

- a blinded item number;
- the passage;
- the highlighted erroneous word;
- the supplied reference correction;
- anonymous Candidate A and Candidate B;
- Arabic judgment fields;
- an optional reviewer-supplied error description and note; and
- a formula-driven completion status.

It does not disclose system identity, training condition, aggregate score,
automatic exact-match result, parsing-warning field, prompt, checkpoint, or
model metadata.

## Source identities

- accepted F2-P1 predictions SHA-256:
  `ca4a6eb2f5e40a60be14f59cdc7365a0f327b41ab0b8f46c8a08c43cfb442753`;
- accepted F3-P1 predictions SHA-256:
  `ccb296e0f091bf28ebe4d7c8b9ed454934f4dade0b5793dcf1b3a5706379c35c`;
- source rows per arm: 511;
- unique ordered record identities per arm: 511; and
- passage, passage ID, erroneous word, supplied correction, source, split, and
  record identity matched exactly between aligned arms.

The displayed candidate string is the exact stored parsed correction. For both
arms, it is byte-for-byte equal to the stored raw model response on all 511
records. No response was repaired, truncated, normalized, or rewritten.

## Blinding

Candidate order was fixed independently for every record using:

`SHA256("musahhih-qualified-arabic-review-v1|3407|" + record_id)`

The low bit of the first digest byte determines whether the two arms are
swapped. The resulting Candidate A allocation is:

- F2-P1: 257 records; and
- F3-P1: 254 records.

The private mapping is stored separately from the reviewer workbook.

- blinded private records SHA-256:
  `a1e17678bc17b62626bab86a3066bb89e8e7e01513fa6c0e18efb5bbc97e4b36`;
- private candidate mapping SHA-256:
  `f6d2fdc2f31269c6a9635154481e230c730ec04c63f6870a164bf77d51ed8d17`.

## Reviewer-facing files

- one-page Arabic instructions DOCX SHA-256:
  `54d7b2d7551fb9bb6ad3de53124d26066d23c1e1857183a3dc989168047c557f`;
- populated 511-record Arabic XLSX SHA-256:
  `0649defd0b9cf63ff4ab5ebd14a9d32cd50cb006d4d4234b881b9acb7775dad9`.

Both files remain in ignored local output storage. The XLSX contains 512 rows
on the review sheet, including one header row.

## Validation

- exact accepted source hashes passed;
- every source arm contains 511 unique records;
- all shared identity and reference fields align;
- all displayed candidates are nonempty;
- the workbook contains zero F2-P1/F3-P1 labels and zero automatic-score,
  prompt, parsing-warning, or raw-response field names;
- Arabic dropdowns constrain both candidate judgments and reference-quality
  judgments;
- completion formulas report 0 complete and 511 remaining before annotation;
- the workbook formula-error scan returned zero matches;
- the instruction and review-header sheets were rendered and visually checked
  without rendering private record text into a public tool response;
- Microsoft Word opened the Arabic instruction document as one page; and
- all DOCX tables passed exact width, grid, indent, and cell-width geometry
  checks.

The packaged DOCX renderer could not start because LibreOffice is not installed
in this Windows environment. Accordingly, DOCX PNG rendering was unavailable;
Word open/page-count and structural audits were used as the documented
fallback.

## Privacy and use boundary

The populated package and mapping are private. They must not be committed,
uploaded to a public AI service, placed in public chat or issues, or shared
beyond the owner and the specifically selected reviewer(s).

If a second qualified reviewer participates, the owner must give that reviewer
a separate copy and require independent work. Original returned files must be
preserved before any comparison or adjudication.

The judgments may support a separately reported expert acceptability and
reference-quality analysis. They do not authorize training, inference,
checkpoint selection, prompt or parser changes, prediction edits, a repeated
evaluation, or publication of record text.
