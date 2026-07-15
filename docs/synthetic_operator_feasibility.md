# First Grammatical Synthetic-Operator Feasibility Review

Status: methodology recommendation for review. No operator is approved or
enabled, and this document contains no transformation rule or generated example.

GitHub issue: https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/22

## Decision boundary

This review asks which one source-backed grammatical category deserves a later
operator-*specification* study. It does not ask which category should be
implemented or used for data generation. The correct outcome may be no-go.

The decision was made without inspecting Nahw-Passage, private QALB text, Tibyan
examples, or model outputs. Final-test behavior did not influence the rubric or
recommendation.

## Candidate set

The fixed candidate set contains the ARETA morphology and syntax tags recorded
in [`arabic_error_taxonomy_sources.md`](arabic_error_taxonomy_sources.md):

- `MI`: Word inflection
- `MT`: Verb tense
- `XC`: Case
- `XF`: Definiteness
- `XG`: Gender
- `XM`: Missing word
- `XN`: Number
- `XT`: Unnecessary word

Orthography, punctuation, merge, split, and broad semantics tags are outside the
first *grammatical* operator decision. This scope does not imply that the eight
candidates are complete, atomic, or equally well defined.

## Primary evidence

- ARETA taxonomy, implementation, and per-tag evaluation: Belkebir and Habash,
  “Automatic Error Type Annotation for Arabic,” CoNLL 2021,
  <https://aclanthology.org/2021.conll-1.47/>.
- QALB L2 correction guidance: Zaghouani et al., 2015,
  <https://aclanthology.org/W15-1614/>.
- CAMeL Tools morphology feature documentation:
  <https://camel-tools.readthedocs.io/en/stable/reference/camel_morphology_features.html>.
- CAMeL Tools analyzer documentation, which describes returned analyses as
  possible out-of-context analyses:
  <https://camel-tools.readthedocs.io/en/v1.3.1/cli/camel_morphology.html>.
- CAMeL Tools reinflector documentation:
  <https://camel-tools.readthedocs.io/en/latest/api/morphology/reinflector.html>.
- CAMELMORPH MSA analyzer/generator: Khairallah et al., LREC-COLING 2024,
  <https://aclanthology.org/2024.lrec-main.240/>.

Tool availability establishes technical support for analysis or candidate-form
enumeration. It does not prove sentence-level grammaticality, unique error type,
meaning preservation, or expert validity.

## Fail-closed rubric

The rubric uses veto gates rather than a weighted total. Correlated strengths
must not compensate for a fundamental validity failure. A candidate advances
only if it has no `Fail` outcome.

| Gate | Pass | Conditional | Fail |
| --- | --- | --- | --- |
| Source specificity | Published category plus enough operational evidence to delimit a study | Category is published but needs a narrowly reviewed scope | Label is too broad to delimit without inventing an uncited category |
| Surface observability | Intended contrast normally produces a distinct undiacritized surface form | Surface contrast exists only for a documented subset | Contrast is commonly invisible or indistinguishable in target text |
| Mechanical reversibility | Open tools and stored metadata can recover the exact clean form | Exact reversal is possible only after restrictive eligibility checks | No bounded, deterministic inverse can be specified |
| Linguistic atomicity | One edit can plausibly target the category without changing meaning or requiring other edits | Atomicity may hold for a narrow relation and must be validated | Edit inherently has broad lexical/semantic effects or commonly triggers other required edits |
| Automatic rejection strength | Open checks can reject most invalid candidates and verify the intended relation | Tools can verify morphology/edit shape but not contextual grammaticality | Tools verify only surface edit shape or offer no meaningful validity check |
| Review burden | A bounded blinded audit can reasonably verify a pilot | Qualified review is required but scope can be narrowly bounded | Validation requires open-ended discourse, lexical, or syntactic adjudication |

ARETA per-tag F1 and support are secondary evidence about automatic annotation,
not operator validity. Mechanical reversibility is distinct from linguistic
uniqueness: storing a deleted token makes an edit reversible but does not prove
that its deletion created one grammatical error.

## Source facts relevant to the rubric

ARETA defines the eight candidates with short English descriptions rather than
operator preconditions. It compares morphological analyses sharing lemma and
part of speech, can produce compound labels, and documents overlapping and
ambiguous source categories. Its authors identify agreement, long-distance
dependencies, and improved parsing/alignment as future work.

On the blind ALC test portion, the paper reports the following tag F1 and
support for its all-analysis configuration:

