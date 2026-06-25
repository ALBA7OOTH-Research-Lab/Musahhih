# Team and AI-Agent Collaboration Workflow

Status: active.

This workflow keeps human contributors and Codex-style AI agents from overwriting
each other, duplicating work, or weakening the research audit trail.

## Operating rule

Use one task, one owner, one branch, and one pull request.

Every non-trivial change should be traceable through:

```text
Notion task -> GitHub issue -> branch -> pull request -> merged commit -> Notion update
```

Notion remains the project hub for roadmap, decisions, owners, and lab-facing
status. GitHub is the execution system for code, documentation, review, and
merge history.

## Standard workflow

1. Pick a task from the Musahhih Research Hub in Notion.
2. Create or claim the matching GitHub issue before starting.
3. Assign exactly one active owner for the issue.
4. Record expected files, deliverables, dependencies, and research safeguards in
   the issue.
5. Create a branch named `codex/<issue-number>-<short-description>` or
   `human/<issue-number>-<short-description>`.
6. Keep changes limited to the issue scope.
7. Push the branch and open a pull request.
8. Request review before merge.
9. After merge, update the Notion task with the PR, merged commit, validation,
   remaining risks, and next step.

Small typo fixes may be grouped, but research logic, data processing, notebooks,
evaluation scripts, and result summaries need their own issue and PR.

## GitHub issue fields

Each implementation issue should state:

- owner;
- linked Notion task;
- status;
- branch name;
- expected files or directories;
- deliverables;
- dependencies or blocked-by tasks;
- datasets touched;
- whether private/restricted data is involved;
- research safeguards;
- validation commands;
- expected artifacts;
- reviewer expectations.

If the issue involves QALB or another restricted corpus, confirm that the
contributor has authorized access before they inspect or process the data. Do not
attach private corpus text, transformed private records, or generated private
artifacts to public GitHub issues or pull requests.

## Branch naming

Use:

```text
codex/<issue-number>-<short-description>
human/<issue-number>-<short-description>
```

Examples:

```text
codex/17-b1-b2-prompt-runner
human/18-literature-review-update
```

Do not work directly on `main` except for emergency administrative fixes. The
default path is pull request review.

## Agent startup checklist

At the beginning of each Codex session, the operator should paste this instruction
or keep an equivalent version in the issue:

```text
You are working on GitHub issue #<number> for Musahhih.
Read AGENTS.md, README.md, docs/research_plan.md, docs/dataset_audit.md, and any
issue-linked docs before editing.
Work only on branch <branch>.
Keep changes limited to this issue.
Do not use Nahw-Passage for training, prompt tuning, checkpoint selection, or repeated
model decisions.
Do not commit credentials, private datasets, model weights, checkpoints, adapters, or
large generated outputs.
Before editing, check git status and inspect active pull requests for overlapping files.
When done, report files changed, validation commands, unresolved risks, and the next step.
Update the linked Notion task if you have Notion access.
```

## Conflict rules

- Two active agents should not edit the same file unless one PR explicitly builds
  on the other.
- If two issues need the same file, decide the order in Notion or GitHub before
  either agent edits it.
- If an agent discovers unexpected local changes, it must stop and report them
  instead of overwriting.
- If a task expands beyond its issue, create a follow-up issue instead of
  silently broadening the branch.
- If a result depends on a model run, keep raw predictions and summaries in
  ignored output paths, then commit only small reviewed reports that contain no
  private corpus text.

## Pull request requirements

Every PR should include:

- linked issue and Notion task;
- summary of changes;
- research-safeguard checklist;
- validation commands actually run;
- commands or checks not run, with reasons;
- artifact paths and checksums when applicable;
- reviewer notes for data, prompt, metric, or reproducibility risks.

Do not merge PRs that:

- train on Nahw-Passage;
- leak QALB or other restricted corpus text;
- report metrics without attached raw predictions and reproducibility metadata;
- change a frozen protocol without a documented protocol revision;
- introduce paid dependencies without explicit approval.

## Recommended status flow

Use these statuses consistently in Notion and GitHub:

```text
Ready -> Claimed -> In Progress -> Review -> Done
                              \-> Blocked
```

Blocked tasks should state the exact blocker and the next person or decision
needed. Do not leave blocked work hidden in a local branch.

## Repository protection recommendations

The GitHub repository should use:

- protected `main`;
- pull requests required before merge;
- at least one approving review for research-critical changes;
- status checks for Python tests or validation scripts when available;
- no force pushes to `main`;
- branch deletion after merge;
- issue and PR templates from `.github/`.

These settings are repository administration controls, not research results. They
can be enabled incrementally as the team adds CI.
