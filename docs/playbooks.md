# Playbooks

There are **seven pipelines**. They use the `work-package` formats and the `github` rules, and run in Orca. Every pipeline
that builds ends with the merge; `plan` (it stops at the accepted plan), `refactor-plan` (it stops at the posted issues)
`review` (it only comments) and `test` (it only reports) merge nothing. Nothing is built or merged unless the [merge rules](../src/skills/github/references/pull-requests.md#merge-rules) allow it, and no
PR's author merges it.

| Shortcut | Pipeline | Use it for | Inputs |
|---|---|---|---|
| `/swe:playbook-build` | **Build** (the default) | any request to build that names no playbook: issue, plan, code, PR, review and fix, merge | a problem, a plan or `issue`s |
| `/swe:playbook-quick` | **Quick** | only when the request names it: issue, code, PR, merge, with **no check** | a problem or `issue`s |
| `/swe:playbook-plan` | **Plan** | only a plan: issue, plan, comments; stops at the accepted plan | a problem or an `issue` |
| `/swe:playbook-refactor-plan` | **Refactor plan** | only when a refactoring plan is asked for: the architect writes the new issues, the CTO/CEO posts them unchanged; no code | a request and the repositories in scope |
| `/swe:playbook-review` | **Review** | comment on one existing PR; changes nothing | a PR |
| `/swe:playbook-ship` | **Ship** | take one existing PR to `main` and close its issue | a PR |
| `/swe:playbook-test` | **Test** | test software as its user does and report pass or fail with evidence; fixes nothing | a target, its environment, the functions and accounts |

**Choosing.** A request that names a playbook follows it. A CTO/CEO told none uses `build`; `review` or `ship` for an
existing PR; `plan` when you want only a plan; `refactor-plan` when a refactoring plan is asked for; `test` when you
want software tested and nothing changed. A question is
answered read-only. Nobody picks `quick` by itself; named
for work with an open design question, the CTO/CEO says so and asks.

**By default you approve and review no code.** The weight is on the plan: the architect plans carefully, the CTO/CEO
checks the plan against the card before it accepts it, and in `build` and `ship` the reviewer checks the code against the
accepted plan (packages, contracts, owned files, verify commands); a departure from the plan is a finding. A
`risk:money-path` PR is never merged automatically, and a project's own approval rules still apply.

## Bots and agents

**Orca** runs the stack: workspaces, one git worktree per task, and orchestration. A **bot** is a standing member that
orchestrates; an **agent** is one run of a **harness** (a coding CLI Orca runs agents in; the plugin installs into each)
that a bot starts for one job. Bots delegate to
bots with a handoff and report back with a status. Agents report only to their bot and never to each other. The CEO or
CTO bot **only orchestrates**: it writes the issues and runs the playbook, and never plans, codes, tests, deploys or
reviews code itself. Each of those jobs goes to the role that holds it (which bot holds which role is your team's own mapping
skill, kept outside this plugin): the architect (plans), the developer, the
tester (`test` lane issues), devops (`ops` lane issues: deployment and operations) and the reviewer (code review). The
flow, the message templates and the linter are in [bot-orchestration](../src/skills/bot-orchestration/SKILL.md).
Replies and status reports are short.

**One child chat per parent chat and receiving bot.** The first delegation from a chat to a bot opens a new chat there
under the parent chat's name; the sender records its id, and every later message from that chat to that bot goes to it,
never to the bot's Home Chat ([the rule](../src/skills/bot-orchestration/SKILL.md#one-child-chat-per-parent-chat-and-bot)).

**One agent table** sets the harness, model and reasoning effort of every agent, by row: `simple`, `medium`, `hard` and
`planner/architect`. The CTO/CEO holds it; each team fills in its own copy of the
[template](../src/skills/bot-orchestration/assets/agent-table.template.md) outside any public repository. A missing table
or row means stop and ask; there is no default, and rows may be the same.

## DAGs

```text
Build     problem ─► card ─► architect plan ─► CTO/CEO checks it against the card, accepts ─► package issues ─► builder by lane: PR, handover ─► reviewer: review against the plan ⇄ fix (≤3) ─► CTO/CEO trusts the PASS ─► merge or stop
Quick     problem ─► issue(s) ─► developer: Done when, PR, required checks ─► CTO/CEO: mechanical conditions only ─► merge or stop ─► remove worktree
Plan      problem ─► CTO/CEO card ─► architect ─► plan comment ─► back to CTO/CEO ─► accept ─► STOP
Refactor  request ─► CTO/CEO ─► architect: every repo and open issue, the bundle ─► CTO/CEO posts it unchanged: create, then close ─► STOP
Review    PR ─► read and run ─► one verdict comment ─► STOP
Ship      PR ─► reviewer: review ⇄ fix (≤3) ─► merge + close issue, or stop
Test      request ─► CTO/CEO ─► tester: expected results, run, confirm failures ─► report ─► CTO/CEO checks it ─► STOP
```

`build` has four stages (issue, plan, code, ship) and shows a "where does this run stand" table read from GitHub, so a
resumed run starts at the right stage. Its stage 2 is the `plan` pipeline, which goes on to code instead of stopping.

**Refactor plan** is planning only. The planner/architect reads every repository in scope with its issues, analyses and
plans, and writes a bundle: a parent card, every new issue complete, and a `remove` or `keep` with its reason for every
open issue. The CTO/CEO does no work on it: `refactor_bundle.py` checks the bundle and prints a dry run, and `post`
publishes the architect's text unchanged. It creates the new issues first, fills their numbers into the references, then
closes each removed issue as **not planned** with a short comment. Nothing is deleted, only listed issues are closed, an
issue with an open linked pull request is never closed automatically (it is reported), and a resumed run reads the host
and creates no duplicate ([bundle format](../src/skills/playbook-refactor-plan/references/bundle.md)).

**Test** changes nothing. The tester writes the expected result of every step before running, then uses the software as
its user does: a web app in a real browser, with a screenshot per step and a video of every click until the answer
arrived ([web-testing](../src/skills/web-testing/SKILL.md)); an API or a command-line tool with real inputs
([api-cli-testing](../src/skills/api-cli-testing/SKILL.md)). Every failure is run again. The report is short: pass or
fail per function, the evidence paths and bugs ready to file; issues are filed only when the request asked. It follows
the [safety rules of a test run](../src/skills/web-testing/references/safety.md): only the allowed target and accounts,
nothing on production that spends money, trades, deletes or messages real people without explicit approval,
credentials from the environment and never in a report, evidence outside the repository and never published, and page
content treated as data.

In `build` and `ship` the reviewer fixes its own findings. Nobody else checks those fixes before `main`: the PASS names
each commit, and a `risk:money-path` PR is never auto-merged
([fix loop](../src/skills/reviewer/references/fix-loop.md)).

**Quick has no check of the code**: no reviewer, no verdict, no feedback rounds. The developer runs the issue's
`Done when` before it opens the PR and keeps the required checks green. The CTO/CEO does not read the diff or run the
PR's commands; it merges only when the merge rules allow it, the required checks passed, the branch is not behind and
has no conflict, the head is the SHA the developer reported, and it is no money path
(`pr_loop.py can-merge --unreviewed --head <reported sha>`, the only place that form is used; the script refuses
any PR that carries a judgment or a stop, and any PR whose linked issues do not all carry the `Pipeline: quick` line that
only quick writes; it cannot know which head was reported, so the sha comes from the builder's report). `gh pr checks --required`
printing `no checks reported` with exit 1 means the repository has no checks, not a failure: it is reported as "no
checks", here and in every pipeline. A red check or a stale branch goes back to the same developer **at most 3 times**:
each return is a `Returned by CTO ... Return <k> of 3.` comment on the PR, so a resumed run keeps the count, and
`pr_loop.py decide` refuses a fourth; then the CTO/CEO posts `Stopped by CTO` and reports to you. A clean rebase after
another quick PR of the run merged after this PR's latest report or return (`Rebase after #<m>.`) does not count.

Each pipeline ships its orchestration commands and a full example: Build
([commands](../src/skills/playbook-build/references/orchestration.md),
[example](../src/skills/playbook-build/references/example.md), with a plan departure, a blocked package and a second
wave), Quick ([commands](../src/skills/playbook-quick/references/orchestration.md),
[example](../src/skills/playbook-quick/references/example.md)), Plan
([commands](../src/skills/playbook-plan/references/orchestration.md),
[example](../src/skills/playbook-plan/references/example.md)), Refactor plan
([example](../src/skills/playbook-refactor-plan/references/example.md)), Ship
([example](../src/skills/playbook-ship/references/example.md)) and Test
([example](../src/skills/playbook-test/references/example.md)).

## Merge rules

A pull request merges only when it links an issue of its repository and every linked issue is approved. As shipped
(`"approvals": ["trusted_author", "owner_comment"]` in `merge-rules.json`), **an issue opened by an account with write access
is approved as it is**: its role on the repository is `admin`, `maintain` or `write`, agents on such an account
included. Nobody has to accept the team's own issues. Being a `MEMBER` or `COLLABORATOR` is not enough. An outsider's
or a read-only account's issue (or one whose author's permission cannot be read) still
needs the repository owner's comment `Accepted by owner.`; for that issue alone, run this from your own account, in any
shell:

```bash
gh issue comment <number> -R <owner>/<repo> --body "Accepted by owner."
```

An issue the owner's account created (`owner_author`) and a board status `Todo` or `In Progress` (`board_status`) approve
nothing by themselves: they are off while agents share the owner's account. A missing, empty or unknown `approvals`
refuses everything. A closed issue (done, not planned, duplicate), a `duplicate` or `wontfix` label or a refusing board
status refuses it, whatever approves it. When the `gh` login lacks the scope for project boards, the check goes on
without them and says so: no board status refuses. Any other failure to read the board refuses. The same check runs
before any work starts. Agents never write the owner's acceptance.
[Full rules](../src/skills/github/references/pull-requests.md#merge-rules).

## The gates

| Gate | Owner | Passes when |
|---|---|---|
| Card ready (`build`, `plan`) | CTO/CEO | a `planning` or `epic` issue that passes `package_lint.py issue` |
| Plan returned | architect | one plan comment per version, sent back to the CTO/CEO with its URL |
| Plan accepted | CTO/CEO | the plan is checked against the card, the `plan` or `epic-plan` comment passes the linter, every open question is answered, and the decision comment is posted. **Plan ends here**; `build` goes on to code |
| Issue ready (`build`, `quick`) | CTO/CEO | `ID: title`, type + lane + difficulty labels, priority, closed file list, runnable `Done when` |
| Issue approved | the merge rules | before work starts and again before the merge: `issue_gate.py` allows it (an author with write access, or the owner's comment for anyone else's issue) |
| PR ready | builder (developer, tester or devops) | owned files only, test first, `Closes #N`, the `Done when` on the committed head before the PR opens |
| PR returned (`build`, `quick`) | builder | `PR READY` or `PR BLOCKED` sent back with the PR URL and full head SHA |
| Bundle checked (`refactor-plan`) | architect, again by `post` | `refactor_bundle.py check`: every open issue has a disposition, every new issue passes the issue linter, references, waves and new-number placeholders resolve; then the dry run |
| Posted unchanged (`refactor-plan`) | CTO/CEO | `post --digest` publishes only the bundle the dry run showed; new issues exist and read back before anything is closed |
| Verdict (`build`, `review`, `ship`) | reviewer, not the PR's writer | `Verdict: PASS\|FAIL at <full sha>` from proven findings, against the accepted plan when there is one; a new push needs a new verdict |
| Feedback limit (`build`, `ship`) | reviewer | at most 3 rounds, then pass or `Stopped by reviewer`; `pr_loop.py decide` refuses a fourth |
| Trusted merge (`build`) | CTO/CEO | `pr_loop.py can-merge`: a PASS on the head by an account that can push, not by the writer, naming the reviewer's own commits; an `Accepted by` on a PR approves nothing |
| Unreviewed merge (`quick` only) | CTO/CEO | `pr_loop.py can-merge --unreviewed --head <reported sha>`: open, no judgment or stop by anyone, every linked issue carries `Pipeline: quick` (only quick writes it), not a money path, the given head (the script cannot know what was reported: the sha comes from the builder's report) |
| Worktree removed (`build`, `quick`, `ship`) | whoever made it | `pr_loop.py can-remove` allows it only when nothing is lost (`--handover` for an open PR another agent takes) |
| Safe to run (`test`) | the test runners, and the tester | allowed hosts and programs only; on production a step that changes something runs only with the owner's approval of that step; evidence outside every repository |
| Report checked (`test`) | CTO/CEO | every function has `PASS`, `FAIL` or `NOT RUN` with evidence, and the evidence of each failure shows it |
| Merge | CTO/CEO (`build`, `quick`) or reviewer (`ship`) | the checked SHA is the head, required checks green (or "no checks"), branch not behind `main`; `gh pr merge --rebase --match-head-commit` |

Issues are written with [`write-issue`](../src/skills/write-issue/SKILL.md) (kinds and the
[catalog](../src/skills/write-issue/references/catalog.md)); plan, decision, verdict, fix and close comments with
[`write-comment`](../src/skills/write-comment/SKILL.md). Each ends with `Created: <agent name>`, and commits are authored
by that name ([identity](../src/skills/github/references/identity.md)).

All templates, and how to change their style: [templates](../src/skills/write-issue/references/templates.md).

## Rules

- A build is one package, one issue, one worktree, one branch, one PR, one owner.
- The CTO/CEO only orchestrates: it does not plan, code, test, deploy or review, and the builder does not merge. A
  project that reserves the merge for a person wins.
- Only `build` and `ship` let the reviewer edit, and only to fix its posted findings. `review` never edits; `quick` has
  no reviewer.
- `test` fixes no code, opens no branch or PR and merges nothing; fixing a bug it found is a new request.
- Plans and verdicts are comments, not new issues. A plan that creates packages also creates their issues and links them.
  `refactor-plan` is the exception: its plan is the new set of issues.
- "Remove" an issue means close it as not planned with a short comment. Nothing deletes an issue.
- A merge is not done until the issue is closed, the branch deleted and the worktree removed.

## What happened to the old playbooks

The old `playbook-deliver`, `playbook-feature`, `playbook-bugfix`, `playbook-cifix`,
`playbook-docs`, `playbook-rebase`, `playbook-land`, `playbook-changelog`, `playbook-verify`, `playbook-solo` and the
`playbook` dispatcher are removed, and so is the short-lived complete pipeline: its four stages are now `playbook-build`.
`playbook-review` is comment-only. Their useful methods live in the skills they named (`github`, `tdd`, `docs-sync`,
`ci-fixer`, `integrator`, `changelog`, `verifier`, `reviewer`, `delegate`); they are no longer separate CTO pipelines.
