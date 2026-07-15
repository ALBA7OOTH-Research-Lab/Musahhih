# Primary Sources for an Arabic GEC Error Registry

Status: source audit for review. This document is not a frozen Musahhih
category registry and does not authorize synthetic generation rules.

GitHub issue: https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/18

## Purpose

This audit identifies error labels that are explicitly documented in primary
Arabic GEC sources. It separates four concepts that must not be conflated:

1. a published linguistic or annotation category;
2. a label supported by an automatic annotation tool;
3. a gold per-record label released with a dataset; and
4. a reviewed, reversible operator suitable for synthetic generation.

A source label does not automatically satisfy the other three roles. Musahhih
must not invent missing definitions, silently translate labels into new
categories, or treat automatic annotations as expert gold.

## Primary sources

- Belkebir and Habash, “Automatic Error Type Annotation for Arabic,” CoNLL
  2021: <https://aclanthology.org/2021.conll-1.47/>
- Zaghouani et al., “Correction Annotation for Non-Native Arabic Texts: A
  Corpus for Language Learners,” 2015: <https://aclanthology.org/W15-1614/>
- Zaghouani et al., “Large Scale Arabic Error Annotation: Guidelines and
  Framework,” 2014: <https://aclanthology.org/L14-1721/>
- The first and second QALB shared-task papers:
  <https://aclanthology.org/W14-3605/> and
  <https://aclanthology.org/W15-3204/>
- Alrehili and Alhothali, “Tibyan Corpus,” arXiv:2411.04588:
  <https://arxiv.org/abs/2411.04588>
- Authoritative Tibyan release, Zenodo record 14623621:
  <https://doi.org/10.5281/zenodo.14623621>

## ARETA candidate inventory

ARETA publishes a two-level inventory of seven top-level classes and 26
supported tags. It is derived from the 29-tag Arabic Learner Corpus taxonomy.
ARETA adds merge (`MG`) and split (`SP`) and excludes five catch-all “Other”
tags: `OO`, `MO`, `XO`, `SO`, and `PO`. The table below reproduces the supported
inventory from Table 1 of the peer-reviewed paper; it does not include the five
excluded tags.

| Parent class | Tag | Published English description |
| --- | --- | --- |
| Orthography | `OA` | Confusion in Alif, Ya and Alif-Maqsura |
| Orthography | `OC` | Wrong order of word characters |
| Orthography | `OD` | Additional character(s) |
| Orthography | `OG` | Lengthening short vowels |
| Orthography | `OH` | Hamza errors |
| Orthography | `OM` | Missing character(s) |
| Orthography | `ON` | Confusion between Nun and Tanwin |
| Orthography | `OR` | Replacement in word character(s) |
| Orthography | `OS` | Shortening long vowels |
| Orthography | `OT` | Confusion in Ha, Ta and Ta-Marbuta |
| Orthography | `OW` | Confusion in Alif Fariqa |
| Morphology | `MI` | Word inflection |
| Morphology | `MT` | Verb tense |
| Syntax | `XC` | Case |
| Syntax | `XF` | Definiteness |
| Syntax | `XG` | Gender |
| Syntax | `XM` | Missing word |
| Syntax | `XN` | Number |
| Syntax | `XT` | Unnecessary word |
| Semantics | `SF` | Conjunction error |
| Semantics | `SW` | Word selection error |
| Punctuation | `PC` | Punctuation confusion |
| Punctuation | `PM` | Missing punctuation |
| Punctuation | `PT` | Unnecessary punctuation |
| Merge | `MG` | Words are merged |
| Split | `SP` | Words are split |

The official CAMeL-Lab repository is a useful implementation source, but its
README also displays the excluded catch-all tags. A registry must therefore use
the peer-reviewed paper's supported 26-tag set rather than copying the README
table wholesale. The repository expands `SF` as *Fasl wa wasl*, concerning
confusion in conjunction use or non-use.

ARETA can assign multiple tags to one aligned word, such as `XF+XG`. Compound
labels are combinations of the supported tags, not additional primitive
categories.

### ARETA provenance and limitations

- ARETA is an automatic, rule-based MSA annotation system using CAMeL Tools and
  CALIMA-Star morphological analyses. Its output is silver diagnostic
  annotation, not expert gold.
- The paper reports 85.8% micro-F1 and 55.0% macro-F1 for its best held-out ALC
  configuration. Large micro/macro divergence and weak rare-tag results make a
  single aggregate score insufficient evidence of category reliability.
- The alignment does not generally support many-to-many cases. Split errors
  require supplied alignment, and `MG`/`SP` were not evaluated on ALC because
  ALC contained neither annotation.
- Some classifications depend on heuristics. For example, an orthographic
  change affecting more than half a source word can be classified as word
  selection (`SW`).
- The authors identify overlap and ambiguity in the source taxonomy and propose
  future work on agreement, reordering, long-distance dependencies, and
  improved alignment.

Musahhih may adopt these 26 codes as a source-backed *candidate inventory*.
Every entry must initially record `synthetic_operator_approved = false`.
Operator eligibility requires a separately cited definition, explicit
preconditions and inverse, tests, and methodology review.

## QALB correction categories

The detailed QALB L2 correction guidance explicitly lists seven broad
categories:

