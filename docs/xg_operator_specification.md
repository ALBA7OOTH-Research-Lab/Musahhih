# XG Gender-Agreement Operator Eligibility and Validation Specification

Status: draft no-go specification. `XG` remains disabled. This document does
not authorize implementation, candidate generation, registry changes, or model
training.

GitHub issue: https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/24

## Purpose

This specification defines the minimum evidence and validation contract that a
future, tiny private `XG` feasibility pilot would have to satisfy. It is written
before any Arabic candidate is created and without inspecting Nahw-Passage,
private QALB text, Tibyan examples, or model outputs.

The current decision is **no-go for implementation**. Two blocking requirements
remain unresolved:

1. a qualified linguistic review has not approved the exact relationship among
   lexical gender, form gender, and the surface feature transition; and
2. the required independent qualified MSA reviewers and adjudicator have not
   been identified and consented.

Resolving those blockers requires a separate reviewed protocol revision. It
must not be silently handled in code.

## Authoritative sources and evidence roles

### MSA agreement sources

- Karin C. Ryding, *A Reference Grammar of Modern Standard Arabic*, Cambridge
  University Press, 2005, Chapters 5 and 10, especially pages 124–127 and
  239–246. DOI: <https://doi.org/10.1017/CBO9780511486975>.
- Lindley Winchester, “Concord and agreement features in Modern Standard
  Arabic,” *Glossa* 4(1):91, 2019. DOI:
  <https://doi.org/10.5334/gjgl.710>.
- QALB L2 correction guidance, which includes gender agreement among documented
  syntactic phenomena: <https://aclanthology.org/W15-1614/>.

Ryding and Winchester support the following source claims:

- An attributive adjective follows and directly modifies its noun and agrees in
  gender, number, case, and definiteness.
- Predicative adjective behavior differs, so predicative constructions cannot
  be pooled with attributive modification.
- Agreement for plural nouns depends on humanness and other morphosyntactic or
  semantic properties. Nonhuman plurals use a distinct agreement pattern.
- Dual-gender nouns, collective or people-denoting nouns, abstraction readings,
  non-gendered adjectives, and comparative/elative forms create exceptions or
  ambiguity that a first study must not assume away.

These sources justify investigating a tightly bounded attributive relation.
They do not provide a machine-executable operator, a safe method for inferring
lexical gender or humanness from raw text, or proof that a generated alternative
preserves meaning.

### Tool and annotation sources

- ARETA paper and `XG` diagnostic label:
  <https://aclanthology.org/2021.conll-1.47/>.
- CAMeL morphology feature inventory:
  <https://camel-tools.readthedocs.io/en/stable/reference/camel_morphology_features.html>.
- CAMeL analyzer, generator, and reinflector documentation:
  <https://camel-tools.readthedocs.io/en/stable/api/morphology/analyzer.html>,
  <https://camel-tools.readthedocs.io/en/stable/api/morphology/generator.html>,
  and
  <https://camel-tools.readthedocs.io/en/stable/api/morphology/reinflector.html>.
- CAMELMORPH MSA analyzer/generator, Khairallah et al., 2024:
  <https://aclanthology.org/2024.lrec-main.240/>.
- CAMeL contextual disambiguator documentation:
  <https://camel-tools.readthedocs.io/en/stable/api/disambig/bert.html>.
- Universal Dependencies Arabic PADT metadata and Stanza dependency parser
  documentation: <https://universaldependencies.org/treebanks/ar_padt/> and
  <https://stanfordnlp.github.io/stanza/depparse.html>.

CAMeL distinguishes `gen` (gender) from `form_gen` (form gender), and similarly
distinguishes number from form number. These fields must not be treated as
synonyms. Analyzer, generator, and reinflector calls may return multiple
analyses or surfaces. A nonempty result establishes morphology-database
compatibility, not contextual grammaticality or uniqueness.

ARETA classifies aligned erroneous/reference edits. An `XG` output is a
diagnostic prediction, not proof that an edit creates exactly one gender error.
A dependency parser predicts a relation; it does not certify the corresponding
Arabic agreement rule.

## Proposed relation scope

If the two blockers are later resolved, the first pilot may consider only an
attributive adjective directly modifying one singular noun within one MSA
sentence. Predicative constructions and all plural or dual heads are excluded.

