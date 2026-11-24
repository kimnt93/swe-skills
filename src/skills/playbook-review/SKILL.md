---
name: playbook-review
description: "The CTO pipeline with a real review round: CTO issue, architect plan comment, CTO acceptance, delegated PRs, then a reviewer PASS/FAIL at the head with findings, the author fixes each finding on the same branch, the reviewer re-reviews the new SHA, and the reviewer/gate merges after PASS. Use when errors are likely, the change is risky, or the CTO wants independent review before merge."
metadata:
  group: start
  summary: "Reviewed pipeline: the plan pipeline plus a PASS/FAIL review and fix loop before the merge gate"
---

# Playbook: Review

This is `playbook-plan` **plus** an independent review and a fix round. Use it for a risky change, a money-path change,
code the human did not write, or any work where a merge after only a format check is not enough. The developer never merges;
the reviewer never approves its own fix.

```text
CTO issue ─► architect plan (comment) ─► CTO accepts ─► developer(+subagents) ─► PR
    ─► reviewer PASS/FAIL at SHA ─► author fixes findings ─► re-review ─► reviewer/gate merge
```

## 1. Make the package and the plan

Follow `playbook-plan` sections 1–3 exactly: work-package issue, architect plan comment, CTO acceptance, delegated worktree,
developer test-first, one PR per package. Do not start a review before the developer has pushed a head and the PR body has the
card's evidence.

The plan's verify command and owned files are the review contract. Add the reviewer's agent/model tier from the project's
model table; never name a model in the issue.

## 2. Reviewer: PASS/FAIL at the head

Use the `reviewer` skill and the `interrogate` skill. The reviewer is a different model family from the author and does not
edit the branch during review.

1. Record the full head SHA; the verdict covers only that SHA.
2. Read the issue, plan comment, PR body and diff; check the owned files and that the PR links the issue.
3. Run the card's exact verify command and the project's required checks; inspect the tests (not tautologies), docs and
   changelog; check the architecture and money-path rules if they apply.
4. Post **one** comment in the
   [verdict format](../work-package/references/comments.md#review-verdict): `Verdict: PASS at <full sha>` or
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

After a PASS at the current head, the reviewer/gate runs the project's merge command (`swe-cli merge ... --sha <full sha>` or
the documented equivalent) with green required checks and a branch not behind `main`. Then confirm the issue is closed, the
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
