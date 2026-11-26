---
name: playbook-ship
description: "Take one existing pull request to main: one agent, the reviewer, reviews it, fixes what it finds on the PR branch, reviews again for at most 3 rounds, then merges it and confirms the linked issue closed, or stops it with final feedback, leaving the PR open. Only for a PR whose issue is approved by the merge rules and that the reviewer did not write. Use when asked to ship, finish or land a PR. For a comment-only review use playbook-review."
metadata:
  group: start
  summary: "Ship: review a PR, fix and re-review (3 rounds), merge it and close its issue, or stop"
---

# Playbook: Ship

A pull request goes in; it ends **merged with its issue closed**, or **stopped** with final feedback. A full run:
[example](references/example.md).

```text
PR ─► merge rules ─► review ⇄ fix (≤3 rounds) ─► PASS ─► merge ─► confirm merged, issue closed ─► remove worktree
        │ refused: report, change nothing      └─► still wrong ─► Stopped (PR and branch stay) ─► remove worktree
```

**You are the reviewer:** you review, fix and merge. Asking for this playbook gives you the merge of this PR. If you wrote
any of it, you cannot ship it: hand it to another agent. A project whose rules reserve the merge for a person wins.

Your own fixes are **checked by nobody else** before `main`. The PASS names them.

## 1. Check that it may be shipped

```bash
gh pr view <n> --repo <owner>/<repo> --json state,isDraft,headRefName,headRefOid,labels,body,closingIssuesReferences
python3 <github skill>/scripts/issue_gate.py pr <n> --repo <owner>/<repo>
```

| Found | Do |
|---|---|
| merged, closed or a draft | report it; change nothing |
| the gate refuses (no linked issue, not approved, done, not planned, duplicate) | change nothing; report the reason and, if approval is all that is missing, the owner's [acceptance comment](../github/references/issues.md#before-any-work) |
| a fork or an outside contributor | do not run or fix it; suggest `playbook-review` and ask the human |
| you wrote some of it, or its author is still working on it | stop: another agent ships it, after the handover |
| `risk:money-path` | review and fix, but **do not merge**: after the PASS, ask the human |

## 2. Review and fix until PASS

Follow the [review and fix loop](../reviewer/references/fix-loop.md): your own worktree on the PR branch, a
`FAIL ... Round k of 3.` before each fix, **at most 3 rounds**, then PASS or `Stopped by reviewer`. A first review with no
finding goes straight to the PASS.

## 3. Merge and confirm

Right before the merge, all of these hold on the current head:

```bash
python3 <github skill>/scripts/pr_loop.py can-merge --pr <n> --repo <owner>/<repo>   # the review allows the merge
python3 <github skill>/scripts/issue_gate.py pr <n> --repo <owner>/<repo>            # merge rules: allowed
gh pr checks <n> --repo <owner>/<repo>                                               # required checks green
gh pr view <n> --repo <owner>/<repo> --json headRefOid,mergeable,mergeStateStatus    # not behind, no conflict
gh pr merge <n> --repo <owner>/<repo> --rebase --match-head-commit <passed sha> --delete-branch
```

Behind `main`: [rebase](../reviewer/references/fix-loop.md#behind-main) and review the new head. Never `--admin`.

**Confirm it; the command's exit is not proof:**

```bash
gh pr view <n> --repo <owner>/<repo> --json state,mergeCommit,closingIssuesReferences   # MERGED
gh issue view <issue> --repo <owner>/<repo> --json state                               # CLOSED
```

Then post the `merge` comment on the PR (`Merged by reviewer (<name>) at <sha> after PASS.`). The issue closes through the
PR's `Closes #N`. If it stayed open and the PR said `Closes`, close it with a `close` comment that links the merge. An
issue linked with `Refs` is partial work: **leave it open**.

## 4. Clean up

[Remove your worktree](../reviewer/references/fix-loop.md#remove-your-worktree), after the confirmed merge or the stop.

## One good, one bad

- **Good:** round 1 finds a missed case; you post the FAIL, add a failing test, fix it, review the whole head again, PASS
  naming your commit, merge that SHA and see the issue closed.
- **Bad:** deleting the failing test to get a PASS, or fixing quietly and posting only a PASS.

## Done

- Merged: the PASS and the merge name the same head, the PR is `MERGED`, each `Closes` issue is `CLOSED`, your worktree is
  gone. Or stopped: final feedback on the PR, issue blocked, PR open, branch on GitHub, your worktree gone.
- The report says: the PR, rounds used, **the commits you pushed that nobody else checked**, and what is left.

## Never

- Ship a PR you wrote, one the merge rules refuse, or auto-merge a money path.
- Fix before posting the finding, ask for a fourth round, or weaken a check to pass.
- Merge a head you did not pass, with a red or missing required check, or with an admin override.