This proposed scope is intentionally narrower than the ARETA `XG` label. It is
not a new linguistic category; it is a project eligibility envelope for studying
one documented agreement relation. The source label remains `XG`.

The future operator specification must name the exact dependency relation,
eligible noun and adjective parts of speech, CAMeL feature transition, and
licensed morphology database. Those details are currently unresolved and no
default may be inferred from the prose below.

## Source eligibility contract

A clean source would be eligible only if every condition passes before any
candidate surface is requested:

1. The source comes from a registered, licensed training-only clean-text pool.
   Evaluation data, QALB development/test, and Nahw-Passage are prohibited.
2. The exact UTF-8 source, source license, record identity, checksum, split, and
   source-group identity are recorded privately.
3. A qualified MSA reviewer has accepted the clean source as well formed under
   the frozen relation scope; a parser or language model cannot provide this
   acceptance.
4. Tokenization identifies exactly one target adjective and one noun head with
   stable indices and no multiword-token expansion.
5. The relation is attributive rather than predicative, coordinated,
   appositional, elliptical, or otherwise outside the reviewed inventory.
6. The noun is singular, not dual-gender, collective, or lexically/syntactically
   ambiguous in gender under the registered lexicon.
7. The adjective is an ordinary gender-inflecting adjective, not a documented
   non-gendered or comparative/elative form. Any additional lexical exclusion
   requires a cited definition in the future reviewed inventory.
8. Source analyses are unique under the frozen disambiguation rule for lemma,
   part of speech, `gen`, `form_gen`, `num`, `form_num`, state/definiteness,
   case, and every other declared invariant.
9. No required feature is unknown, unavailable, backoff-generated, or supported
   only by an analyzer normalization that changes the exact source spelling.
10. No other source token participates in an agreement cascade or would require
    a second edit.

These predicates are fail-closed. Missing evidence rejects the source; it does
not trigger a guess, fallback model, or manual exception during generation.

## Explicit source exclusions

Reject all cases involving:

- plural or dual heads;
- humanness-dependent, collective, abstraction, or people-denoting agreement;
- dual-gender or lexically inconsistent nouns;
- source-documented non-gendered or comparative/elative adjectives;
- predicted relations that differ across registered parser models or change
  after the prospective edit;
- coordination, ellipsis, apposition, multiword expressions, clitic-boundary
  changes, or tokenization instability;
- unknown or multiple surviving lemma/POS/gender/form-gender analyses;
- syncretic forms where the intended contrast is not uniquely visible in exact
  undiacritized text;
- cases whose alternative surface also has an unchanged-gender analysis;
- compound ARETA categories or any evidence of another simultaneous error;
- sensitive personal text, offensive content, or uncertain licensing; and
- any exact or near overlap with a registered evaluation source.

The exclusion list may be expanded through reviewed evidence. It may not be
relaxed after seeing pilot or final-test performance.

## Unresolved gender-feature transition

The exact prospective change is deliberately unspecified. CAMeL exposes both
`gen` (gender) and `form_gen`; the reviewed sources do not establish a universally
safe rule that toggles one or both fields for every eligible adjective.

Before implementation, a qualified linguist and morphology-tool reviewer must
approve a versioned feature-transition appendix that states:

- which field expresses lexical eligibility;
- which field expresses the intended observable form contrast;
- whether and when the fields must agree;
- all permitted source and target bundles;
- the treatment of case, state/definiteness, number/form number, clitics, and
  diacritics; and
- the evidence for excluding every other bundle.

Until that appendix is merged, there is no executable XG operator specification.

## Mechanical one-edit and inverse contract

Any future implementation must satisfy all of these mechanical requirements:

1. Only one predeclared adjective token may differ between clean and candidate
   strings; token count and all other exact UTF-8 substrings remain unchanged.
2. The stored target offsets use a declared offset unit and identify the exact
   original string before transformation.
3. The original token, candidate token, analysis bundles, tool versions, and
   generation query are retained privately.
4. Replacing the candidate token with the stored original must reproduce the
   byte-for-byte clean UTF-8 string.
5. The candidate surface must differ visibly from the original without relying
   on undocumented normalization or hidden diacritics.
6. Generation or reinflection must yield exactly one surviving exact surface
   after all frozen rejection checks. Zero or multiple surfaces reject the item.
7. Round-trip analysis must preserve lemma identity, part of speech, number,
   form number, state/definiteness, case, clitics, and every frozen invariant.
   Only fields approved by the future transition appendix may differ.
