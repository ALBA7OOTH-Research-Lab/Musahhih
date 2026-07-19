# Synthetic Arabic GEC Data Protocol

Status: general methodology registered; no arm is executable from this document
alone. The proposed Tibyan-derived matched view is specified separately in
[`tibyan_f2_f3_protocol.md`](tibyan_f2_f3_protocol.md) and remains draft NO-GO
pending independent exact-commit review. No model may be fine-tuned from either
document until that gate passes.

GitHub issue: https://github.com/ALBA7OOTH-Research-Lab/Musahhih/issues/16

## Purpose and proposed contribution

Musahhih will test whether source-backed, controlled synthetic Arabic
grammatical errors transfer to unseen correction data better than natural-only
supervision when model, training budget, data size, prompt format, decoding, and
evaluation are held constant. The primary contribution is the controlled
natural-versus-synthetic-versus-mixed comparison, not the mere use of synthetic
data or the fine-tuning of Gemma.

The study may support claims about measured transfer under the frozen
conditions. It must not claim that generated examples are linguistically valid
because they look plausible, that automatic labels are expert gold labels, or
that Musahhih performed expert validation unless qualified Arabic linguists
actually complete and document that work.

## Research questions

1. Does natural-data supervised fine-tuning improve held-out MSA grammatical
   correction over the frozen untouched-model baselines?
2. At a matched training-record count, does controlled synthetic supervision
   perform differently from natural supervision?
3. At the same total record count and update budget, does a fixed mixture of
   natural and synthetic supervision outperform either source alone?
4. How do data source and mixture affect overcorrection, minimal-edit behavior,
   error-category performance, and general Arabic capability retention?

An optional secondary question may test correction-plus-explanation multitask
training. It is not part of the core claim and must use a separately frozen
protocol and targets with documented provenance.

## Experimental conditions

The core comparison uses one base-model revision, one training interface, one
maximum sequence length, one optimizer configuration, one update budget, and a
predeclared seed set. Let `N` be the largest record count that all three main
conditions can supply after filtering and split isolation.

| ID | Training records | Total records | Role |
| --- | --- | ---: | --- |
| F1-P1 | `N` eligible natural records | `N` | Natural-only reference |
| F2-P1 | `N` eligible synthetic records | `N` | Synthetic-only comparison |
| F3-P1 | `N/2` natural + `N/2` synthetic | `N` | Fixed 50:50 mixed comparison |
| F4-P1 | Predeclared size and mixture ablations | Varies | Learning-curve and mixture analysis |

If `N` is odd, discard one record through the frozen seeded selection rule
rather than silently changing the ratio. Sampling is without replacement within
each run. Selected identities and order must be written to a private, immutable
manifest before training.

F4 may evaluate total sizes of 25%, 50%, and 100% of `N`, and synthetic shares
of 25%, 50%, and 75%, only if resources allow. Freeze this grid before the first
F4 run. Mixture selection may use development results only. F4 must not become
an unrestricted search, and Nahw-Passage results must never select a mixture,
checkpoint, prompt, or seed.

If epoch-based training gives different update counts because examples have
different lengths, report both examples and tokens seen. Prefer a fixed maximum
update budget with identical gradient accumulation and effective batch size.

## Data roles and legal constraints

### Natural supervision

- Use eligible QALB training records only through the private selection
  manifest. Preserve the official split and recorded train-side exclusion.
- QALB development may support technical validation and checkpoint selection
  under a frozen rule. QALB test remains evaluation-only.
- QALB is research-restricted. Do not redistribute it, commit its text, or
  assume that its license permits publishing transformed derivatives.

### Synthetic supervision

- Tibyan is a candidate released synthetic source under CC BY 4.0, subject to
  attribution, a project-defined source-group split, private QALB overlap
  checks, and resolution or disclosure of its token-count discrepancy.
- Project-generated examples require a clean-text source whose license permits
  the intended transformation and research use. Record the source URL, version,
  license, retrieval date, and checksum before generation.
- Do not use Nahw-Passage, QALB development/test, or any evaluation text as a
  clean source, demonstration pool, retrieval corpus, or generation seed.
- Restricted natural training text must not be transformed into a persistent
  synthetic corpus unless the license and institutional guidance permit it.

No source becomes eligible merely because it is accessible online.

## Error-category provenance

Musahhih must not invent Arabic linguistic labels. Before implementation, every
category identifier must map to:

1. an exact label and definition from a cited grammar reference, released
   dataset schema, shared-task guide, or documented tool such as ARETA;
2. a machine-readable internal ID that does not pretend to be a new category;
3. permitted source contexts and transformation constraints;
4. known ambiguity and automatic-validation limits; and
5. the person or program that assigned the label.

ARETA output may be retained as an automatic diagnostic with tool version and
confidence where available. It must not be described as expert gold annotation.
Tibyan's corpus-level coverage does not establish per-record gold labels when
the release contains no per-record labels.

The first implementation task after this protocol freezes is a source-backed
category registry. It must be reviewed before its rules generate examples.

## Generation strategies

Two strategies are eligible for separate, identifiable ablations:

- deterministic transformations with explicit preconditions and inverse
  corrections; and
- model-assisted generation with a pinned open model, exact prompt, decoding
  configuration, and raw response retained privately.

Do not mix strategies under one unnamed `synthetic` source. Each record must
identify its strategy and generator version. Deterministic rules are preferred
when they can express a category without changing unrelated text.

