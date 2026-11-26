---
name: playbook-build
description: "The default pipeline of a CTO/CEO: issue, plan, code, PR, review and fix, merge. (1) The CTO/CEO creates the issue card; (2) the architect plans it carefully and the CTO/CEO checks the plan against the card and accepts it; (3) each package of the plan becomes an issue the merge rules approve, and the role that holds its lane (developer, tester or devops) builds it in its own worktree, opens the PR and hands it over; (4) the reviewer reviews the code against the issue and the accepted plan, fixes what it finds within 3 rounds and passes or stops it, and the CTO/CEO trusts the verified PASS, merges, confirms and closes the card. Use for any request to build that names no other playbook. For one existing PR use playbook-ship; for only a plan, playbook-plan."
metadata:
  group: start
  summary: "Build (the default): issue, architect plan, package PRs, reviewer fixes and passes, CTO merges"
---

# Playbook: Build

The default. A request goes in; each package of its plan ends **merged** or **stopped**, and the card is closed when
every package is merged. Four stages: **issue → plan → code → ship**. The plan carries the weight: the owner approves and
reviews no code by default.

```text
1 ISSUE  CTO/CEO: the card (planning card or epic)
           │
2 PLAN   architect: plan comment ─► sends it back ─► CTO/CEO checks it against the card, accepts  (changes: plan v2)
           │                                          an accepted plan already? start at 3
3 CODE   CTO/CEO: one package issue per PR ─► the merge rules approve it
           │
         builder by lane (developer / tester / devops): own worktree, one PR, hands over, removes its worktree
           │
4 SHIP   reviewer: review against the issue and the plan ⇄ fix, at most 3 rounds
           ├─ PASS ────► CTO/CEO trusts it ─► merges ─► confirms ─► every child merged: closes the card
           └─ Stopped ─► CTO/CEO reports it (PR and branch stay)
```

The reviewer's own fixes are **checked by nobody else** before `main`: that is the trade this playbook makes. The PASS
names them, and a `risk:money-path` PR is never auto-merged.

**Asking** follows [the asking rule](../principles/references/never-block-on-the-human.md); the stops this playbook
names stay.

Commands: [orchestration](references/orchestration.md) (Orca `/orchestration`). A
full run, with a blocked package and a second wave: [example](references/example.md).

Who may message whom is [bot-orchestration](../bot-orchestration/SKILL.md). Each role is held by a bot or by an agent;
which bot holds which role is the team's own mapping. The CTO/CEO **only orchestrates**: it never plans, codes, tests,
deploys or reviews, and it starts no agent for a role another bot holds. Only when no bot has a role does it start its
own agent for it.

## Where does this run stand

Read it from the host, so a resumed run starts at the right stage. Look at the card, then each package issue, then each PR:

```bash
gh issue view <card> --repo <owner>/<repo> --comments                       # the plan and the decisions; children in Notes
python3 <github skill>/scripts/issue_gate.py issue <n> --repo <owner>/<repo>  # each package: approved?
gh issue view <n> --repo <owner>/<repo> --json state,closedByPullRequestsReferences
python3 <github skill>/scripts/pr_loop.py state --pr <pr> --repo <owner>/<repo>
```

