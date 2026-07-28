# B1-P1 timeout-safe final-kernel preparation audit

## Scope

Issue #137 prepares one private B1-P1 511-record final-evaluation segment on
the restored P100 runtime that passed issue #135. Preparation does not access
Nahw-Passage, load a model, run inference, compute a metric, or submit a Kaggle
kernel.

## Prepared activation path

`scripts/prepare_b1_final_kaggle_kernel.py` generates a new, write-once private
kernel package only after receiving:

- the exact reviewed 40-character commit;
- a Musahhih owner-GO issue-comment permalink;
- one private kernel ID; and
- one private dataset source.

The generated wrapper fixes the B1-P1 model, immutable model revision, input
hash, prompt-bundle hash, seed 3407, greedy decoding, 32-token output limit,
canonical run ID, and explicit final-evaluation confirmation.

Its execution order is fail closed:

1. capture the wrapper start epoch;
2. clone and verify the exact approved commit;
3. restore and validate the issue #135 P100 stack in fresh processes;
4. only then discover the two private artifacts and verify their exact hashes;
5. invoke the guarded B1-P1 evaluator; and
6. accept only `complete` or metric-free `incomplete_time_budget`.

The evaluator retains the existing 34,200-second safe stop, per-row flush and
`fsync`, atomic corpus-text-free progress manifest, exact-prefix resume
validation, and prohibition on partial metrics.

## Validation

- the new generator and its generated wrapper compile;
- tests verify private-input discovery occurs after the restored-runtime gate;
- tests verify the frozen identities and absence of a temperature argument;
- tests verify private P100 metadata with exactly one data source;
- tests verify invalid commits, approval URLs, and slugs fail closed;
- tests verify a package cannot overwrite an earlier attempt; and
- the existing prompt-baseline and restored-runtime tests continue to pass.

No corpus text, model response, API credential, private prediction, or metric is
contained in this audit.

## Authorization boundary

Merging this preparation does not authorize Kaggle submission. One real
B1-P1 segment requires a fresh owner GO naming the exact merged commit, kernel
ID and version, private dataset identity and hashes, restored P100 runtime,
34,200-second safe stop, first-terminal-state preservation, and no retry.
B2-P1 remains out of scope.