The correction target is always derived from the stored clean source, never
from a model repairing its own output. The core experiment uses the same
correction interface for natural and synthetic records. A separate sentence-
level experiment may be added later but must not be conflated with Nahw's
highlighted-token accuracy.

## Private record and public manifest schemas

Every private synthetic record must support exact reconstruction:

```json
{
  "record_id": "stable project ID",
  "source_dataset": "registered source ID",
  "source_record_id": "source-local ID or null",
  "source_text_sha256": "SHA-256 of exact UTF-8 clean text",
  "clean_text": "private UTF-8 text",
  "erroneous_text": "private UTF-8 text",
  "target_correction": "private UTF-8 text",
  "error_span": {"start": 0, "end": 0},
  "category_id": "source-backed registry ID",
  "category_source": "citation or tool/version",
  "generation_strategy": "deterministic or model-assisted",
  "generator": {"name": "...", "revision": "..."},
  "prompt_sha256": "hash or null",
  "transformation": {"rule_id": "...", "version": "..."},
  "split": "train or development",
  "source_group_id": "group kept within one split",
  "validation": {
    "status": "accepted or rejected",
    "automatic_checks": [],
    "human_review": "none, non-expert, or qualified-expert"
  }
}
```

Offsets are measured on the exact stored Unicode string and the unit must be
declared. Preserve Arabic exactly; store normalization separately and never
overwrite source text.

Public manifests may contain IDs, hashes, source IDs, category IDs, split,
strategy, rule version, and validation flags. They must not contain restricted
text, prompts reproducing restricted text, or reversible encodings of it.

## Validation and filtering

Reject a candidate if any required check fails. At minimum:

1. clean and erroneous strings decode as UTF-8 and are not identical;
2. the declared span and inverse correction reconstruct exact clean text;
3. text outside the edit is unchanged for a single-edit condition;
4. the category rule's documented preconditions pass;
5. source license, generator revision, required fields, and hashes exist;
6. no prohibited evaluation-source provenance exists;
7. exact and near-duplicate checks pass across training/development pools;
8. source-group split isolation passes; and
9. output format contains no unintended instructions, explanations, or choices.

Automatic morphology or error tools can reject candidates or add diagnostics,
but tool agreement is not linguistic proof. Non-expert review may check schema,
alignment, obvious corruption, and formatting; it is not expert validation.

If qualified Arabic linguists participate, freeze a blinded guide, sample
design, adjudication rule, and agreement statistic before review. Obtain any
required ethics or institutional approval.

## Split isolation and contamination control

- Assign every variant of one clean source to one split through
  `source_group_id` before generation.
- Deduplicate exact text without normalization first, then run separately
  documented normalized, token, and near-duplicate checks.
- Compare training/development hashes with registered QALB test and Nahw hashes
  in the authorized private environment.
- Never rewrite official raw datasets; express exclusions through manifests.
- Freeze and checksum train/development manifests before the first model run.
- If overlap is discovered after training, invalidate and preserve the affected
  run, correct the manifest, and use a new run ID.

## Model selection and evaluation

Development data controls checkpoint selection under one predeclared metric and
tie-break rule. For highlighted-token correction, use development exact-match
accuracy, invalid-response rate as first tie-breaker, and earliest checkpoint as
second. Do not change this after viewing condition-specific results.

Report at minimum:

- exact correction accuracy and fully documented normalized exact match;
- invalid, empty, multi-token, and suspicious response rates;
- overcorrection on a frozen set of unchanged/correct inputs;
- minimal-edit or edit-distance diagnostics appropriate to the output format;
- source-backed category results where sample size permits;
- F4 learning curves;
- capability retention on a frozen external Arabic benchmark; and
- examples, tokens, updates, runtime, GPU, package versions, seeds, adapter
  size, and artifact checksums.

Use at least three predeclared seeds for trained conditions if free compute is
available. If only one run is feasible, report that limitation. Do not introduce
paid APIs or require paid Colab tiers.

Nahw-Passage is a single-use final-test gate for each frozen protocol family.
After results are viewed, they may be analyzed but must not drive a new prompt,
mixture, taxonomy, checkpoint, or training decision presented as the same
preregistered experiment.

## Optional explanation-augmented experiment

Correction-plus-explanation training is exploratory and receives a separate ID,
for example `F5-P1`. Explanation targets require documented human or dataset
provenance. Model-generated explanations must be labeled synthetic and cannot be
treated as expert rationales. Evaluate correction and explanation separately.

## Freeze checklist

- [ ] Cite and review the category registry and transformations.
- [ ] Register every source with license and checksums.
- [ ] Freeze `N`, F4's grid, seeds, update budget, checkpoint rule, and metrics.
- [ ] Approve private and public manifest schemas.
- [ ] Complete QALB/Tibyan/Nahw overlap checks privately.
- [ ] Review generation and rejection logic with no final-test text present.
- [ ] State whether qualified linguistic review exists and its true scope.
- [ ] Confirm the matrix is feasible on free compute; reduce it before running
      if needed.
- [ ] Obtain independent methodology review and record the approving commit.

For the Tibyan released-data path, the companion protocol resolves the proposed
alignment, group, project-split, nested-selection, matched-budget, and staged-
design rules. Its own freeze checklist remains controlling. The project-created
`XG` path remains disabled and is not an alternative implementation of the
Tibyan arm.

Only then may an implementation issue generate synthetic candidates. Fine-
tuning remains a later, separately reviewed task.
