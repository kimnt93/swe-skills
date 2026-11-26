# Example: a plan, three packages, reviewed and merged

The request: "API clients flood us; limit requests per API key". It names no playbook, so the CEO uses this one.
`CEO (example)`, `Architect (example)`, `Developer (example)`, `Devops (example)`, `Tester (example)` and
`Reviewer (example)` sign the texts of each role. The project, files, numbers and names are made up. `ORCA` is as in
[orchestration](orchestration.md).

| # | Stage | Who | What | File |
|---|---|---|---|---|
| 1 | 1 | CEO | writes the planning card `RATE-00` and creates #60 | [card](../assets/example/card.md) |
| 2 | 2 | CEO | sends it to the architect; ends its turn | [architect brief](../assets/example/architect-brief.md) |
| 3 | 2 | Architect | analyses the code, posts one plan comment with three packages | [plan comment](../assets/example/plan-comment.md) |
| 4 | 2 | Architect | sends it back | [plan report](../assets/example/plan-report.md) |
| 5 | 2 | CEO | checks the plan against the card, accepts plan v1 and goes on | [acceptance](../assets/example/plan-acceptance.md) |
| 6 | 3 | CEO | creates #61 (`backend`), #62 (`ops`) and #63 (`test`, wave 2); the gate allows all three, opened by an account with write access | [#61](../assets/example/issue-a.md), [#62](../assets/example/issue-b.md), [#63](../assets/example/issue-c.md) |
| 7 | 3 | CEO | sends wave 1: #61 to the developer, #62 to devops; holds #63 | [developer brief](../assets/example/developer-brief.md), [devops brief](../assets/example/devops-brief.md) |
| 8 | 3 | Developer | its agent builds; it verifies, opens PR #64, runs the handover check, removes the worktree, reports | [handover](../assets/example/return-report.md) |
| 9 | 3 | Devops | the issue's check cannot run without a file the owner keeps; it opens no PR and keeps the worktree | [PR BLOCKED](../assets/example/report-b.md) |
| 10 | 4 | CEO | sends PR #64 to the reviewer without reading it | [reviewer brief](../assets/example/reviewer-brief.md) |
| 11 | 4 | Reviewer | round 1: the code departs from the plan | [FAIL](../assets/example/verdict-fail.md) |
| 12 | 4 | Reviewer | fixes it and pushes | [fix](../assets/example/fix.md) |
| 13 | 4 | Reviewer | passes the new head, naming its commit; reports | [PASS](../assets/example/verdict-pass.md), [report](../assets/example/review-report.md) |
| 14 | 4 | CEO | `can-merge`, gate, checks; merges; confirms #61 closed | [merge](../assets/example/merge.md) |
| 15 | 3, 4 | CEO, Tester, Reviewer | `RATE-00a` is merged, so wave 2 goes: #63 to the tester, then the same review and merge | [tester brief](../assets/example/tester-brief.md) |
| 16 | 4 | CEO | reports to the owner; #60 stays open for the blocked #62 | [report](../assets/example/report.md) |

With no developer bot, step 7 starts the CEO's own agent for #61 with an
[agent brief](../assets/example/agent-brief-developer.md); with no reviewer bot, step 10 starts one with an
[agent brief](../assets/example/agent-brief-reviewer.md).

## The host afterwards

```text
#60  RATE-00: Limit requests per API key          open; plan v1 accepted
  #61  RATE-00a (wave 1)  PR #64 merged after PASS (reviewer's commit 5a6b7c8)  closed
  #62  RATE-00b (wave 1)  no PR: blocked; the devops worktree is kept          open
  #63  RATE-00c (wave 2)  PR #66 merged after PASS                              closed
worktrees: rate-00a, rate-00c and both review worktrees removed; rate-00b kept
```

## Commands, in order

```bash
R=<owner>/<repo>
# 1. CEO
AGENT_NAME="CEO (example)" python3 <work-package skill>/scripts/package_lint.py issue --kind planning \
    --title "RATE-00: Limit requests per API key" \
    --label enhancement --label backend --label medium --body-file card.md
gh issue create --repo $R --title "RATE-00: Limit requests per API key" \
    --label enhancement --label backend --label medium --body-file card.md

# Each --chat new below is the first message from the CEO's chat to that bot: the CEO records the new chat's id
# 2 to 5. CEO and architect, as in the plan example
ORCA orchestration send --to "bot:<architect>" --chat new --type handoff \
    --subject "<parent chat name>" --body-file architect-brief.md
gh issue view 60 --repo $R --comments
gh issue comment 60 --repo $R --body-file plan-acceptance.md

# 6 and 7. CEO
python3 <github skill>/scripts/issue_gate.py issue 61 --repo $R            # OK: opened by an account with write access
python3 <bot-orchestration skill>/scripts/message_lint.py delegate --body-file devops-brief.md
ORCA orchestration send --to "bot:<developer>" --chat new --type handoff \
    --subject "<parent chat name>" --body-file developer-brief.md
ORCA orchestration send --to "bot:<devops>" --chat new --type handoff \
    --subject "<parent chat name>" --body-file devops-brief.md

# 8. Developer bot, after its agent's report
python3 <github skill>/scripts/pr_loop.py can-remove --worktree <path> --pr 64 --repo $R --handover
ORCA worktree rm --worktree path:<path>

# 10. CEO: no diff, no test run
ORCA orchestration send --to "bot:<reviewer>" --chat new --type handoff \
    --subject "<parent chat name>" --body-file reviewer-brief.md

# a later review, a rebase or MERGED goes to the reviewer's recorded child chat

# 14. CEO
python3 <github skill>/scripts/pr_loop.py can-merge --pr 64 --repo $R
python3 <github skill>/scripts/issue_gate.py pr 64 --repo $R
gh pr checks 64 --repo $R --required             # 'no checks reported' and exit 1: the repository has none
gh pr view 64 --repo $R --json headRefOid,mergeable,mergeStateStatus
gh pr merge 64 --repo $R --rebase --match-head-commit 5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b --delete-branch
gh pr view 64 --repo $R --json state,mergeCommit,closingIssuesReferences
gh issue view 61 --repo $R --json state

# 15. CEO: wave 2 from the new main
ORCA orchestration send --to "bot:<tester>" --chat new --type handoff \
    --subject "<parent chat name>" --body-file tester-brief.md
```

**If round 3 had not been enough:** after three `FAIL` rounds the next failing review is
[`Stopped by reviewer`](../assets/example/stopped.md), nothing is merged, #63 is not sent, and #60 stays open.

**An outsider's issue:** had #61 been opened by an account without write access (an outsider, or a member with read access), the gate would
refuse it as not approved, and the CEO would give the owner its link and
`gh issue comment 61 -R <owner>/<repo> --body "Accepted by owner."`, then end its turn.
