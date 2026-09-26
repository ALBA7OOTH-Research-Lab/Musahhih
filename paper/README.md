# MRL 2026 camera-ready manuscript

This directory contains the accepted MRL 2026 manuscript, its bibliography,
the official ACL style files, and corpus-text-free figures generated from the
reviewed aggregate results.

## Build

From the repository root:

```bash
python scripts/generate_paper_figures.py
tectonic paper/main.tex --outdir paper/build
```

The generated PDF is `paper/build/main.pdf`. The build directory is ignored;
the LaTeX source and figure inputs are the version-controlled artifacts.

The manuscript uses the ACL style files pinned from `acl-org/acl-style-files`
commit `d5adc823ff0f80f98c80405ca0ab66c68e684409`:

- `acl.sty`: `19dfeddc2c0e448f3926a0bef048a9db3f3611b46265b760caabd7ada4f361de`
- `acl_natbib.bst`: `3c0626f6860018f0db63437e647e98116e8102a22d371d8861516029eb13be54`

The camera-ready source names the three authors and uses the final
ACL style option. The public manuscript contains no restricted corpus text,
record-level predictions, raw model responses, private logs, adapters, or
checkpoints. The MRL workshop permits nine content pages for an accepted long
paper, excluding references; the final PDF must be checked against this limit
and the workshop's submission instructions before upload.