8. Reanalysis of the candidate must not admit a surviving unchanged-gender or
   alternative-lemma interpretation under the frozen ambiguity rule.
9. Parser tokenization, indices, head, and relation must remain unchanged.

Mechanical success does not establish that the candidate is linguistically
invalid or that the original is uniquely correct. Human validation remains
mandatory.

## Pinned tool contract

A future pilot must record:

- Python, CAMeL Tools, morphology database/package, disambiguator, parser,
  parser model/treebank, tokenizer, and ARETA versions or revisions;
- analyzer normalization flags, backoff setting, feature inventory, and exact
  generator/reinflector inputs;
- every raw analysis and generated surface before filtering; and
- deterministic selection, tie, confidence/margin, and rejection settings.

Required fail-closed behavior:

- reject out-of-vocabulary and backoff-only analyses;
- reject unknown (`u`) or unavailable (`na`) values for decision features;
- reject tied or multiple surviving contextual analyses rather than trusting a
  top-1 rank;
- compare exact Unicode separately from analyzer-normalized forms;
- reject any material change to the target or invariant-neighbor analyses after
  the prospective edit;
- use dependencies only as a candidate filter, never sole proof of agreement;
  and
- use ARETA only as an after-the-fact diagnostic. `XG` output cannot override a
  failed check, and lack of `XG` cannot be manually overridden.

No paid API or paid compute is permitted or necessary for this contract.

## Qualified linguistic review protocol

The design principles—written guidelines, independent coding, locked labels,
agreement measurement, and post-label adjudication—follow established corpus
annotation methodology, including Artstein and Poesio, 2008,
<https://aclanthology.org/J08-4004/>, and Pustejovsky and Stubbs, 2012,
*Natural Language Annotation for Machine Learning*.

The following thresholds and logistics are conservative Musahhih project
choices, not universal methodological facts or a statistical power claim.

### Reviewers

- Two independent reviewers must have postgraduate training in Arabic
  linguistics, Arabic philology, or a closely relevant discipline, plus
  demonstrated MSA morphosyntax work through publication, teaching, corpus
  annotation, or professional editing.
- A third qualified reviewer adjudicates only after independent labels lock.
- The operator author or developer cannot annotate or adjudicate.
- Record relevant qualifications, annotation experience, dialect/standard-
  language background, conflicts, consent, and compensation privately.

### Calibration and pilot material

- Use 6–8 separate licensed calibration items to clarify the written rubric.
  They never enter the scored pilot.
- Freeze a versioned guide after calibration. A substantive guide change
  invalidates the scored batch and requires fresh material.
- The first scored feasibility batch contains 30 randomized pairs: 20 attempted
  candidates plus 10 hidden controls, with five acceptable MSA controls and five
  invalid or out-of-scope controls.
- A control key must come either from an independently licensed authoritative
  gold source or from two qualified linguists who are not pilot reviewers and
  who agree independently before the batch freezes. Disagreement excludes the
  proposed control before randomization; controls are never replaced afterward.
- All material must be licensed, training/development-only, source-group
  isolated, and disjoint from every evaluation set.
- This is a diagnostic convenience sample. It supports no population,
  prevalence, representativeness, or production-readiness claim.

### Blinding and labels

Reviewers work independently without communication until label lock. Hide the
operator name, intended direction, generation method, developer identity,
candidate/control status, provenance, and the other reviewer's answers. Randomize
item order and independently randomize A/B order for each reviewer.

Each reviewer assigns closed labels, including `uncertain`, for:

- MSA well-formedness of A and B;
- pair relation: exactly one XG contrast, another single difference, multiple
  differences, no material difference, or uncertain;
- meaning preservation apart from the alleged agreement contrast;
- natural/plausible MSA context; and
- correction direction: A-to-B, B-to-A, neither, both, or uncertain.

Optional rationale and confidence are diagnostic only. A candidate can be valid
only when one member is well formed, the other ill formed, the relation is
exactly one XG contrast, meaning is preserved, context is natural, and correction
direction is unique.

### Agreement and adjudication

- Canonicalize independently randomized A/B order back to stable hidden side IDs
  only after labels lock. Treat well-formedness of each side as a separate
  variable and pair relation, meaning preservation, naturalness, and correction
  direction as pair-level variables.
