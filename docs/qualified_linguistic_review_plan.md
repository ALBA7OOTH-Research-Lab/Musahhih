# Qualified linguistic error-review plan

Status: planning draft. No reviewer selected and no record-level review
authorized.

## Purpose

Aggregate exact match answers whether a system reproduced the supplied
correction. It does not explain whether a different output is an acceptable
alternative, which grammatical phenomena improved, or whether an apparent
error category is linguistically well formed.

Those questions require qualified Arabic linguistic review. Codex, automatic
tools, and non-specialist project members must not create or validate Arabic
error labels.

## Minimum reviewer qualifications

The owner should recruit at least one reviewer with documented expertise in
Modern Standard Arabic grammar or Arabic grammatical error correction.
Preferred evidence includes:

- an advanced degree or research record in Arabic linguistics;
- professional Arabic language editing or assessment experience;
- peer-reviewed Arabic GEC, grammar, or annotation work; or
- equivalent documented subject-matter expertise accepted by the project
  owners.

Two independent reviewers plus adjudication are preferable for category-level
claims. With only one reviewer, report the work as a single-expert review and
do not imply inter-annotator reliability.

## Scope options

The owner must choose one scope before any private artifact is opened:

1. **Alternate-correction review:** inspect model outputs marked wrong by exact
   match and decide whether an output is acceptable in context.
2. **Error-category review:** assign externally sourced grammatical categories
   to the supplied error/correction relationship.
3. **Comparative failure review:** explain a content-neutral sample of
   F3-P1/F2-P1 discordant outcomes.
4. **Output-quality review:** assess multi-token, malformed, or explanatory
   outputs separately from linguistic correctness.

Do not combine these tasks into one vague “expert score.” Each requires its own
rubric and denominator.

## Sampling

Freeze sampling before the reviewer sees text or model identities.

Recommended comparative sample:

- start from the 121 F2-P1/F3-P1 discordant records;
- rank record identities by
  `SHA256("F2-F3-linguistic-review|3407|<record-id>")`;
- take a predeclared number from each discordant direction;
- blind system identity and randomize presentation order; and
- retain the full 511-record denominator when reporting how the reviewed sample
  was obtained.

If reviewing exact-match failures more broadly, define separate content-neutral
samples for each system. Do not choose examples because they look interesting
or support the preferred conclusion.

The sample size, identity digest, and balance must be committed as text-free
metadata before record text is exported to the review environment.

## Rubric design

The rubric must be written or approved by the qualified reviewer before model
outputs are revealed. It should distinguish:

- exact supplied correction;
- acceptable alternative correction;
- incorrect correction;
- insufficient context or genuinely ambiguous case;
- output-format failure; and
- unable to judge.

Any grammatical category inventory must come from a cited external source such
as ARETA or another qualified Arabic taxonomy and must be adapted only with the
reviewer's written approval. Automatic ARETA output may be shown as an
unvalidated diagnostic aid, never as expert gold.

The rubric must state whether spelling, punctuation, diacritics, hamza forms,
morphology, syntax, and semantic/contextual acceptability are in scope.

## Blinding and adjudication

- hide system labels and training conditions;
- do not show aggregate system scores;
- randomize output order within each record;
- include duplicate hidden calibration items only if the reviewer approves;
- capture reasons in private structured fields;
- if two reviewers disagree, use a predeclared adjudication procedure; and
- never modify model predictions or the original automatic exact-match result.

If two reviewers participate, report raw agreement and an appropriate
reliability statistic selected with methodological review. Do not choose a
statistic after seeing which one looks favorable.

## Privacy and licensing

The review package may contain benchmark passages, gold corrections, and model
outputs. It therefore remains private even where the upstream benchmark is
public.

- use an access-controlled private workspace;
- share only the minimum selected records;
- prohibit copying into public email, chat, issues, or pull requests;
- record reviewer access and deletion/retention expectations;
- do not include QALB text unless its separate license procedure explicitly
  permits the planned review; and
- publish examples only after upstream-license and privacy review.

Public evidence should normally be aggregate counts, rubric/version hashes,
sample-selection hashes, reviewer qualification scope, agreement statistics,
and limitations—not record text.

## Required artifacts

Before review:

- reviewer-approved rubric and version hash;
- qualification statement approved for public wording;
- frozen scope, sample size, selection rule, and identity digest;
- private-data access and retention plan;
- blinded package generator with synthetic tests; and
- exact owner authorization.

After review:

- private record-level judgments and adjudication log;
- corpus-text-free aggregate summary;
- audit of counts, identities, blinding, and rubric version;
- reviewer-approved interpretation language; and
- explicit statement of whether the review changes only interpretation or also
  supplies a separately reported alternate-correction metric.

## Authorization boundary

This plan does not authorize opening private predictions, sampling records,
exporting review packages, contacting a reviewer on the owner's behalf, or
publishing examples. The owner must first identify the reviewer, approve the
scope, and create a dedicated issue with the private-data procedure.
