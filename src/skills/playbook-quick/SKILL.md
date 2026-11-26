---
name: playbook-quick
description: "The quick pipeline, only when a request names it: issue, code, PR, merge, with no check. No plan, no reviewer, no verdict and no feedback rounds. The CTO/CEO turns the problem into ready-to-build issues; each developer implements one in its own worktree, runs the issue's Done when, opens one PR, watches the required checks and sends it back; the CTO/CEO, without reading the diff or running the PR's commands, merges it only when the mechanical conditions hold (merge rules allow, required checks green, not behind and no conflict, the head is the reported SHA, not a money path), confirms, and the developer removes its worktree. When they cannot hold, the CTO/CEO stops it and the PR stays open. Never picked by itself: with no playbook named, use playbook-build."
metadata:
  group: start
  summary: "Quick, only when named: CTO issues, developer PRs, CTO merges on mechanical checks only; no review"
---

# Playbook: Quick

A problem goes in; each issue ends **merged** or **stopped**, and no developer worktree is left on disk. **No architect**
plan and **no check**: no reviewer, no verdict, no feedback rounds. The CTO/CEO writes the issues and merges; developers
build. Nothing judges the code but the issue's own `Done when` and the required checks.

```text
problem ─► CTO/CEO: one or more issues ─► send each to a developer
                                              │ one issue, one worktree, one branch, one PR; Done when; checks green
                                              ▼
        CTO/CEO: mechanical conditions ◄── developer sends it back (the head SHA)
          │   (no diff read, no command of the PR run)
          ├─ all hold ─► CTO/CEO merges ─► confirms the merge ─► developer removes the worktree
          ├─ a red check, behind main ─► Returned (≤3) ─► the same developer ─► new head ─► again
          └─ cannot hold (gate refuses, money path, blocked) ─► Stopped by CTO ─► developer removes the worktree
                                                                (the PR and branch stay on GitHub)
```

This skill gives the **workflow**. How to send, track and answer is in [orchestration](references/orchestration.md),
which uses the Orca `/orchestration` skill; load that skill before the first send. A complete run is in [the example](references/example.md).

Who may message whom is [bot-orchestration](../bot-orchestration/SKILL.md): when a bot holds the developer role,
delegate to it; it runs its own agents.

## Roles

