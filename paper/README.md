# MRL 2026 manuscript

This directory contains the anonymized review manuscript for issue #149.

## Format

The paper uses the official ACL style files pinned from
`acl-org/acl-style-files` commit
`d5adc823ff0f80f98c80405ca0ab66c68e684409`.

- `acl.sty` SHA-256:
  `19dfeddc2c0e448f3926a0bef048a9db3f3611b46265b760caabd7ada4f361de`
- `acl_natbib.bst` SHA-256:
  `3c0626f6860018f0db63437e647e98116e8102a22d371d8861516029eb13be54`

Two trailing spaces in the upstream bibliography style were removed for
repository diff hygiene; this does not change its BibTeX behavior.

Do not place author names, affiliations, acknowledgements, identifying
repository links, private corpus text, record-level predictions, model
responses, logs, or adapters in the review package.

## Build

From the repository root:

```powershell
python scripts/generate_paper_figures.py
tectonic paper/main.tex --outdir paper/build
```

Run the figure generator before compiling. The generated figure contains only
reviewed aggregate values from `results/research_results_consolidated.json`.

The current target is the MRL 2026 long-paper limit: eight content pages plus
unlimited references. The final PDF must be visually rendered and checked
before submission.
