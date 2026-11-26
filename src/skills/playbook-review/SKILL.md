---
name: playbook-review
description: "The CTO build pipeline with a real review round: it takes a plan accepted through playbook-plan, creates the child cards and delegates the PRs, then a reviewer gives PASS/FAIL at the head with findings, the author fixes each finding on the same branch, the reviewer re-reviews the new SHA, and the reviewer/gate merges after PASS. Use to build an accepted plan, when errors are likely, the change is risky, or the CTO wants independent review before merge."
metadata:
  group: start
  summary: "Build an accepted plan: delegated PRs, PASS/FAIL review and fix loop, then the merge gate"
---

# Playbook: Review

The **build** pipeline for planned work: it takes a plan accepted through `playbook-plan`, builds it, and merges only
after an independent review and fix round. Use it for a risky change, a money-path change, code the human did not write,
or any work where a merge after only a format check is not enough. The developer never merges; the reviewer never
approves its own fix.

```text
accepted plan ─► child cards ─► developer(+subagents) ─► PR
    ─► reviewer PASS/FAIL at SHA ─► author fixes findings ─► re-review ─► reviewer/gate merge
```

## 1. Start from an accepted plan, then delegate

No accepted plan yet? Run `playbook-plan` first; it stops at the acceptance, and this playbook starts only when the
request includes building. A changed file list or a new package needs a new plan version and acceptance.

For each package being built:

1. Create its child issue from the plan's package list with the `write-issue` skill (kind `package`), linked to the card.
2. Create one worktree from the newest `main`; one package, one branch, one PR.
3. Delegate with the `delegate` skill or the Orca `/orchestration` skill. Take the agent and model from the project's
   agent table. One owner owns the package.
4. Give the developer the child issue and the plan comment, the owned files, the verify command and the banner: **do not
   merge, do not touch files outside the list, commit early and push**.
5. The developer follows the `developer` skill: test first, the smallest change, the PR in the project's format,
   `Closes #N`, evidence from the card's command on the committed head. It comments the PR link on the issue.
6. Waves start from the newest `main` after the previous wave merges. Do not run two packages that own the same file.

Do not start a review before the developer has pushed a head and the PR body has the card's evidence. The card's verify
command and owned files are the review contract.

## 2. Reviewer: PASS/FAIL at the head

Use the `reviewer` skill and the `interrogate` skill. The reviewer is a different model family from the author and does not
edit the branch during review.

1. Record the full head SHA; the verdict covers only that SHA.
2. Read the issue, plan comment, PR body and diff; check the owned files and that the PR links the issue.
3. Run the card's exact verify command and the project's required checks; inspect the tests (not tautologies), docs and
   changelog; check the architecture and money-path rules if they apply.
4. Post **one** comment in the
   [verdict format](../write-comment/references/other-comments.md#verdict-reviewer-on-the-pr): `Verdict: PASS at <full sha>` or
   `Verdict: FAIL at <full sha>`, with each finding's command, actual output and required output.
5. A finding is real only when a command showed it. A comment without evidence is not a finding; a PASS with an open
   finding is a failed review.

## 3. Fix the findings

The **author/developer** fixes the findings on the same branch, in its worktree, and pushes a new commit. It replies with the
new SHA and the re-run output:

```text
Fixed in <full sha>:
- <finding>: <what changed>
- `<command>` -> <tail>

New head: <full sha>. Please re-review.
```

Rules:

- One fix round fixes every finding that is still valid; unrelated code does not enter the branch.
- A finding the author disputes gets a reply with evidence; the reviewer either withdraws it or the CTO decides. Do not edit
  the issue to match the result.
- The reviewer re-reviews the new SHA. Never carry a PASS to a new head.
- If the CTO explicitly assigns the **reviewer as fixer** (a mechanical lint/format/docs finding, or an emergency), the
  reviewer may fix only the findings and push; a **different** reviewer or the CTO posts the PASS for the new SHA. The
  reviewer never approves its own fix.

## 4. Merge gate

After a PASS at the current head, the reviewer/gate runs the [merge command](../github/references/pull-requests.md#merge)
(or the project's documented equivalent) with green required checks and a branch not behind `main`. Then confirm the issue is closed, the
branch is deleted, the worktree is removed, and the merge is recorded in the run report. On FAIL, do not merge; return to
step 3 or stop with the findings.

## Done

- The PR's merged SHA has a PASS from a reviewer who did not author that SHA.
- Every finding was fixed or explicitly withdrawn with evidence; the final head has the verify output.
- The issue closed through `Closes #N`; no branch, worktree or session remains.

## Never

- Let the author approve or merge its own PR.
- Let the reviewer edit and approve the same SHA.
- Merge after a FAIL, with an open finding, or with a red/absent required check.
- Start the review before the PR has a pushed head and a runnable verify command.