| Tag | F1 | Support |
| --- | ---: | ---: |
| `MI` | 16.0 | 1.3% |
| `MT` | 90.9 | 0.6% |
| `XC` | 82.1 | 3.1% |
| `XF` | 93.5 | 4.9% |
| `XG` | 70.6 | 2.0% |
| `XM` | 82.4 | 4.6% |
| `XN` | 25.0 | 0.5% |
| `XT` | 91.2 | 6.0% |

High F1 for `XF` or `XT` means ARETA often recognized those labels on aligned
correction data. It does not show that Musahhih can safely create new errors in
those categories. Low support also makes `MT`'s high F1 weak evidence for a
first operator.

CAMeL morphology exposes features including case, state/definiteness, gender,
form gender, number, form number, aspect, mood, person, voice, and clitics. The
analyzer can return multiple analyses for an undiacritized word; the generator
and reinflector can enumerate licensed forms. A licensed form is necessary but
not sufficient evidence of contextual correctness or incorrectness.

## Consistent candidate assessment

The outcomes below are Musahhih methodology judgments derived from the cited
facts, not claims made by ARETA, QALB, or CAMeL Tools.

| Tag | Specificity | Surface | Reverse | Atomicity | Auto rejection | Review | Outcome |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `MI` | Fail | Conditional | Conditional | Fail | Fail | Fail | Defer: word inflection is too broad and overlaps separately named features |
| `MT` | Conditional | Pass | Conditional | Fail | Conditional | Fail | Defer: tense/aspect choice is contextual and can change proposition meaning |
| `XC` | Conditional | Fail | Conditional | Conditional | Fail | Fail | Reject first: case is often unobservable in ordinary undiacritized MSA and requires syntax |
| `XF` | Conditional | Pass | Conditional | Fail | Conditional | Fail | Defer: state, article presence, construct phrases, and referential meaning are not equivalent |
| `XG` | Conditional | Conditional | Conditional | Conditional | Conditional | Conditional | Advance only to a narrow specification study |
| `XM` | Fail | Pass | Pass | Fail | Fail | Fail | Reject first: deletion shape is easy, obligatory-word status is not |
| `XN` | Conditional | Conditional | Conditional | Fail | Fail | Fail | Reject first: number can change meaning and trigger multi-token agreement; ARETA evidence is weak |
| `XT` | Fail | Pass | Pass | Fail | Fail | Fail | Reject first: insertion space and contextual acceptability are open-ended |

### Why `XG` advances over `XF`

`XF` has stronger ARETA annotation results, but its surface cues combine
definiteness, morphological state, article/clitic realization, and construct
phrase behavior. A mechanically simple article edit can alter meaning or create
a different valid structure, so the linguistic-atomicity and review gates fail.

`XG` also remains context-sensitive and ambiguous. However, open morphology
resources expose lexical and form-gender features, visible gender contrasts are
available for a restricted subset, and a later study can investigate whether a
single explicit agreement relation can be isolated while preserving lemma,
part of speech, number, definiteness/state, and all text outside one target.
Those are questions for the next specification—not rules approved here.

`XG`'s lower ARETA F1 is a reason to prohibit ARETA-only acceptance, not a reason
to prefer a category whose generated edits are harder to interpret causally.

## Recommendation

Advance `XG` (Gender) to one later, documentation-only operator-specification
study. This is the least-bad research candidate, not an enabled operator.

The future study must remain no-go unless it can:

1. cite a recognized Arabic grammar or annotation source for the exact
   agreement relation and eligibility boundary;
2. identify target relations without using Nahw-Passage or evaluation text;
3. preserve exact clean text and demonstrate a one-edit inverse;
4. distinguish lexical gender from surface/form gender;
5. preserve lemma, part of speech, number, state/definiteness, and unrelated
   morphology under pinned tools;
6. reject syncretic or ambiguous surface forms and compound error cases;
7. use automatic tools only as filters, never as proof of grammaticality;
8. define a blinded qualified-linguist pilot and adjudication plan before any
   generated record is accepted; and
9. keep registry status disabled until a separate reviewed approval changes it.

If qualified linguistic review or a sufficiently precise primary source is not
available, the correct next decision is no-go. Do not fall back to a plausible-
sounding model-generated rule.

## What was not done

- No Arabic sentence or token was created, inspected, copied, or transformed.
- No private dataset or final-test content was used.
- No transformation rule, prompt, generator, or validation implementation was
  written.
- No model was loaded, queried, trained, or selected.
- No operator status was changed.
