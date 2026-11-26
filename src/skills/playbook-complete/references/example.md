# Example: one issue, built, reviewed and merged

Issue #52 asks the order list to show local times (the [quick example's web issue](../../playbook-quick/assets/example/issue-web.md)).
The repository owner has accepted it. `CTO (example)`, `Developer (example)` and `Reviewer (example)` are three agents.
Project, numbers and names are made up.

| # | Who | What | File |
|---|---|---|---|
| 1 | CTO/CEO | gate allows #52; sends it; ends the turn | [developer brief](../assets/example/developer-brief.md) |
| 2 | Developer | builds, opens PR #54, hands over, removes its worktree | [handover](../assets/example/return-report.md) |
| 3 | CTO/CEO | sends the PR to a reviewer without reading it | [reviewer brief](../assets/example/reviewer-brief.md) |
| 4 | Reviewer | round 1: posts the finding | [FAIL](../assets/example/verdict-fail.md) |
| 5 | Reviewer | fixes it and pushes | [fix](../assets/example/fix.md) |
| 6 | Reviewer | passes the new head, naming its commit; reports | [PASS](../assets/example/verdict-pass.md), [report](../assets/example/review-report.md) |
| 7 | CTO/CEO | `can-merge`, gate, checks; merges; confirms | [merge](../assets/example/merge.md) |
| 8 | Reviewer | checks and removes its worktree | |

```bash
R=<owner>/<repo>
# CTO, step 7: no diff, no test run
python3 <github skill>/scripts/pr_loop.py can-merge --pr 54 --repo $R
python3 <github skill>/scripts/issue_gate.py pr 54 --repo $R
gh pr checks 54 --repo $R
gh pr view 54 --repo $R --json headRefOid,mergeable,mergeStateStatus
gh pr merge 54 --repo $R --rebase --match-head-commit 9b8a7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b --delete-branch
gh pr view 54 --repo $R --json state,mergeCommit,closingIssuesReferences
gh issue view 52 --repo $R --json state
```

**If round 3 had not been enough:** after three `FAIL` rounds the next failing review is
[`Stopped by reviewer`](../assets/example/stopped.md), and nothing is merged.
