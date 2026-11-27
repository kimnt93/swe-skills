---
name: playbook-solo
description: "The solo pipeline, only when a request names it: one agent takes the given problems and writes them as issues, then for each, in dependency order, makes its own worktree and branch, builds the complete issue with unit and functional tests, opens one PR, checks it itself and merges it, confirms, closes the work and removes the worktree; one report at the end. It starts no other agent or bot and hands nothing over. The check before each merge is a self-check, not an independent review, and posts no reviewer verdict. A money-path change stops with the PR open. Never picked by itself: with no playbook named, use playbook-build."
metadata:
  group: start
  summary: "Solo, only when named: one agent, from problems to merged PRs; self-checked, no review"
---

# Playbook: Solo

Problems go in; **one agent** turns them into issues and takes each to **merged** or **blocked**, one at a time. A full
report comes at the end.

```text
problems ─► issues, in dependency order
for each issue ─► own worktree and branch ─► the complete issue with its tests ─► one PR ─► self-check
                     ├─ everything holds ─► rebase merge ─► confirm ─► close the work ─► remove the worktree
                     └─ money path or blocked ─► issue and PR stay open ─► the independent issues go on
all issues done or blocked ─► one report
```

**The check before each merge is a self-check, not an independent review.** The agent that wrote the code is the only
one that looks at it. Say so in every PR, merge comment and report. **Post no reviewer verdict:** no `Verdict:` line,
no verdict comment, no `Accepted by` on a PR.

**Asking** follows [the asking rule](../principles/references/never-block-on-the-human.md); the stops this playbook
names stay. Ask the person who gave you the problems.

## When to use it, and who runs it

**Only when the request names `playbook-solo`.** Nobody picks it by itself, whatever the size of the work: with no
playbook named, use [playbook-build](../playbook-build/SKILL.md).

**One agent runs it, the one a person asked directly,** and does every step itself. It **starts no other agent,
subagent or bot and hands nothing over:** no brief, handoff, helper or review request. Where a skill or method it uses
would start one, it does that work itself. A bot does not run this playbook or pass it to an agent it starts: under
[bot-orchestration](../bot-orchestration/SKILL.md) a bot never does a task itself, and an agent a bot started never
merges. A bot that gets such a request says so and asks: give it to an agent directly, or name another playbook.

A project whose rules reserve the merge for a person, or ask for a review, wins: build, open the PR, leave it open.

## 1. Turn the problems into issues

Use [write-issue](../write-issue/SKILL.md): search first, then one `package` issue per pull request, on the repository
that owns the code. Two or more get a parent `epic` that lists them. An existing issue that passes the linter is used.