| Role | Does | Does not |
|---|---|---|
| **CTO/CEO** (owns the problem) | writes the issues, sends them, checks the **mechanical** merge conditions, **merges or stops**, confirms, tells the developer to clean up | read the diff, run the PR's commands, judge or review the code, write or edit the code |
| **Developer** (the developer role's bot and the agents it runs; your own agent only when no bot has the role) | builds one issue in its own worktree, runs its `Done when`, opens its PR, keeps the required checks green, **sends it back**, **removes the worktree** when told | merge, close the PR, delete the branch on GitHub, touch files the issue does not own, change the issue |

Every issue, comment and PR body ends with `Created: <agent name>`; every commit is authored by the developer's name.

## When to use it

**Only when the request names `playbook-quick`.** Nobody picks it by itself: a CTO/CEO told no playbook uses
`playbook-build`, which plans and reviews.

| The request names quick, but | Do |
|---|---|
| a design choice is open: a new boundary, schema or contract nobody has decided | say so and ask the owner whether to use `playbook-build`; do not switch silently |
| it is `hard` work, a race, security, `risk:money-path`, or code nobody here understands | say so and ask; do not switch silently |
| a developer finds the work bigger than the issue says | it sends back `PR BLOCKED` with the evidence; the CTO/CEO tells the owner and asks |

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
  write it, the work needs a plan: say so and ask.
- **The `Done when` is the only check**, so make it a command that proves the outcome.
- **Mark every issue quick:** the header line `Pipeline: quick` right after `Priority:`, before the first `## `
  heading, with nothing else there but the template's header lines
  ([the quick line](../write-issue/references/catalog.md#the-quick-line-pipeline-quick-only-from-playbook-quick)).
  Only this playbook writes it, and only because the owner named it; without it the unreviewed merge is refused.
- Each child says `Refs #<parent>` in `Notes`. After creating the children, list their numbers and waves in the
  parent's `## Notes`.

**Then run the gate on every issue** to be built:
`python3 <github skill>/scripts/issue_gate.py issue <n> --repo <owner>/<repo>`. As shipped, an issue opened by an account with write
access is approved ([merge rules](../github/references/pull-requests.md#merge-rules)). Only an issue it refuses **as not approved**,
such as an outsider's, waits for the owner: give them its link and one line that works in any shell, then end your turn,
and never post it yourself:

```bash
gh issue comment <number> -R <owner>/<repo> --body "Accepted by owner."
```

Send only the issues the gate allows.

## 2. CTO/CEO: send each issue to a developer

One message per issue. The developer's **bot** gets a [handoff](assets/example/developer-brief.md): the issue URL, the
limits and **the return address**. Your own agent (no bot for the role) gets an
[agent brief](assets/example/agent-brief.md), which also gives its author name. Send every issue of wave 1, then **end your turn**. A later wave is sent
only after the PRs it depends on are **merged**. Commands: [send the issues](references/orchestration.md#2-send-the-issues).

## 3. Developer: one issue, one worktree, one PR

A developer **bot** rates the issue, starts one agent on that [row](../bot-orchestration/references/routing.md) for it,
verifies the agent's work itself and answers to the CTO/CEO. The **agent** does the steps below, opening the PR included:
a bot never codes.

**Every issue has its own worktree**, never shared with another issue or with the main checkout
([create it](references/orchestration.md#2-send-the-issues)). Use the `developer` skill and the language skill:

1. Run `issue_gate.py issue <n>` (the `github` skill) **before** the worktree and any code; refused: send `PR BLOCKED`
   with the reason. In the worktree, branch from the newest `main` as `<id-lowercase>/<slug>`; change only the owned files.
2. Test first when the change has code. Clean the diff with `deslop`.
3. Commit with your name: `agent_identity.py git --author "<your name>" -- commit -m "<type>(<id>): <summary>"`.
4. Run the issue's `Done when` on the committed head **before opening the PR**. Write the PR body from the
   [PR template](../work-package/assets/pr.template.md), run both linters (the `work-package` and `github` skills), push and
   open the PR.
5. Watch the required checks (`gh pr checks <n> --required`); fix what fails (the `ci-fixer` skill). `no checks reported`
   with exit 1 means the repository has no checks: say "no checks". You own the PR until it is merged or stopped.
   **Never merge.**
6. **Keep the worktree** until the CTO/CEO says `MERGED` or `STOPPED` ([step 7](#7-developer-remove-the-worktree)): a
   red check or a rebase needs it.

## 4. Developer: send it back to the CTO/CEO

**Opening the PR is not the end of the job.** An **agent** reports only to the bot that started it
([agent report](../bot-orchestration/assets/agent-report.template.md)). That bot verifies the head; a developer **bot** then
sends the CTO/CEO the [return report](assets/example/return-report.md): `PR READY` or `PR BLOCKED`, the issue, the PR URL,
the full head SHA, the `Done when` result, the check state and what you did not do. How:
[send it back](references/orchestration.md#3-send-the-pr-back). Then end your turn.

## 5. CTO/CEO: merge, then confirm

**There is no check of the code.** Do not read the diff or run the PR's commands. Asking for this playbook gives the
CTO/CEO the merge of its PRs; **a project whose rules reserve the merge for a person, or ask for a review, wins**: stop
and ask that person. Merge only when every mechanical condition holds, with the head SHA the developer reported:

```bash
python3 <github skill>/scripts/pr_loop.py can-merge --pr <n> --repo <owner>/<repo> --unreviewed --head <reported sha>
python3 <github skill>/scripts/issue_gate.py pr <n> --repo <owner>/<repo>    # merge only on 'merge rules: allowed'
gh pr checks <n> --repo <owner>/<repo> --required                            # every required check passed
gh pr view <n> --repo <owner>/<repo> --json headRefOid,mergeable,mergeStateStatus   # not behind, no conflict
gh pr merge <n> --repo <owner>/<repo> --rebase --match-head-commit <reported sha> --delete-branch
```

`can-merge --unreviewed` refuses a PR that is not open; **any** judgment or stop on the PR, by anyone, on any head (a
`Verdict`, `Changes required`, `Accepted by`, `Stopped by`: a judged PR belongs to build or ship); a PR that links no
issue, or links one without the `Pipeline: quick` line; a `risk:money-path` label on the PR or a linked issue; and a
head other than the one given. **The script cannot know which head was reported:** you take the full SHA from the
developer's report and pass it, never the live head you just read.
`gh pr checks --required` printing `no checks reported` and exiting 1 means the repository has **no** checks, not that one
failed: merge, and report "no checks". Only quick uses `--unreviewed`.

| Found | Do |
|---|---|
| everything allows it | merge that SHA |
| a red required check, or the branch behind `main` or in conflict | **return** it to the same developer ([at most 3](#returns-at-most-3)); its new head is reported and checked again |
| 3 returns used, and a condition still does not hold | stop (step 6) and report to the owner |
| a head other than the reported one | ask the developer for a new report |
| `risk:money-path` | never auto-merged: ask a person to merge, and stop (step 6) |
| the gate refuses (the issue became done, not planned or duplicate, or lost its approval) | stop (step 6) |

### Returns: at most 3

Each time you send a PR back, first post the return on the PR, so the count lives on the host and a resumed run keeps it:

```text
Returned by CTO (<name>). PR #<n> at <head sha>. Return <k> of 3.
```

with the mechanical reason under `Blocking` (the failing check, the conflict), then `Gate` and `Residual`
([PR comment template](../write-comment/assets/pr-comment.template.md)). Check it first:
`python3 <github skill>/scripts/pr_loop.py decide --pr <n> --repo <owner>/<repo> --body-file returned.md`. It refuses a
fourth return: after 3, the next condition that does not hold is `Stopped by CTO` (step 6) with that reason, and a
report to the owner. **One return is free:** a clean rebase needed only because another quick PR of this run merged
is `Returned by CTO (<name>). PR #<n> at <head sha>. Rebase after #<m>.` ([example](assets/example/returned.md)).
`decide` allows it once per merged quick PR `#<m>`, and only when `#<m>` merged after this PR's latest report or return
(the newest of its last return, its creation and its head commit); an older merge, or a time it cannot read, and it
counts. A return judges nothing, so the
unreviewed merge still holds afterwards. `pr_loop.py state` shows `returns used: <k> of 3`.

**Always `--rebase`.** It puts the developer's own commits on `main` under the developer's name. A squash makes a new
commit authored by the account that opened the PR ([why](../github/references/identity.md#merges-keep-the-author)).

**Confirm it; the command's exit is not proof:**

```bash
gh pr view <n> --repo <owner>/<repo> --json state,mergeCommit,headRefOid,closingIssuesReferences   # MERGED, your SHA
gh issue view <issue> --repo <owner>/<repo> --json state                                           # CLOSED
git fetch origin && git log origin/main -<commits> --format='%an | %s'                           # developer's name
```

Only then: post the [merge comment](assets/example/merge.md) on the PR and send the developer
[`MERGED`](assets/example/cleanup-merged.md) ([clean up](references/orchestration.md#5-clean-up)). Not merged: keep the
worktree and fix the cause.

- **Merge in dependency order, one at a time.** After each merge, another open PR may be behind: its developer rebases
  and reports the new head.
- **Then send the next wave**, from the new `main`.
- **Close the problem:** when every child is merged, run the parent's `Done when` on `main`, post a `close` comment and
  close the parent.

## 6. Stop

When a PR cannot be merged under this playbook (the gate refuses, a money path, `PR BLOCKED`, 3 returns used and a
condition still does not hold, or the owner cancels):

1. Post `Stopped by CTO (<name>). PR #<n> at <sha>.` on the PR, with the mechanical reason under `Blocking` and what a
   person has to decide under `Residual` ([example](assets/example/stopped.md)). It judges no code.
2. Post a `status` comment (`Status: blocked`) on the issue with the PR and the link.
3. Send the developer [`STOPPED`](assets/example/cleanup-stopped.md). It **stops implementing**: if anything is not on
   GitHub yet, it commits and pushes it to the same branch, then cleans up (step 7).
4. **The PR stays open and unmerged, and the branch stays on GitHub.** Do not close the PR, delete the branch or close
   the issue. Work that depends on this issue is not sent. Other issues carry on; the parent stays open.
5. Report to the owner: the PR, why it stopped, what is left (for example `playbook-ship` to review and land it).

## 7. Developer: remove the worktree

Only after `MERGED` or `STOPPED`. First prove nothing is lost; the script removes nothing:

```bash
ORCA worktree current --json            # note this worktree's path
python3 <github skill>/scripts/pr_loop.py can-remove --worktree <path> --pr <n> --repo <owner>/<repo>
```

It allows removal when the tree is clean, every local commit is on the PR on GitHub, and the PR is merged, or stopped
with its branch still there. **Refused: do not remove**; fix the reason or report it.

```bash
ORCA worktree rm --worktree path:<path>
```

**Never `--force` and never `--delete-branch`.** Ignored files (build output, installed packages, local settings) go with the worktree, which is
the point; copy out first anything in them you need.

**A worker that runs inside the worktree reports first** ("check passed, removing now") and removes it as its very last
command, because removing it can end its session. A bot working from elsewhere removes it, then reports. Either way
**the CTO/CEO confirms it is gone** (`ORCA worktree ps`); if it is still there and its developer cannot finish, the
CTO/CEO runs the same check and removes it.

A developer cancelled before it opened a PR pushes its branch, then runs `can-remove --worktree <path>` without `--pr`.

## State: read it from the host

| For each issue (`pr_loop.py state` for a PR) | The next step |
|---|---|
| no PR | send it, if the PRs it depends on are merged; otherwise it waits |
| a PR, no report for its head | the developer is working |
| a PR, the reported head, conditions hold | merge and confirm (step 5) |
| a PR, a red check or behind `main` | post the next return (`pr_loop.py state`: returns used); the same developer fixes and reports again |
| a PR, 3 returns used, a condition still failing | stop (step 6) and report to the owner |
| merged, issue closed | the developer removes the worktree; when all are done, close the parent |
| `Stopped by` | the developer removes the worktree; the PR, branch and issue stay for the owner |
| closed without a merge or a `Stopped` | keep the branch and worktree; report it to the owner |

## One good, one bad

- **Good:** the developer runs the `Done when`, opens PR #54, waits for green checks and reports its head; the CTO runs
  `can-merge --unreviewed --head` with that SHA, the gate and the checks, and merges it without opening the diff.
- **Bad:** the CTO reads the diff and asks for a change; or merges a head pushed after the report; or merges with a red
  required check; or a forced removal of the worktree right after the last report.

## Done

- Every issue is **merged** (the reported SHA merged, the merge confirmed, the issue closed) or **stopped** (the PR open,
  the branch on GitHub, the issue blocked).
- Every developer worktree of this run is removed, and no worker is left running.
- The owner has one report: the problem, the issues, what was merged, what was stopped and why, and that nobody reviewed
  the code.

## Never

- Pick quick when the request did not name it, or switch away from it silently.
- Build or merge for an issue the gate refuses, or write the owner's acceptance for them.
- Read the diff, run the PR's commands or judge the code as the CTO/CEO; let a developer merge.
- Merge without `can-merge --unreviewed --head <reported sha>`, with a red required check, a money path, or an admin
  override; pass a head the developer did not report, or write `Pipeline: quick` on an issue the owner did not ask
  quick for.
- Send a PR back without posting its return, or a fourth time: stop it instead.
- Remove a worktree before `MERGED` or `STOPPED`, when the check refuses, or with `--force`.
- Close a stopped PR or delete its branch.
- Run two issues that own the same file at once, or start a wave before what it depends on is merged.
