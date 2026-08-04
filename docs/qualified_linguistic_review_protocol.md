# Qualified Arabic linguistic review protocol

Status: corpus-text-free preparation for issue #151. No private review package
has been generated or opened.

## Research purpose

The frozen automatic evaluation reports whether each model output exactly
matches the single supplied Nahw-Passage correction. Qualified review addresses
different questions:

1. Is a non-matching output nevertheless acceptable Modern Standard Arabic in
   the passage context?
2. Is the supplied reference correction valid, non-unique, questionable, or
   ambiguous?
3. Which published ARETA category best describes the supplied
   error/correction relationship, when a reviewer can judge it?
4. Is an apparent failure linguistic, a formatting failure, or genuinely
   indeterminate from the available context?

Expert review is a secondary analysis. It never replaces, edits, or tunes the
frozen exact-match result, model outputs, prompts, checkpoints, or systems.

## Reviewer qualification

At least one reviewer must have documented expertise relevant to Modern
Standard Arabic grammar. A PhD whose official specialization is stated broadly
as `اللغة العربية` is potentially sufficient for a single-expert review, but
the project must privately record the degree title, relevant teaching,
research, editing, or assessment experience, and the reviewer's confirmation
that they are comfortable judging Modern Standard Arabic corrections.

Public reporting uses only wording approved by the reviewer and does not name
an institution, person, or identifying credential unless the reviewer
separately consents.

With one qualified reviewer, the paper must say **single-expert review** and
must not imply inter-annotator reliability. A second independently qualified
reviewer is preferred.

## Frozen core scope

The recommended core scope is the complete 511-record matched F2-P1/F3-P1
evaluation. Each record presents:

- the passage and highlighted erroneous token;
- the supplied reference correction;
- two candidate outputs labeled only Candidate A and Candidate B; and
- a frozen, per-record random presentation order.

The reviewer never sees system names, training conditions, aggregate scores,
automatic correctness labels, or which candidate is F2-P1 or F3-P1.

An optional F1-P1 candidate may be added only as a separately declared
extension before the reviewer sees outputs. It is not required for the primary
F2-P1/F3-P1 expert comparison.

## Candidate judgment rubric

Each candidate receives exactly one judgment:

- **Exact supplied correction**: substantively the same correction as the
  supplied reference under the frozen comparison convention.
- **Acceptable alternative**: differs from the supplied reference but is an
  acceptable correction in context.
- **Incorrect**: not an acceptable correction in context.
- **Output-format failure**: the response format prevents a valid
  highlighted-token correction judgment.
- **Ambiguous / insufficient context**: the passage does not support a
  confident correctness judgment.
- **Unable to judge**: the reviewer cannot responsibly decide for another
  reason, stated privately.

The reviewer also records high, medium, or low confidence and may give a
private rationale. Spelling, punctuation, diacritics, hamza forms, morphology,
syntax, and contextual acceptability are in scope only as required to decide
whether the proposed correction is acceptable in the supplied context.

## Reference-quality rubric

Each record receives exactly one reference judgment:

- valid and sufficiently supported;
- acceptable but non-unique;
- questionable;
- ambiguous / insufficient context; or
- unable to judge.

This judgment is reported separately from candidate acceptability.

## Error categories

The workbook exposes ARETA's published seven-class, 26-tag supported inventory
as a candidate vocabulary. It does not invent Arabic labels or examples.

The reviewer may select one primary class and tag, optional secondary tags, or
leave the category unable to judge. Any wording change or taxonomy adaptation
requires written reviewer approval before outputs are disclosed. Automatic
ARETA labels, if later provided as diagnostics, are never expert gold.

## Two-reviewer procedure

If a colleague joins:

1. each reviewer completes a separate qualification and consent form;
2. each receives a separate, access-controlled workbook with the same frozen
   record identities and blinding;
3. reviewers work independently and do not discuss records before submission;
4. the statistic is selected before judgments are opened;
5. report raw agreement and Cohen's kappa for the mutually exclusive
   candidate-judgment labels, with denominators and missing/indeterminate cases
   stated explicitly; and
6. disagreements are adjudicated only after both original workbooks are
   preserved, using a predeclared consensus meeting or a separately qualified
   adjudicator.

The original judgments remain immutable. Adjudicated judgments form a
separate field and summary.

## Calibration and quality control

The reviewer first approves the written rubric without seeing outputs. A
private 20-record calibration batch may then be used only to resolve
instruction ambiguity. If the rubric changes, its version and hash change and
all calibration records are re-annotated under the final rubric.

The final package includes completion formulas but no automatic linguistic
decision. Hidden duplicates may be used only if approved before package
generation; they are reported as a quality-control diagnostic, not a reason to
discard an inconvenient judgment.

## Privacy, access, and retention

Populated workbooks contain benchmark text, supplied corrections, and private
model outputs. They must remain in an access-controlled private workspace.
They must not be uploaded to SciSpace, public GitHub, public chat, or
uncontrolled email; copied into public notes; or used for another purpose.

Before access, each reviewer records:

- who may access the package;
- the approved transfer method;
- whether local copies are permitted;
- the return date;
- the deletion or retention date; and
- consent for nonidentifying qualification wording and aggregate publication.

The public repository receives only corpus-text-free counts, hashes,
qualification scope, agreement statistics, adjudication counts, limitations,
and reviewer-approved interpretation language.

## Analysis and paper claims

The predeclared secondary analysis may report:

- per-system exact-or-acceptable counts and rates;
- the paired F3-P1 minus F2-P1 expert-acceptability difference with a paired
  confidence interval;
- counts of acceptable alternatives;
- candidate-judgment distributions;
- output-format-failure counts;
- reference-quality distributions;
- ARETA class/tag distributions on the stated denominator;
- reviewer agreement and adjudication counts when two reviewers participate;
  and
- sensitivity analyses that separately retain ambiguous and unable-to-judge
  records.

The analysis must not convert expert review into a new training signal, prompt
choice, checkpoint choice, or model-selection criterion.

## Authorization boundary

This protocol and its blank workbook do not authorize private prediction
access, corpus export, review-package population, reviewer access, annotation,
or publication of examples. Those steps require the owner to confirm the
reviewer, scope, transfer method, retention terms, exact frozen artifacts, and
a fresh private-data authorization in a dedicated issue.
