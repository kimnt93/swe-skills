---
name: playbook-quick
description: "The quick build pipeline: the CTO/CEO turns a problem into one or more ready-to-build issues, each developer implements one in its own worktree, opens one PR and sends it back, the CTO/CEO checks it and gives feedback for at most 3 rounds, then merges and confirms the merge, or stops it with final feedback, leaving the PR and branch on GitHub; either way the developer then removes the worktree. No architect plan and no separate reviewer. Use when every issue can be written now without a design question. Not for open design, money paths or hard work."
metadata:
  group: start
  summary: "Quick: CTO issues, a worktree and PR each, 3 feedback rounds, CTO merges or stops, clean up"
---

# Playbook: Quick

A problem goes in; each issue ends **merged** or **stopped**, and no developer worktree is left on disk. The CTO/CEO
writes the issues, decides and merges. Developers build. There is **No architect** plan and no separate reviewer.

```text
problem ─► CTO/CEO: one or more issues ─► send each to a developer
                                              │ one issue, one worktree, one branch, one PR
                                              ▼
        CTO/CEO checks the head ◄──────── developer sends it back
          │                                   ▲
          ├─ not right, rounds left ──────────┘  Changes required (Round 1, 2, 3 of 3)
          │
          ├─ right ─► CTO/CEO merges ─► confirms the merge ─► developer removes the worktree
          │
          └─ still not right after round 3 ─► Stopped + feedback ─► developer stops, removes the worktree
                                                                     (the PR and branch stay on GitHub)
```

This skill gives the **workflow**. How to send, track and answer is in [orchestration](references/orchestration.md),
which uses the Orca `/orchestration` skill; load that skill before the first send. For a delegated agent outside Orca,
use the `delegate` skill. A complete run is in [the example](references/example.md).

## Roles

| Role | Does | Does not |
|---|---|---|
| **CTO/CEO** (owns the problem) | writes the issues, sends them, checks every PR, gives feedback, **merges or stops**, confirms, tells the developer to clean up | write or edit the code, merge a PR it authored |
| **Developer** (a standing bot or a delegated worker) | builds one issue in its own worktree, opens its PR, **sends it back**, fixes what is asked, **removes the worktree** when told | merge, close the PR, delete the branch on GitHub, touch files the issue does not own, change the issue |

Every issue, comment and PR body ends with `Created: <agent name>`; every commit is authored by the developer's name.

## Is it quick?

Quick when the CTO/CEO can write, **now**, each issue's *Owned files* and runnable *Done when* with no design question,
and each is `simple` or `medium`. The number of issues does not matter.

| Signal | Go to |
|---|---|
| a design choice is open: a new boundary, schema or contract nobody has decided | `playbook-plan` |
| `hard` work, a race, security, `risk:money-path`, or code nobody here understands | `playbook-review` |
| a developer finds the work bigger than the issue says | it sends back `PR BLOCKED` with the evidence; the CTO/CEO re-routes |

## 1. CTO/CEO: turn the problem into issues

Use the `write-issue` skill: one `package` issue per pull request, on the repository that owns the code.

