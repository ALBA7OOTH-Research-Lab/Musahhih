# Qualified linguistic review package preparation audit

Status: corpus-text-free preparation complete for issue #151. No private
review package has been populated or opened.

## Scope completed

- added the reviewer qualification and scope protocol;
- prepared an editable expert-reviewer packet with:
  - an English and Arabic invitation;
  - qualification and availability questions;
  - confidentiality, retention, consent, and credit terms;
  - the blinded candidate and reference-quality rubrics;
  - the published ARETA seven-class, 26-tag supported inventory;
  - single-reviewer and two-independent-reviewer procedures;
  - pre-adjudication agreement and adjudication rules; and
  - reviewer-approved paper-language templates;
- prepared a blank 511-row annotation workbook with validation lists,
  completion formulas, QC flags, a reviewer profile, a label guide, and a
  completion gate.

The package contains no benchmark passage, supplied correction, model output,
prediction, private metric, reviewer identity, credential, token, or model
artifact.

## Qualification boundary

An official PhD specialization stated as `اللغة العربية` is treated as
potentially sufficient for a **single-expert review** only after the reviewer
records relevant Modern Standard Arabic teaching, research, editing,
assessment, or annotation experience and confirms comfort with the task.

The protocol does not claim specialized Arabic GEC expertise unless that
experience is actually documented and the reviewer approves the public
wording. With one reviewer, the paper must make no inter-annotator reliability
claim. A second independently qualified reviewer is preferred.

## Frozen methodological decisions

- recommended core scope: all 511 frozen F2-P1/F3-P1 records;
- two candidates per record, with system identity and aggregate results hidden;
- reviewer approves the rubric before outputs are disclosed;
- candidate labels remain mutually exclusive;
- reference quality is a separate judgment;
- ARETA categories remain optional candidate expert labels, not automatic gold;
- two reviewers work independently until both original submissions are
  preserved;
- raw agreement and Cohen's kappa are selected before judgments are opened;
- adjudication creates a separate field and never overwrites original
  judgments; and
- expert review changes interpretation only, not predictions, exact-match
  results, prompts, checkpoints, or model selection.

## Local deliverable identities

- `Musahhih_Arabic_Expert_Reviewer_Packet.docx`
  - SHA-256:
    `f19f67f88894ca51f75d790bb894c2f2881f6b00566e99d1eedc86885114fdad`
- `Musahhih_Blinded_Review_Template.xlsx`
  - SHA-256:
    `af9d26d73384b97a28f8eabf4593c303feed36160d9d5c41c8f64cf5a232da46`

These local deliverables are intentionally ignored rather than committed.

## Validation

- workbook inspection found no formula-error strings;
- the blank workbook reports zero populated records, zero QC flags, and a
  zero-percent completion rate;
- every workbook sheet was rendered and visually inspected, including three
  readable annotation-sheet segments;
- all annotation categorical fields have constrained validation lists;
- the DOCX opened successfully in Microsoft Word and reported 19 pages;
- the DOCX contains 138 paragraphs, 28 real heading-style paragraphs, and 23
  tables;
- the packaged table-geometry audit confirmed exact matching `tblW`,
  `tblInd`, `tblGrid`, and `tcW` values for every table; and
- the heading audit confirmed the expected Heading 1 and Heading 2 structure.

The packaged LibreOffice renderer could not start because no LibreOffice
executable is installed in this Windows environment. Microsoft Word opened the
document, but its PDF export did not complete within the bounded QA attempts.
Consequently, DOCX page-image review remains a delivery-side limitation even
though Word open, page count, structure, style, and table geometry were
validated.

## Authorization boundary

This preparation does not authorize opening private predictions, selecting or
exporting records, populating a workbook, granting reviewer access, beginning
annotation, publishing examples, running inference, training, rerunning an
evaluation, or changing any frozen research decision.

The next private step requires a fresh owner authorization naming the confirmed
reviewer scope, approved rubric version and hash, exact frozen artifact hashes,
transfer method, access list, return date, and deletion or retention plan.