1. Spelling Errors
2. Word Choice Errors
3. Morphology Errors
4. Syntactic Errors
5. Proper Name Errors
6. Punctuation Errors
7. Dialectal Usage Errors

The guidance documents examples or subtypes including:

- morphology: incorrect derivation, inflection, templatic morphology, and
  concatenative morphology;
- syntax: agreement in gender, number, definiteness, or case; wrong case;
  wrong tense; wrong word order; missing words; and redundant words; and
- dialectal usage: lexical, pseudo-dialectal lexical, morphological,
  phonological, and closed-class choices, with correction scope constrained by
  the guidelines.

These descriptions are correction guidance, not per-record gold labels in the
QALB release. The shared-task papers explicitly state that annotators did not
label linguistic error types.

The shared tasks also report automatically grouped correction actions:
`Edit`, `Add`, `Merge`, `Split`, `Delete`, `Move`, and `Other`. These are edit
operations, not linguistic error categories. They must not be merged into the
ARETA hierarchy or used as evidence that a grammatical phenomenon was labeled.

QALB sources are not perfectly uniform. Shared-task summaries commonly name six
broad phenomena and omit Proper Name, while the detailed LREC and L2 guidance
state seven including Proper Name. Musahhih should preserve this discrepancy
and cite the seven-category claim specifically to the detailed guidance.

The L2 guidance also gives a correction-decision priority: correct inflection,
then cliticization, then derivation while preserving the root, then preposition
errors, then lexical errors. This is an annotation priority, not an error
hierarchy or an approved synthetic-generation order.

## Tibyan category evidence

The Tibyan paper analyzes the final corpus with ARETA's seven classes and 26
tags. Its final frequency table therefore supports a claim of aggregate
ARETA-tag coverage. It does not provide a new compatible taxonomy.

The paper's source guides use broader, heterogeneous headings such as syntax,
morphology, grammar, sentence structure, semantics, phonetics, style, spelling,
punctuation, and informal or borrowed words. These headings are not defined as
a single hierarchy and must not be treated as synonyms for ARETA tags.

The paper describes two annotation phases. Reviewers corrected the assumed-
clean side for several phenomena but did not assign error types. ARETA tagging
was performed afterward, and complex cases required additional handling. Expert
review of a corrected side therefore does not establish expert gold labels for
each injected error.

The authoritative Zenodo release contains aligned correct and incorrect UTF-8
text files. It contains no stable record IDs, train/development/test split,
ARETA annotation file, per-record category field, or demonstrated mapping from
each final augmented pair to a guide category. Consequently:

- Tibyan can supply corpus pairs under the documented license and safeguards;
- it can support aggregate comparison with the paper's ARETA analysis; but
- it cannot directly supply gold category labels for Musahhih.

Any per-record Tibyan labels generated by Musahhih must record the pinned ARETA
version and be described as automatic. Source-level licensing and attribution
for bundled guide-derived material also require review before redistribution or
creation of public derivatives.

Tibyan should not be represented as controlled single-error data. Its generation
procedure can introduce multiple families into long contexts, and the paper
reports many combined tags. The final frequencies are also highly skewed even
though all 26 tags appear, so “coverage” must not be silently restated as
balanced per-category supervision.

## Evidence matrix and registry decision

| Source | Verified vocabulary | Gold per-record linguistic labels released? | Automatic implementation | Current Musahhih role |
| --- | --- | --- | --- | --- |
| ARETA paper/tool | 7 classes, 26 supported tags | No dataset gold is created merely by running ARETA | Yes | Candidate vocabulary and diagnostic tool |
| QALB guidance/release | 7 broad correction categories; documented subtypes | No; annotators did not assign error types | Correction actions are grouped automatically | Correction guidance and natural pairs, not category gold |
| Tibyan paper/release | Aggregate ARETA 7-class/26-tag analysis | No per-record labels in authoritative release | Labels can be regenerated with ARETA | Synthetic pairs and aggregate evidence, not labeled atomic operators |

The source audit supports one narrow decision:

> Use ARETA's published 26-tag, seven-class inventory as the initial
> source-backed candidate vocabulary, while retaining QALB's broader guidance
> as separate evidence. Do not treat any category as an approved synthetic
> operator or expert gold label without additional rule-specific validation.

## Requirements for the future registry

Each registry entry must include:

- exact source label, parent, and unmodified published description;
- primary citation and precise table/section location;
- whether ARETA supports it and the pinned tool version;
- whether any dataset supplies a human gold per-record label;
- known ambiguity, alignment, frequency, and evaluation limitations;
- `synthetic_operator_approved`, initially false;
- a separate operator specification and review link if approval is later sought;
- Arabic terminology only when directly sourced and cited, not translated or
  invented by the project team.

Excluded ARETA catch-all tags and unresolved source discrepancies should remain
in a provenance appendix, not the active candidate inventory. No Arabic examples
should appear in the public registry unless their source and redistribution
rights are independently established.

## Machine-readable candidate registry

The reviewed candidate metadata is stored in
[`data/registry/arabic_error_categories.json`](../data/registry/arabic_error_categories.json).
Run `python scripts/validate_error_registry.py` to verify the exact 26-tag
inventory and confirm that every synthetic operator remains disabled. The file
is public taxonomy metadata only; it contains no corpus examples or approved
transformation rules.
