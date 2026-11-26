# Example: one problem, two issues, merged

The problem: "users misread order times, because the list shows them in the server's zone". It needs an API change and
a web change, with one contract between them. The project, files, numbers and names are made up. `ORCA` is as in
[orchestration](orchestration.md).

| # | Who | What | File |
|---|---|---|---|
| 1 | CTO/CEO | creates the parent and two issues; the contract is in both | [parent](../assets/example/parent.md), [API issue](../assets/example/issue-api.md), [web issue](../assets/example/issue-web.md) |
| 2 | CTO/CEO | runs the gate; after the repository owner's [acceptance](../../github/assets/owner-acceptance.template.md) on each issue, sends wave 1 (API); ends the turn | [brief](../assets/example/developer-brief.md) (the web one; the API one is alike) |
| 3 | Developer | builds, opens the PR | [PR body](../assets/example/pr.md) |
| 4 | Developer | sends it back | [return report](../assets/example/return-report.md) |
| 5 | CTO/CEO | checks the head, asks for a change | [changes](../assets/example/changes.md) |
| 6 | Developer | fixes on the same branch, sends it back | [fix](../assets/example/fix.md) |
| 7 | CTO/CEO | accepts the new SHA | [acceptance](../assets/example/acceptance.md) |
| 8 | CTO/CEO | merges that SHA, **confirms** the merge | [merge comment](../assets/example/merge.md) |
| 9 | CTO/CEO, Developer | says `MERGED`; the developer checks and removes its worktree; the CTO confirms it is gone | [message](../assets/example/cleanup-merged.md), [report](../assets/example/cleanup-report.md) |

The API PR (`ORD-01`) goes through steps 3 to 8 first; the web issue is sent only after it merges. The files for steps
3 to 8 show the web PR.

## If the loop had broken

Had rounds 1, 2 and 3 been used and the next head still failed, steps 7 to 9 would instead be:

| # | Who | What | File |
|---|---|---|---|
| 7 | CTO/CEO | stops the PR with the final feedback, marks the issue blocked | [stopped](../assets/example/stopped.md) |
| 8 | CTO/CEO | sends `STOPPED` | [message](../assets/example/cleanup-stopped.md) |
| 9 | Developer | pushes anything left, checks, removes the worktree; PR and branch stay | [report](../assets/example/cleanup-report.md) |

## The result

```text
#50  ORD-00: Epic — Order times in the user's zone     closed
  #51  ORD-01 (wave 1)   PR #53 merged                 closed
  #52  ORD-02 (wave 2)   PR #54 merged                 closed
         PR #54 comments: Changes required (Round 1 of 3) -> Fixed -> Accepted -> Merged
worktrees: ord-01 and ord-02 removed; every CTO check worktree removed
```

## Commands, in order (for the web PR)

```bash
# 1. CTO/CEO (the parent first, then each child with --kind package)
python3 <work-package skill>/scripts/package_lint.py issue --kind package \
    --title "ORD-02: Show order times in the local zone" \
    --label bug --label frontend --label simple --body-file issue-web.md
gh issue create --repo <owner>/<repo> --title "ORD-02: Show order times in the local zone" \
    --label bug --label frontend --label simple --body-file issue-web.md

# 2. CTO/CEO, after PR #53 is merged
ORCA orchestration worker-start --spec-file agent-brief-ord-02.md --agent <agent> \
    --worktree new-child --repo <repo> --name ord-02

# 3. Developer
python3 <github skill>/scripts/agent_identity.py git --author "<name>" -- commit -m "fix(ord-02): show local order times"
python3 <work-package skill>/scripts/package_lint.py pr --branch ord-02/local-order-times \
    --title "fix(ord-02): show local order times" --body-file pr.md
python3 <github skill>/scripts/pr_lint.py local --body pr.md --allow 'web/src/pages/Orders*' --allow CHANGELOG.md
git push -u origin HEAD
gh pr create --base main --title "fix(ord-02): show local order times" --body-file pr.md

# 4. Developer: report with worker_done, as the dispatch preamble says

# 5. CTO/CEO
python3 <github skill>/scripts/pr_lint.py pr 54 --repo <owner>/<repo> --allow 'web/src/pages/Orders*' --allow CHANGELOG.md
gh pr checks 54 --repo <owner>/<repo>
python3 <work-package skill>/scripts/package_lint.py comment --kind decision --body-file changes.md
python3 <github skill>/scripts/pr_loop.py decide --pr 54 --repo <owner>/<repo> --body-file changes.md
gh pr comment 54 --repo <owner>/<repo> --body-file changes.md
ORCA orchestration send --to dispatch:<dispatch_id> --subject "ORD-02: changes required on PR #54" --body-file changes.md

# 6. Developer: push the fix, comment fix.md on the PR, report again

# 7 and 8. CTO/CEO
gh pr comment 54 --repo <owner>/<repo> --body-file acceptance.md
python3 <github skill>/scripts/pr_loop.py can-merge --pr 54 --repo <owner>/<repo>
python3 <github skill>/scripts/issue_gate.py pr 54 --repo <owner>/<repo>
gh pr merge 54 --repo <owner>/<repo> --rebase --match-head-commit 9b8a7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b --delete-branch
gh pr view 54 --repo <owner>/<repo> --json state,mergeCommit,closingIssuesReferences
gh pr comment 54 --repo <owner>/<repo> --body-file merge.md

# 9. CTO/CEO, then the developer in its worktree, then the CTO/CEO
ORCA orchestration send --to dispatch:<dispatch_id> --subject "MERGED ORD-02: remove your worktree" --body-file cleanup-merged.md
python3 <github skill>/scripts/pr_loop.py can-remove --worktree <path> --pr 54 --repo <owner>/<repo>
ORCA worktree rm --worktree path:<path>
ORCA worktree ps
```
