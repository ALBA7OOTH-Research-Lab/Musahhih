# B2-P1 timeout-safe final-kernel preparation audit

## Scope

Issue #141 prepares one private B2-P1 511-record final-evaluation segment on
the restored P100 runtime that passed issue #135 and completed B1-P1 in issue
#139. Preparation does not access Nahw-Passage, load a model, run inference,
compute a metric, or submit a Kaggle kernel.

## Prepared activation path

`scripts/prepare_b2_final_kaggle_kernel.py` generates a new, write-once private
kernel package only after receiving an exact reviewed commit, a Musahhih
owner-GO issue-comment permalink, one private kernel ID, and one reviewed
private dataset source.

The generated wrapper freezes:

- protocol B2-P1 and its existing expert-style prompt renderer;
- the 511-record input SHA-256;
- the untouched Gemma model and immutable revision;
- seed 3407;
- greedy decoding with no temperature argument;
- maximum 32 new tokens; and
- the canonical B2-P1 run identity.

It deliberately passes no demonstration bundle. Although the reused private
dataset also contains the separately frozen B1 bundle, the B2 wrapper addresses
and hashes only `nahw_gec_test.jsonl`.

The execution order remains fail closed:

1. capture the wrapper start epoch;
2. clone and verify the exact approved commit;
3. restore and validate the passing P100 stack in fresh processes;
4. only then access and hash the exact private test input;
5. invoke the guarded B2-P1 evaluator; and
6. accept only `complete` or metric-free `incomplete_time_budget`.

The evaluator retains the 34,200-second safe stop, per-row flush and `fsync`,
atomic corpus-text-free progress, exact-prefix continuation checks, and
prohibition on partial metrics.

## Validation

- the new generator and its generated wrapper compile;
- tests prove the restored-runtime gate precedes private-input access;
- tests verify B2-P1 has no bundle or temperature argument;
- tests verify the frozen input/model/seed/decoding identity;
- tests verify private P100 metadata with exactly one data source;
- invalid commits, approval URLs, sources, and kernel IDs fail closed;
- a package cannot overwrite an earlier attempt; and
- existing prompt-runner and restored-P100 tests continue to pass.

No corpus text, response, API credential, prediction, or metric is contained
in this audit.

## Authorization boundary

Merging this preparation does not authorize Kaggle submission. One B2-P1
segment requires a fresh owner GO naming the exact merged commit, kernel ID and
version, private dataset and input hash, passing P100 runtime, 34,200-second
safe stop, first-terminal-state preservation, and no retry.

B1-P1 is complete and must not be repeated.
