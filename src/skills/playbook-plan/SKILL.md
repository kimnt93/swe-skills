---
name: playbook-plan
description: "The CTO pipeline for new features, cross-file changes and hard bugs: CTO creates or accepts one work package, the architect posts a plan comment with the packages and waves, the CTO accepts it, developers and subagents build one PR per package, and the reviewer/gate verifies the head and merges it. No separate review-and-fix round: a failed check goes to playbook-review."
metadata:
  group: start
  summary: "Plan pipeline: CTO issue, architect plan comment, CTO approval, delegated PRs, reviewer merge gate"
---

# Playbook: Plan

Use this when the work is new behaviour, a cross-file change, a hard bug, or anything whose shape is not yet settled.
The CTO owns the issue and the decision; the architect plans; developers build; the reviewer/gate merges. The CTO does not
code, the developer does not merge.

```text
CTO issue ─► architect plan (comment) ─► CTO accepts ─► developer(+subagents) ─► PR ─► reviewer/gate merge
```

## 1. CTO: make one work package

Use the `work-package` skill. The issue is the contract:

- title `ID: outcome`, one lane + one difficulty + at least one area label;
- body `Goal`, `Read first`, `Owned files`, `Forbidden`, `Depends on`, `Done when`, `Branch and PR`;
- a runnable `Done when` command and a closed file list, or the issue is not ready.

If an issue exists, check it against the same format. Fix it with a comment or a new package (`Replaces #N`) before any
architect work. Do not start a plan on an issue without an acceptance command.

## 2. Architect: comment the plan

Use the `architect` and `planner` skills. Read the issue, the project map, `ARCHITECTURE.md`, the specs named by the issue,
and the surrounding code. Do not edit tracked code and do not open a PR.

Post **one** plan comment in the format of
[work-package comments](../work-package/references/comments.md#architect-plan):

- the decision and the rejected alternative;
- packages and waves, with IDs, lane, difficulty, owned files and dependencies;
- every shared contract (names, types, routes, schema, event);
- the agent/model tier per wave (from the project's model table, never a model slug in the package);
- the exact verify command and expected output per package;
- risks and open questions.

The plan is complete when a developer could start every package without asking a design question. If a package needs a new
decision, stop and put it in the plan; do not hide it in a brief.

## 3. CTO: accept, then delegate

The CTO reads the plan comment and writes **one** acceptance comment:

```text
Accepted plan at <date>. Start wave 1: <IDs>. Owner: <bot>.
```

or one `Changes required` comment with the exact changes. No delegation starts before acceptance. A changed file list or a
new package needs a new acceptance.

For each accepted package:

1. Create one worktree from the newest `main`; one package, one branch, one PR.
2. Delegate with the `delegate` skill or the project's Orca/T3/CLI runner. Use the model tier the plan named; the CTO may
   start bounded subagents for research or a second design opinion, but one owner still owns the package.
3. Give the developer the full issue and plan comment, the owned files, the verify command and the banner: **do not merge,
   do not touch files outside the list, commit early and push**.
4. The developer follows the `developer` skill: test first, the smallest change, the PR in the project's format, `Closes #N`,
   evidence from the card's command on the committed head. The developer comments the PR link on the issue.
5. Waves start from the newest `main` after the previous wave merges. Do not run two packages that own the same file.

## 4. Reviewer/gate: verify and merge

The reviewer is a different model family from the author. It does not edit the branch. At the PR head:

1. Read the issue, plan comment, PR body and diff; check the file list against `Owned files` and the diff.
2. Run the card's exact verify command and inspect the required checks; read the docs and changelog entry the project requires.
3. Post **one** verdict with `Verdict: PASS at <full sha>` or `Verdict: FAIL at <sha>` in the
   [comment format](../work-package/references/comments.md#review-verdict). A PASS with an open finding is a failed review.
4. On PASS, run the project's merge gate (`swe-cli merge ... --sha <full sha>` or the repo's documented gate). The reviewer
   does not edit code; running the gate is the merge action, not an edit. Never merge a SHA you did not review, a branch
   behind `main`, or a PR with a red required check.
5. On FAIL, stop this playbook. Fix the findings with `playbook-review`; do not merge.

After the merge: confirm the issue closed, delete the branch, remove the worktree when its package is done, and record the
PR and verify output in the run report.

## Done

- Every package has an issue, a plan comment, a CTO acceptance, a PR and a reviewer verdict at its merged SHA.
- `main` contains the work; each package's verify command passed on the head that merged.
- No worktree, branch or agent session is left for a merged package.

## Never

- Start a developer before the CTO accepts the plan.
- Let a developer merge, or a reviewer edit the branch and then approve its own change.
- Plan a package without owned files or a runnable verify command.
- Merge with a red check, an open finding or a stale head; the gate is not a formality.