- **Complete:** each holds its feature, [unit tests and functional tests](../developer/SKILL.md#what-you-deliver):
  test files under `Owned files`, both kinds in its `Done when`. No test issue, and
  [no tester](../bot-orchestration/SKILL.md#the-tester-only-on-request).
- **Order:** name what each needs under `Depends on`. That order is the list you work through, one issue at a time.
- **Money path** (the **money-path** principle): label it `risk:money-path` and `hard`.
- **No unasked data:** an issue names an outbound destination and its data only when the person's problem does. Never
  write one in to get your own change through the security check; a change that needs one is a question.
- **No `Pipeline:` line:** that line is playbook-quick's alone.

**The gate, unchanged:** `python3 <github skill>/scripts/issue_gate.py issue <n> --repo <owner>/<repo>` on every issue
before its worktree. Who may approve an issue is the [merge rules'](../github/references/pull-requests.md#merge-rules)
alone: one your account opens is approved only as any account with write access has it approved, which means nobody
else has read it. Never write the owner's acceptance. Only for an issue refused **as not approved**, such as an
outsider's, give the owner its link and this line, and go on with the independent issues:

```bash
gh issue comment <number> -R <owner>/<repo> --body "Accepted by owner."
```

## 2. For each issue, in dependency order

Start an issue only when what it depends on is **merged**. One that already has an open PR, or somebody else's worktree
on its files (`ORCA worktree ps`), is not yours: report it.

**Its own worktree and branch,** from the newest `main`, with no agent started in it (no `--agent`, no `--prompt`):

```bash
git fetch origin
ORCA worktree create --repo <repo> --name <id-lowercase> --branch <id-lowercase>/<slug> --base-branch origin/main
```

**Build the complete issue** there, with the [developer](../developer/SKILL.md) skill (steps 0 to 5) and the language
skill: owned files only, test first, unit and functional tests, `deslop`, commits under your name.

**One PR.** Run the `Done when` on the committed head. Write the [PR template](../work-package/assets/pr.template.md)
body: `Closes #<n>`, both test lines (or why one kind cannot apply) and the words
**self-check, not an independent review** ([example](assets/example/pr.md)). Run `package_lint.py pr` and
`pr_lint.py local`, push, open the PR, and watch `gh pr checks <n> --required`; fix what fails (`ci-fixer`).

## 3. Self-check, then merge

Before the merge, read and obey the project's [business rules](../principles/references/business-rules.md).
All of this holds for **one head SHA**, the PR's. Any new commit or rebase starts the list again.

1. **Yours and unjudged:** `agent_identity.py check --author "<you>"` reports 0 problems, so you wrote every commit.
   `pr_loop.py state` and `gh pr view <n> --comments` show no verdict, change request or stop, and nobody asks to hold.
   A PR somebody else wrote or judged is never merged here: that is `playbook-ship`.
2. **Not a money path:** no `risk:money-path` label on the PR or a linked issue, and the diff touches no orders, fills,
   positions, balances, risk limits or P&L, nor a high-risk path the project's business rules add
   ([step 5](#5-a-money-path-or-a-blocked-issue)).
3. **`Done when`:** exits 0 on the committed head, with a clean tree.
4. **Security:** the [security-review](../security-review/SKILL.md) skill on the diff: run the installed scan, resolve
   every item, list every path data leaves by, work the topics the diff touches and prove each suspicion. It must end
   with **no proven finding** and **no outbound data the accepted issue does not ask for** (read that only from
   `issue_gate.py asked`). An unread part, an untraced destination or a scan that scanned nothing (exit 2): no merge.
   Put the result under `## Verification` in the PR body, not in a verdict.
5. **Merge rules, checks, branch:** `merge rules: allowed`; required checks green; not behind `main`, no conflict.

```bash
python3 <github skill>/scripts/agent_identity.py check --author "<you>"                # on the branch: 0 problems
python3 <github skill>/scripts/pr_loop.py state --pr <n> --repo <owner>/<repo>       # 'head not judged', 0 rounds
gh pr view <n> --repo <owner>/<repo> --comments
gh pr view <n> --repo <owner>/<repo> --json labels,closingIssuesReferences           # then each issue's labels
python3 -I <security-review skill>/scripts/security_scan.py --base origin/main --head <checked sha>
python3 <github skill>/scripts/issue_gate.py asked <issue> --repo <owner>/<repo> --pr <n>   # for an outbound path
python3 <github skill>/scripts/issue_gate.py pr <n> --repo <owner>/<repo>            # merge rules: allowed
gh pr checks <n> --repo <owner>/<repo> --required                                    # required checks green
git fetch origin && git merge-base --is-ancestor origin/main <checked sha>           # exit 0: not behind
gh pr view <n> --repo <owner>/<repo> --json headRefOid,mergeable,mergeStateStatus    # that head, no conflict
gh pr merge <n> --repo <owner>/<repo> --rebase --match-head-commit <checked sha> --delete-branch
```

`no checks reported` with exit 1 means the repository has no checks, not a failure: say "no checks". Behind `main`:
rebase your branch (`agent_identity.py git ... -- rebase origin/main`, then `git push --force-with-lease`) and check
the new head. A rebase that conflicts is aborted and blocks the issue: a resolution
[needs a fresh review](../integrator/SKILL.md), which this playbook has not. Never `--admin`.

**`pr_loop.py can-merge` has no form for a self-merge, and this playbook changes no gate.** Its plain form needs
another agent's PASS; its unreviewed form is playbook-quick's alone. Never post a verdict or write quick's issue line
to make it allow. So **no script refuses a solo merge** for a money path, a judged PR or a moved head: items 1 and 2
are yours to hold, and `--match-head-commit` holds the head.

## 4. Confirm, close, remove the worktree

**The merge command's exit is not proof.**

```bash
gh pr view <n> --repo <owner>/<repo> --json state,mergeCommit,closingIssuesReferences   # MERGED
gh issue view <issue> --repo <owner>/<repo> --json state                                # CLOSED
python3 <github skill>/scripts/pr_loop.py can-remove --worktree <path> --pr <n> --repo <owner>/<repo>
ORCA worktree rm --worktree path:<path>
```

Check your name on the new commits of `main`, then post the `merge` comment
([example](assets/example/merge.md)). An issue left open although its PR said `Closes` gets a `close` comment and is
closed; a `Refs` issue stays open. `can-remove` allows it, or the worktree stays: never `--force` or
`--delete-branch`. Leave a worktree before removing it. Then take the next issue from the new `main`. When every child
is merged, run the parent's `Done when` on `main`, post a `close` comment and close it.

## 5. A money path or a blocked issue

- **Money path:** build it (with its replay test), open the PR, self-check it, and **stop with the PR open**. A person
  reviews and merges it.
- **Blocked:** the gate refuses, the `Done when` or a required check cannot pass without weakening a test or leaving the
  owned files, a finding cannot be fixed inside the issue, a rebase conflicts, the host refuses the merge, or a
  question the asking rule keeps open has no answer.

Push what is committed. Post `Status: blocked` on the issue with the PR link, the evidence and the one thing needed.
**The issue stays open, and the PR and its branch stay;** with no PR yet, never open one whose `Done when` fails.
Keep its worktree: `can-remove` allows removing an open PR's worktree only after a `Stopped by` line from a CTO, CEO or
reviewer. You are none of these, so post no such line; nor use `--handover`. Name the worktree in the report.

**Issues that depend on it wait. Independent issues go on.**

## State: read it from the host

| For each issue | Next |
|---|---|
| no PR, nothing unmerged before it | step 2; a worktree of yours that exists is reused |
| your open PR, not blocked | step 3, the whole list, on its current head |
| `Status: blocked`, or a money path with its PR open | leave it; go on with the independent ones |
| merged | step 4, whatever is left of it |

## 6. One report

Once, when every issue is merged, blocked or waiting ([example](assets/example/report.md)): the problems and the
issues in order; for each merged one, the PR and full head SHA; for each blocked or waiting one, why, what it needs and
the worktree kept; any test kind left out, with why; the choices you made; and that **every merge rests on the
author's self-check, with no independent review**.

## One good, one bad

- **Good:** two problems become two issues. The agent builds the first with unit and functional tests, checks that
  head itself, merges it, removes its worktree, then starts the second. The second moves money, so it leaves the PR
  open and reports: "1 merged on my own check, with no independent review; 1 waits for a person."
- **Bad:** the agent starts a helper to review its PR, posts `Verdict: PASS`, writes quick's line on the issue so that
  a script allows the merge, or stops everything because one issue is blocked.

## Done

- Every issue is **merged** (self-check on that head, merge and closed issue confirmed, worktree removed), **blocked**
  or waiting on a blocked one (open, named in the report).
- No other agent or bot was started or asked, and no verdict was posted. The person has one report.

## Never

- Run this playbook unnamed, start or message another agent or bot, or hand any part over.
- Call the self-check a review, or post a verdict.
- Merge a money path, a PR you did not write alone or one somebody judged, a head you did not check, or with a failed
  check, a proven finding, unasked outbound data or an admin override.
- Weaken a test, check or gate, write the owner's acceptance, or write an outbound path into an issue to pass.
- Close a blocked issue or its PR, delete its branch, or remove a worktree by force.