| On the host | Stage | Next |
|---|---|---|
| no card for the request | 1 | create it |
| a card, no plan comment | 2 | send it to the architect, or the architect is still working |
| a plan comment, no decision, or `Changes required by` as the latest | 2 | check and decide, or the architect revises |
| `Accepted by` the latest plan version, no package issues | 3 | create the package issues |
| a package issue the gate refuses as not approved (an outsider's) | 3 | ask the owner, with the one-line command; send the others, end your turn |
| an approved package, no PR, what it depends on not merged | 3 | it waits for that merge (stage 4) |
| a package or step the acceptance says waits for the owner, no answer yet | 3 | it waits; the others go on |
| an approved package, no PR, nothing unmerged before it | 3 | send it to its builder, or the builder is working |
| a PR, handed over, no verdict on its head | 4 | send it to the reviewer, or the reviewer is working |
| `Verdict: PASS` on the head | 4 | merge and confirm |
| merged, issue closed | 4 | send the next wave; when every child is merged, close the card |
| `Stopped by reviewer` | 4 | nothing: the PR, branch and issue stay for the owner |

## Roles

| Role | Does | Does not |
|---|---|---|
| **CTO/CEO** | writes the card and the package issues, sends each job to the role that holds it, checks the plan against the card and decides, **trusts the verdict**, merges, confirms, closes the card | plan, code, test, deploy, review the diff, edit code |
| **Architect** | analyses the code, plans carefully, posts the plan comment, sends it back | accept its own plan, build |
| **Builder**: the developer; the tester for a `test` lane issue; devops for an `ops` lane issue | builds one issue in its own worktree as the plan says, opens the PR, hands it over, removes its worktree | merge, fix after the handover |
| **Reviewer** (from a different model family than the builder when the project has one) | reviews the PR against its issue **and the accepted plan**, **fixes its findings**, passes or stops it | judge code it wrote first, merge, change the issue or the plan |

Each role signs with its own [name](../bot-orchestration/SKILL.md#names). No bot for the tester or devops role: the
developer builds that issue. No developer bot either: your own agent, named `<your name> / <role>`.

## When to use it

| The request | Pipeline |
|---|---|
| names a playbook | that playbook |
| work to build, no playbook named | **build** |
| names `playbook-quick` | `playbook-quick`; nobody picks it by itself |
| an existing PR to review and land | `playbook-ship`; to comment only, `playbook-review` |
| only a plan | `playbook-plan` |
| a question | answer it read-only; no pipeline |

## 1. Issue

The CTO/CEO creates the card: [playbook-plan step 1](../playbook-plan/SKILL.md#1-ctoceo-turn-the-problem-into-a-card), a
`planning` card for one outcome or an `epic` for an initiative.

## 2. Plan

[playbook-plan steps 2 to 5](../playbook-plan/SKILL.md#2-ctoceo-send-it-to-the-architect): the CTO/CEO sends the card to
the **architect** (its own agent only when no bot has the role) and ends its turn; the architect analyses the code,
posts the plan comment and sends it back. The CTO/CEO **checks the plan against the card** (the
[plan check](../playbook-plan/SKILL.md#5-ctoceo-confirm-then-stop): the `Goal` met, every scope line covered, a real
rejected approach, every choice decided or open as the asking rule allows, each gate a command) and accepts it or asks
for changes. A careful plan is what lets the code go in without the owner reviewing it.

**Do not stop at the acceptance.** Coding starts only after it, and the `Accepted by` comment says the packages are built
now under this playbook; then go on to stage 3. A request that already has an accepted plan starts at stage 3.

## 3. Code

### Package issues

Each package of the accepted plan becomes one `package` issue (the `write-issue` skill), keeping the plan's ID (`<ID>a`,
`<ID>b`). Split as in [playbook-quick step 1](../playbook-quick/SKILL.md#1-ctoceo-turn-the-problem-into-issues): one
issue per PR, the same wave never owns the same file, each shared contract written in the `Notes` of both issues, waves
under `Depends on`. Each child says `Refs #<card>`; list the children and their waves in the card's `## Notes`.

### The merge rules approve them

Run the gate on every package: `python3 <github skill>/scripts/issue_gate.py issue <n> --repo <owner>/<repo>`. As
shipped ([merge rules](../github/references/pull-requests.md#merge-rules)), an issue opened by an account with write access to
the repository (role admin, maintain or write) is approved, agent-signed or not, so the team's own issues need **no owner step**. The
gate still refuses a closed, refused or refusing-board issue.

Only an issue the gate refuses **as not approved**, such as one an outsider or a read-only member opened, waits for the
owner. Give them the links, in one message, each with one line that works in any shell, and your recommendation. Send
the packages that can go, then end your turn; never post the line yourself:

```bash
gh issue comment <number> -R <owner>/<repo> --body "Accepted by owner."
```

### Send each issue to its builder

| The issue's lane | Builder |
|---|---|
| `test` | the tester |
| `ops` | devops |
| any other | the developer |

The builder's **bot** gets a [handoff](assets/example/developer-brief.md) with your return address; your own agent (no bot
for the role) gets an [agent brief](assets/example/agent-brief-developer.md), which also gives its author name. Send
every issue of a wave together. A wave is sent only after what it depends on is **merged** (stage 4). Then end your turn.

### Builder: build, open, hand over

The builder bot gives the issue to one agent on its [row](../bot-orchestration/references/routing.md) of the agent table, then **verifies
the result itself** before the handover. The bot never codes.

1. Steps 1 to 5 of [playbook-quick step 3](../playbook-quick/SKILL.md#3-developer-one-issue-one-worktree-one-pr): the
   gate first, **its own worktree**, owned files, test first, commits under its name, the linters, the PR, green checks.
   It follows the accepted plan; a plan it cannot follow is `PR BLOCKED`, not a new design.
2. **Hand over.** The branch now belongs to the reviewer. Prove that everything is on GitHub:

   ```bash
   python3 <github skill>/scripts/pr_loop.py can-remove --worktree <path> --pr <n> --repo <owner>/<repo> --handover
   ```

3. An agent reports only to the bot that started it; that bot verifies, and sends the CTO/CEO the
   [handover report](assets/example/return-report.md). Then the worktree is removed
   (`ORCA worktree rm --worktree path:<path>`; refused: keep it, do not force it). A worker inside it reports
   first and removes it last.

The builder is then finished. Cancelled or [`PR BLOCKED`](assets/example/report-b.md) before that: report and keep the
worktree. Do not do its work or send it to another role: report the block and its one need to the owner.

## 4. Ship

### Hand the PR to the reviewer

Do **not** read the diff or run the commands: that is the reviewer's job. Send the
reviewer's **bot** a [handoff](assets/example/reviewer-brief.md) that links the accepted plan (or, with no such bot, your
own agent that wrote none of the PR an [agent brief](assets/example/agent-brief-reviewer.md)), then end your turn.

### Reviewer: review against the plan, and fix

A reviewer **bot** gives the loop to its own agent, from another model family when the team's table has one. The agent
signs with the **reviewer bot's** name, and the bot checks the verdict before it reports.

Follow the [review and fix loop](../reviewer/references/fix-loop.md): own worktree on the PR branch, a
`FAIL ... Round k of 3.` before each fix, **at most 3 rounds**, then a PASS that names its own commits, or
`Stopped by reviewer`. The reviewer checks the code against the issue **and the accepted plan**
([against the plan](../reviewer/SKILL.md#against-the-accepted-plan)): its packages, contracts, owned files and verify
commands. Every turn also does the [security and outbound-data check](../reviewer/SKILL.md#security-and-outbound-data):
a proven finding, or data going out that no accepted issue asks for, is a FAIL. So a package issue that needs an
outbound path **names the destination and the data** before it is built. **A departure from the plan is a finding** ([example](assets/example/verdict-fail.md)). An agent reports only
to the bot that started it. A reviewer **bot** sends the CTO/CEO the [review report](assets/example/review-report.md):
`REVIEW PASSED` or `REVIEW STOPPED`, the PR, the head SHA, the verdict link, rounds used and the commits it pushed.

### CTO/CEO: trust the verdict, merge, confirm

**Trust it: do not review again.** A reviewer bot has already checked its agent's work. With **no reviewer bot** the
verdict is your own agent's, and you are the bot that must verify it: run its evidence command once on that head before
you rely on it. That checks the claim; it is not a second review. Then check that it is a real verdict on what you are
about to merge:

```bash
python3 <github skill>/scripts/pr_loop.py can-merge --pr <n> --repo <owner>/<repo>   # PASS on this head, not the writer's
python3 <github skill>/scripts/issue_gate.py pr <n> --repo <owner>/<repo>            # merge rules: allowed
gh pr checks <n> --repo <owner>/<repo> --required                                    # required checks green
gh pr view <n> --repo <owner>/<repo> --json headRefOid,mergeable,mergeStateStatus    # not behind, no conflict
gh pr merge <n> --repo <owner>/<repo> --rebase --match-head-commit <passed sha> --delete-branch
```

`gh pr checks --required` printing `no checks reported` and exiting 1 means the repository has **no** checks, not that
one failed: report "no checks". Anything else refused: do not merge. A branch behind `main` or a red check goes **back to
the reviewer**, whose new head needs a new PASS. `risk:money-path`: ask a person to merge. Running this playbook gives the
CTO/CEO the merge; a project whose rules reserve it for a person, or ask for other approvals, wins.

Then confirm as [playbook-quick step 5](../playbook-quick/SKILL.md#5-ctoceo-merge-then-confirm) (`MERGED`, the
issue `CLOSED`), post the [merge comment](assets/example/merge.md) and tell the reviewer `MERGED`. It
[removes its worktree](../reviewer/references/fix-loop.md#remove-your-worktree). Merge in dependency order, then send
the next wave (stage 3). **When every child is merged**, run the card's `Done when` on `main`, post a `close` comment and
close the card. Report to the owner once ([example](assets/example/report.md)).

### The loop breaks

The reviewer posts [`Stopped by reviewer`](assets/example/stopped.md), marks the issue blocked and removes its worktree.
**The PR stays open, the branch stays on GitHub, the issue stays open.** The CTO/CEO does not merge, overrule or restart
it: it reports the verdict to the owner. Work that depends on it is not sent; other issues carry on; the card stays open.

## One good, one bad

- **Good:** the CTO checks the plan against the card and accepts it, writes three package issues the gate approves, sends
  the `ops` issue to devops and the backend one to the developer, merges each head the reviewer passed (the reviewer
  having caught a departure from the plan), then sends the `test` issue of wave 2.
- **Bad:** the CTO stops at the accepted plan, waits for the owner to accept issues the team opened, writes the tests itself
  because the tester was slow, or re-reads the diff after a PASS and merges a head pushed after it.

## Done

- The card has an accepted plan; every package is **merged** (a PASS on the merged head, the merge confirmed, the issue
  closed) or **stopped**; when all are merged, the card is closed.
- No PR got more than 3 rounds; no builder, reviewer or check worktree is left; no worker is running.
- The owner has one report: what merged, what stopped or is blocked, and **which commits only the reviewer saw**.

## Never

- Build or merge for an issue the gate refuses, or write the owner's acceptance.
- Plan, code, test, deploy or review as the CTO/CEO, or start an agent for a role a bot holds.
- Let a builder or the reviewer's author judge its own PR, or one agent be both builder and reviewer.
- Merge without `can-merge`, on a new head, with a red required check, or with an admin override.
- Pass or merge without the security check, or add an outbound path to an issue after its code to make it pass.
- Auto-merge a money path, ask for a fourth round, or close a stopped PR.
