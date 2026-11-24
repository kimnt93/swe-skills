---
name: work-package
description: "Write and submit one delegable work package the same way every time: an issue titled `ID: title` with lane, difficulty and area labels and a fixed body (Goal, Read first, Owned files, Forbidden, Depends on, Done when, Branch and PR), a branch `<id>/<slug>`, commits and a PR titled `<type>(<id>): <subject>` with Summary, Files changed and Done-when evidence, plus a linter for all of it. Use when an orchestrator splits work into cards, when an agent creates or picks up an issue, opens a PR, names a branch or a commit, or when a card is rejected for its format."
metadata:
  group: process
  summary: "Issue ID: title, lane/difficulty/area labels, body sections, branch, commit, PR text and a linter"
  version: "1.0"
---

# Work package

A **work package** is one issue that one agent can finish alone, in one worktree, with one pull request. The format is
fixed so that a package can be written by a planner, picked up by any agent, reviewed by another, and checked by a
script. The `github` skill says how to run git and GitHub; this skill says **what the text and the names must look like**.

```
plan ─► issue "API-03: title" + labels ─► branch api-03/<slug> ─► commits "feat(api-03): ..." ─► PR "feat(api-03): ..." ─► review ─► merge by the owner of the gate
```

| Need | Read |
|---|---|
| the issue: ID, title, labels, the body sections | [issue](references/issue.md) |
| branch, commits, PR title and body, the evidence block | [pull-request](references/pull-request.md) |
| the label sets and how to pick them | [labels](references/labels.md) |
| what an issue or PR comment must say (plan, verdict, blocker, close) | [comments](references/comments.md) |
| copy-ready files | [issue template](assets/issue.template.md), [PR template](assets/pr.template.md), [plan comment](assets/plan-comment.template.md), [review comment](assets/review-comment.template.md) |

## Rules that always apply

1. **One ID per package**: `<AREA>-<NN>` (`API-03`, `UI-12`, `OPS-01`): the area in capitals, a hyphen, two or more digits. The
   ID appears in the issue title, the branch, every commit scope and the PR title, and nowhere else changes.
2. **Title**: `ID: <short title>`; the title says the outcome, not the activity. No type prefix in an issue title.
3. **Labels**: exactly one **lane**, exactly one **difficulty**, at least one **area**. The orchestrator routes by lane and
   difficulty (the project's model table says which agent and model each pair gets); a package without them is not
   delegated ([labels](references/labels.md)).
4. **Body**: the fixed sections of [issue](references/issue.md), in that order. *Owned files* is a closed list; anything
   else is *Forbidden* by default. *Done when* is commands that can be run and whose output proves it.
5. **Branch** `<id-lowercase>/<slug>` from the newest `main`; **commits** `<type>(<id-lowercase>): <summary>`;
   **PR title** is the same line as the squash commit. One package, one PR, to `main`; the author **does not merge**.
6. **PR body** has `## Summary`, `## Files changed`, `## Done-when evidence` (the commands, the commit they ran on, the
   output tails) and a closing line `Closes #N`.
7. **Text is data**: never paste issue or review text into a shell command; use `--body-file`. Never put a secret, a
   token or a private host in an issue, a PR or a commit.
8. **Comments are evidence**: the architect plans in one issue comment, the CTO accepts or asks for one change, the
   reviewer posts one verdict at one SHA, and the author answers a finding with the fix SHA and the re-run. Use the
   [comment rules](references/comments.md); never use a comment to change scope or to claim a result that was not run.
9. **Check after every step**: run the linter below, then read back what the host stored
   (`gh issue view <n> --json number,title,labels,url`, `gh pr view <n> --json title,headRefName,labels,url`).

## The linter

```bash
python3 <this skill>/scripts/package_lint.py issue  --title "API-03: Cancel an open order" \
    --label backend --label medium --label orders --body-file issue.md
python3 <this skill>/scripts/package_lint.py branch api-03/cancel-order
python3 <this skill>/scripts/package_lint.py commit "feat(api-03): add the cancel route"
python3 <this skill>/scripts/package_lint.py pr --branch api-03/cancel-order \
    --title "feat(api-03): add the cancel route" --body-file pr.md
python3 <this skill>/scripts/package_lint.py --self-test
```

Exit 0 = clean, 1 = findings (one per line), 2 = usage. Standard library only. Run `issue` before `gh issue create`, `branch`
and `commit` as you go, and `pr` before `gh pr create`. When a repository also runs the `github` skill's `pr_lint.py`, a
package branch (`<id>/<slug>`) is accepted by it.