- Compute nominal Krippendorff's alpha on every closed label from locked,
  pre-adjudication judgments. Report candidate-only and control-only results
  separately; never pool controls with candidates to improve reliability. Also
  report exact agreement, label marginals, confusion tables, uncertain rate,
  and item-level disagreements.
- Bootstrap intervals may be descriptive but must state that 30 pairs are
  unstable. Never compute reliability on adjudicated labels.
- If a label has no variation and alpha is undefined, report it as undefined;
  do not substitute percent agreement and call the label reliable.
- After reporting agreement, the third reviewer sees anonymized pairs, both
  judgments and rationales, and the frozen guide, but not intended output or
  candidate/control status. Preserve original and adjudicated records.
- Adjudication includes a reason code: rubric ambiguity, reviewer error, genuine
  linguistic ambiguity, operator defect, or other.

### Stop rules

Any one condition stops activation and keeps `XG` disabled:

- either reviewer misses any of the 10 independently keyed controls;
- candidate-only alpha is below 0.80 or undefined for pair relation or
  correction direction;
- candidate-only pre-adjudication exact agreement is below 18 of 20 items on
  either critical label;
- for either critical label, `uncertain` exceeds 4 of the 40 candidate reviewer-
  item ratings in total or 2 of 20 ratings for either reviewer;
- fewer than 18 of 20 attempted candidates are valid after adjudication;
- any adjudicated candidate violates provenance, licensing, safety, leakage, or
  offensive-content rules; or
- any reviewer or adjudicator reports a systemic rubric or tool defect.

A pre-adjudication meaning-change, multiple-error, other-error, or non-unique-
correction flag requires mandatory adjudication and remains in the audit trail.
If adjudicated as an ordinary linguistic invalidity, it counts against the
18-of-20 yield gate. If adjudicated as a systemic operator defect or a safety,
provenance, licensing, or leakage violation, it stops the pilot immediately.

Every critical label is required for all 20 candidates and all 10 controls.
Missing or withdrawn critical ratings make the batch incomplete; do not compute
the pass decision, replace items, or top up the batch. Report it incomplete and
restart only under a new protocol ID with a fresh frozen batch.

Do not delete failures and recompute thresholds. Preserve the batch, diagnose
the defect, revise under a new protocol ID, and use fresh blinded material.

Passing these gates would mean only “eligible for a larger preregistered
validation study.” It would not authorize corpus-scale generation, training,
expert-validation claims, registry activation, or Nahw-Passage evaluation.

## Ethics and reporting

Obtain informed consent, fair compensation, data minimization, reviewer contact
and withdrawal procedures, and secure handling of reviewer identities. Consent
must state the withdrawal deadline and whether de-identified annotations can be
removed after aggregate analysis. If withdrawal removes a required rating, the
batch is incomplete under the rule above. Avoid
sensitive personal text. Record dialect and standard-language bias as a
limitation. Obtain institutional or ethics guidance when required by the team's
jurisdiction and intended publication venue.

Two reviewers and 30 pairs cannot establish generality across genres, ambiguity,
or pedagogical safety. Adjudication can conceal legitimate variation, so retain
and report pre-adjudication disagreement where consent and licensing permit.

## Current go/no-go decision

**No-go for implementation or generation.** The specification is sufficiently
developed for expert review, but the feature-transition appendix and qualified
review team are absent. The registry must continue to report `XG` as disabled.

The exact next actions are:

1. recruit and verify two independent qualified MSA reviewers and a third
   adjudicator;
2. have a qualified linguist and morphology-tool reviewer produce and approve
   the feature-transition appendix using the cited sources;
3. obtain methodology, licensing, and any required ethics review;
4. merge a protocol revision that resolves both blockers; and only then
5. open a separate implementation issue for a 20-candidate private feasibility
   batch with 10 hidden controls.

If those actions cannot be completed, `XG` remains no-go. Musahhih may instead
consider separately audited released synthetic data, such as Tibyan, only under
its recorded license, attribution, split, provenance, overlap, and leakage
safeguards; that alternative cannot be presented as a newly validated controlled
operator.

## What was not done

- No Arabic text or example was created, copied, inspected, or transformed.
- No private dataset or evaluation text was accessed.
- No registry field, operator status, script, prompt, or model was changed.
- No generation, inference, fine-tuning, or human annotation occurred.
- No expert linguistic validation is claimed.