| The problem needs | Create |
|---|---|
| one PR | one `package` issue |
| two or more PRs | a parent `epic` (`<AREA>-00`, its difficulty the highest child's), then one `package` per PR |

How to split:

- **One issue = one outcome = one PR = one developer.**
- **Same wave, different files.** Two issues that run at once never own the same file. If they must share one, put the
  second in a later wave and name the first under `Depends on`. The one exception is the changelog, where each PR adds
  its own line: PRs merge one at a time, and the later one rebases.
- **A shared contract is written down** (names, types, route, format) in the `Notes` of **both** issues. If you cannot
  write it, the work is not quick.
- Each child says `Refs #<parent>` in `Notes`. After creating the children, list their numbers and waves in the
  parent's `## Notes`.

## 2. CTO/CEO: send each issue to a developer

One brief per issue in the [brief format](assets/example/developer-brief.md): the issue URL, the developer's author
name, the limits and **the return address**. Send every issue of wave 1, then **end your turn**. A later wave is sent
only after the PRs it depends on are **merged**. Commands: [send the issues](references/orchestration.md#2-send-the-issues).

## 3. Developer: one issue, one worktree, one PR

**Every issue has its own worktree**, never shared with another issue or with the main checkout
([create it](references/orchestration.md#2-send-the-issues)). Use the `developer` skill and the language skill:

1. In the worktree, branch from the newest `main` as `<id-lowercase>/<slug>`; change only the owned files.
2. Test first when the change has code. Clean the diff with `deslop`.
3. Commit with your name: `agent_identity.py git --author "<your name>" -- commit -m "<type>(<id>): <summary>"`.
4. Run the issue's `Done when` on the committed head. Write the PR body from the
   [PR template](../work-package/assets/pr.template.md), run both linters (the `work-package` and `github` skills), push and
   open the PR.
5. Watch the required checks; fix what fails. You own the PR until it is merged or stopped. **Never merge.**
6. **Keep the worktree** until the CTO/CEO says `MERGED` or `STOPPED` ([step 8](#8-developer-remove-the-worktree)): the
   next round needs it.

## 4. Developer: send it back to the CTO/CEO

**Opening the PR is not the end of your job.** Send the [return report](assets/example/return-report.md): `PR READY` or
`PR BLOCKED`, the issue, the PR URL, the full head SHA, the verify result, the check state and what you did not do.
One report for each head you want checked. How: [send it back](references/orchestration.md#3-send-the-pr-back). Then end your turn.

## 5. CTO/CEO: check the head, at most 3 rounds of feedback

Check the **PR at its head SHA**, not the report. First read where the loop stands:

```bash
python3 <this skill>/scripts/quick_loop.py state --pr <n> --repo <owner>/<repo>
gh pr view <n> --repo <owner>/<repo> --json headRefOid,mergeable,mergeStateStatus,closingIssuesReferences
python3 <github skill>/scripts/pr_lint.py pr <n> --repo <owner>/<repo> --allow '<each owned file>'
gh pr checks <n> --repo <owner>/<repo>
gh pr diff <n> --repo <owner>/<repo>
```

Run the issue's `Done when` in a clean check worktree of that SHA, and **remove it right after**, every round:

```bash
git fetch origin pull/<n>/head
git worktree add --detach <check dir> <sha>
# run the commands in <check dir>
git worktree remove <check dir>
```

Confirm: the `Goal` is met; only owned files changed; the tests would fail without the change; the changelog and docs
the project requires are there. Then write **one** `decision` comment from the
[PR comment template](../write-comment/assets/pr-comment.template.md), check it, and post it **on the PR**:

```bash
python3 <this skill>/scripts/quick_loop.py decide --pr <n> --repo <owner>/<repo> --body-file decision.md
gh pr comment <n> --repo <owner>/<repo> --body-file decision.md
```

| The head | First line of the decision |
|---|---|
| right | `Accepted by CTO (<name>). PR #<n> at <40-character sha>.` → step 6 |
| not right, fewer than 3 rounds used | `Changes required by CTO (<name>). PR #<n> at <sha>. Round <k> of 3.` |
| not right, 3 rounds used | `Stopped by CTO (<name>). PR #<n> at <sha>.` → step 7 |

**A round** is one `Changes required` decision: feedback, a fix, a new check. So there are at most **3 fixes and 4
checks**: if the head after round 3 is still not right, the loop breaks. Put everything you know into each round; do not
hold a finding back for the next. A rebase request, a question, or checks the developer fixes before reporting are not
rounds. The count never resets.

After `Changes required`, send it to the **same developer** ([feedback](references/orchestration.md#4-send-feedback)).
It pushes to the same branch from the same worktree, posts a `fix` comment and sends the PR back. A wrong or unclear
issue is fixed on the issue, not worked around.

## 6. CTO/CEO: merge, then confirm the merge

Asking for this playbook gives the CTO/CEO the merge of its PRs. **A project whose rules reserve the merge for a
person wins:** stop after the acceptance and ask that person.

When the accepted SHA is still the head, checks are green and the branch is not behind `main`, **the CTO/CEO merges**
with the [merge command](../github/references/pull-requests.md#merge):

```bash
gh pr merge <n> --repo <owner>/<repo> --rebase --match-head-commit <accepted sha> --delete-branch
```

**Always `--rebase`.** It puts the developer's own commits on `main` under the developer's name. A squash makes a new
commit authored by the account that opened the PR ([why](../github/references/identity.md#merges-keep-the-author)).

**Confirm it; the command's exit is not proof:**

```bash
gh pr view <n> --repo <owner>/<repo> --json state,mergeCommit,headRefOid,closingIssuesReferences   # MERGED, your SHA
gh issue view <issue> --repo <owner>/<repo> --json state                                           # CLOSED
git fetch origin && git log origin/main -<commits> --format='%an | %s'                           # developer's name
```

Only then: post the `merge` comment on the PR and send the developer [`MERGED`](assets/example/cleanup-merged.md)
([clean up](references/orchestration.md#5-clean-up)). Not merged: keep the worktree and fix the cause.

- **Merge in dependency order, one at a time.** After each merge, another open PR may be behind: its developer rebases,
  and the new SHA is checked again.
- **Then send the next wave**, from the new `main`.
- **Close the problem:** when every child is merged, run the parent's `Done when` on `main`, post a `close` comment and
  close the parent.

## 7. The loop breaks: stop

1. Post the `Stopped by` decision on the PR. It is the **final feedback**: one `Blocking` section per thing still wrong,
   with its smallest fix, the `Gate` output, and under `Residual` what a person has to decide
   ([example](assets/example/stopped.md)).
2. Post a `status` comment (`Status: blocked`) on the issue with the PR and the decision link.
3. Send the developer [`STOPPED`](assets/example/cleanup-stopped.md) with the feedback. It **stops implementing**:
   if anything is not on GitHub yet, it commits and pushes it to the same branch, then cleans up (step 8).
4. **The PR stays open and unmerged, and the branch stays on GitHub.** Do not close the PR, delete the branch or close
   the issue. Work that depends on this issue is not sent, and a developer already on it is stopped the same way. Other
   issues carry on; the parent stays open.
5. Report to the human: the PR, why it stopped, what is left. Restarting is the human's decision (for example a new
   plan with `playbook-plan`, `playbook-review`, or a replacement issue).

## 8. Developer: remove the worktree

Only after `MERGED` or `STOPPED`. First prove nothing is lost; the script removes nothing:

```bash
ORCA worktree current --json            # note this worktree's path
python3 <this skill>/scripts/quick_loop.py can-remove --worktree <path> --pr <n> --repo <owner>/<repo>
```

It allows removal when the tree is clean, every local commit is on the PR on GitHub, and the PR is merged, or stopped
with its branch still there. **Refused: do not remove**; fix the reason or report it.

```bash
ORCA worktree rm --worktree path:<path>
```

**Never `--force` and never `--delete-branch`.** A plain git worktree outside Orca: `git worktree remove <path>`, run
from another checkout. Ignored files (build output, installed packages, local settings) go with the worktree, which is
the point; copy out first anything in them you need.

**A worker that runs inside the worktree reports first** ("check passed, removing now") and removes it as its very last
command, because removing it can end its session. A bot working from elsewhere removes it, then reports. Either way
**the CTO/CEO confirms it is gone** (`ORCA worktree ps`); if it is still there and its developer cannot finish, the
CTO/CEO runs the same check and removes it.

A developer cancelled before it opened a PR pushes its branch, then runs `can-remove --worktree <path>` without `--pr`.

## State: read it from the host

| For each issue (`quick_loop.py state` for a PR) | The next step |
|---|---|
| no PR | send it, if the PRs it depends on are merged; otherwise it waits |
| a PR, head not decided | the developer is working, or the CTO/CEO checks it (step 5) |
| `Changes required` on the head | the developer fixes and sends it back |
| `Accepted` names the head | merge and confirm (step 6) |
| merged, issue closed | the developer removes the worktree; when all are done, close the parent |
| `Stopped` | the developer removes the worktree; the PR, branch and issue stay for the human |
| closed without a merge or a `Stopped` decision | keep the branch and worktree; report it to the human |

## One good, one bad

- **Good:** after round 3 the head still fails, so the CTO posts `Stopped by` with what is left; the developer pushes,
  passes the removal check and removes the worktree; the open PR holds all the work for whoever takes it up.
- **Bad:** a fourth "small" change request; or a forced removal of the worktree right after the last report, losing a fix
  that was never pushed.

## Done

- Every issue is **merged** (an accepted SHA, the merge confirmed, the issue closed) or **stopped** (final feedback on
  the PR; PR open, branch on GitHub, issue blocked).
- No PR got more than 3 `Changes required` decisions.
- Every developer worktree and every check worktree of this run is removed, and no worker is left running.
- The human has one report: the problem, the issues, what was merged, what was stopped and why.

## Never

- Let a developer merge, or the CTO/CEO write the fix and merge it.
- Merge a SHA you did not accept, with a red or missing required check, or with an admin override.
- Ask for a fourth round, or reset the count with a new PR for the same work.
- Remove a worktree before `MERGED` or `STOPPED`, when the check refuses, or with `--force`.
- Close a stopped PR or delete its branch.
- Run two issues that own the same file at once, or start a wave before what it depends on is merged.
- Stretch quick over an open design: stop and use `playbook-plan`.
