# Example: ship one pull request

PR #54 fixes order times and closes issue #52. #52 was opened by an account with write access, so the merge rules approve it. The author finished and handed the
branch over. You are `Reviewer (example)`. Project, numbers and names are made up. `ORCA` is as in
[orchestration](../../playbook-plan/references/orchestration.md).

| # | What happens | Comment to copy |
|---|---|---|
| 1 | the gate allows PR #54; you did not write it | |
| 2 | round 1: you post the finding | [FAIL, round 1](../assets/example/verdict-fail.md) |
| 3 | you fix it in your worktree and push | [fix](../assets/example/fix.md) |
| 4 | you review the new head and pass it, naming your commit | [PASS](../assets/example/verdict-pass.md) |
| 5 | you merge that SHA, confirm, say so | [merge](../assets/example/merge.md) |
| 6 | you remove your worktree | |

```bash
R=<owner>/<repo>
python3 <github skill>/scripts/issue_gate.py pr 54 --repo $R
git fetch origin ord-02/local-order-times
ORCA worktree create --repo <repo> --name review-pr-54 --branch review/pr-54 --base-branch origin/ord-02/local-order-times

# round 1
python3 <github skill>/scripts/pr_loop.py decide --pr 54 --repo $R --body-file verdict-fail.md
gh pr comment 54 --repo $R --body-file verdict-fail.md
python3 <github skill>/scripts/agent_identity.py git --author "Reviewer (example)" -- commit -m "fix(ord-02): format dates in the local zone"
git push origin HEAD:ord-02/local-order-times
gh pr comment 54 --repo $R --body-file fix.md

# the new head
python3 <github skill>/scripts/pr_loop.py decide --pr 54 --repo $R --body-file verdict-pass.md
gh pr comment 54 --repo $R --body-file verdict-pass.md

# merge
python3 <github skill>/scripts/pr_loop.py can-merge --pr 54 --repo $R
python3 <github skill>/scripts/issue_gate.py pr 54 --repo $R
gh pr checks 54 --repo $R --required                  # 'no checks reported' and exit 1: the repository has none
gh pr merge 54 --repo $R --rebase --match-head-commit 9b8a7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b --delete-branch
gh pr view 54 --repo $R --json state,mergeCommit,closingIssuesReferences
gh issue view 52 --repo $R --json state
gh pr comment 54 --repo $R --body-file merge.md

# clean up
python3 <github skill>/scripts/pr_loop.py can-remove --worktree <path> --pr 54 --repo $R
ORCA worktree rm --worktree path:<path>
```

**If round 3 had not been enough:** after three `FAIL` rounds the next failing review is
[`Stopped by reviewer`](../assets/example/stopped.md): no merge; the PR, branch and issue stay.
