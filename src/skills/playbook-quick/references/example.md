# Example: one problem, two issues, merged without a check

The request: "`/swe:playbook-quick` users misread order times, because the list shows them in the server's zone". It
names quick, so quick runs. It needs an API change and a web change, with one contract between them. `CTO (example)`
and `Developer (example)` are bots. The project, files, numbers and names are made up. `ORCA` is as in
[orchestration](orchestration.md).

| # | Who | What | File |
|---|---|---|---|
| 1 | CTO/CEO | creates the parent and two issues; the contract is in both | [parent](../assets/example/parent.md), [API issue](../assets/example/issue-api.md), [web issue](../assets/example/issue-web.md) |
| 2 | CTO/CEO | runs the gate on both: allowed, opened by an account with write access; sends wave 1 (API); ends the turn | [brief](../assets/example/developer-brief.md) (the web one; the API one is alike) |
| 3 | Developer | builds, runs the `Done when` on the committed head, opens the PR, watches the required checks | [PR body](../assets/example/pr.md) |
| 4 | Developer | sends it back with the full head SHA | [return report](../assets/example/return-report.md) |
| 5 | CTO/CEO | without reading the diff: `can-merge --unreviewed --head`, gate, required checks, not behind; merges that SHA, **confirms** the merge | [merge comment](../assets/example/merge.md) |
| 6 | CTO/CEO, Developer | says `MERGED`; the developer checks and removes its worktree; the CTO confirms it is gone | [message](../assets/example/cleanup-merged.md), [report](../assets/example/cleanup-report.md) |

The API PR (`ORD-01`, #53) goes through steps 3 to 6 first; the web issue is sent only after it merges. The files for
steps 3 to 6 show the web PR, #54. With no developer bot, step 2 starts the CTO's own agent with an
[agent brief](../assets/example/agent-brief.md), which reports with `worker_done`.

## If a condition had not held

| Found at step 5 | Then | File |
|---|---|---|
| PR #54 behind `main` because another quick PR of this run, #55, merged after #54's report | the CTO posts the free return `Rebase after #55.` and sends it back to the same developer, who rebases and reports the new head; step 5 runs again on it | [return](../assets/example/returned.md), [rebase](../assets/example/rebase.md) |
| a required check still red after `Return 3 of 3` | `decide` refuses a fourth return: the CTO posts `Stopped by CTO` with that reason and reports to the owner | [stopped](../assets/example/stopped.md) |
| the gate refuses: #52 closed as not planned meanwhile | the CTO posts `Stopped by CTO`, marks #52 blocked, sends `STOPPED`; the developer pushes anything left and removes the worktree; the PR and branch stay | [stopped](../assets/example/stopped.md), [message](../assets/example/cleanup-stopped.md) |

## The result

```text
#50  ORD-00: Epic — Order times in the user's zone     closed
  #51  ORD-01 (wave 1)   PR #53 merged after checks    closed
  #52  ORD-02 (wave 2)   PR #54 merged after checks    closed
worktrees: ord-01 and ord-02 removed; nobody reviewed the code
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
python3 <github skill>/scripts/issue_gate.py issue 52 --repo <owner>/<repo>    # OK: opened by an account with write access
ORCA orchestration send --to "bot:<developer>" --chat new --type handoff \
    --subject "BUILD ORD-02: show order times in the local zone" --body-file developer-brief.md

# 3. Developer
python3 <github skill>/scripts/agent_identity.py git --author "<name>" -- commit -m "fix(ord-02): show local order times"
cd web && npm run check                                                         # the issue's Done when
python3 <work-package skill>/scripts/package_lint.py pr --branch ord-02/local-order-times \
    --title "fix(ord-02): show local order times" --body-file pr.md
python3 <github skill>/scripts/pr_lint.py local --body pr.md --allow 'web/src/pages/Orders*' --allow CHANGELOG.md
git push -u origin HEAD
gh pr create --base main --title "fix(ord-02): show local order times" --body-file pr.md
gh pr checks 54 --repo <owner>/<repo> --required --watch                       # 'no checks reported': say "no checks"

# 4. Developer bot: status PR READY to the return address

# 5. CTO/CEO: no diff, no test run
python3 <github skill>/scripts/pr_loop.py can-merge --pr 54 --repo <owner>/<repo> \
    --unreviewed --head 4f2c9a1d8b7e6c5a4f3e2d1c0b9a8f7e6d5c4b3a
python3 <github skill>/scripts/issue_gate.py pr 54 --repo <owner>/<repo>
gh pr checks 54 --repo <owner>/<repo> --required
gh pr view 54 --repo <owner>/<repo> --json headRefOid,mergeable,mergeStateStatus
gh pr merge 54 --repo <owner>/<repo> --rebase --match-head-commit 4f2c9a1d8b7e6c5a4f3e2d1c0b9a8f7e6d5c4b3a --delete-branch
gh pr view 54 --repo <owner>/<repo> --json state,mergeCommit,closingIssuesReferences
gh pr comment 54 --repo <owner>/<repo> --body-file merge.md

# 6. CTO/CEO, then the developer in its worktree, then the CTO/CEO
ORCA orchestration send --to "bot:<developer>" --chat <its chat id> --type handoff \
    --subject "MERGED ORD-02: remove your worktree" --body-file cleanup-merged.md
python3 <github skill>/scripts/pr_loop.py can-remove --worktree <path> --pr 54 --repo <owner>/<repo>
ORCA worktree rm --worktree path:<path>
ORCA worktree ps
```
