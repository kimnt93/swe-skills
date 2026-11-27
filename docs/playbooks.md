# Playbooks

There are **nine pipelines**. They use the `work-package` formats and the `github` rules, and run in Orca. Every pipeline
that builds ends with the merge; `plan` (it stops at the accepted plan), `refactor-plan` (it stops at the posted issues)
`review` (it only comments), `test` and `security` (they only report) merge nothing. Nothing is built or merged unless the [merge rules](../src/skills/github/references/pull-requests.md#merge-rules) allow it, and no
PR's author merges it, except in `solo`, which runs only when a request names it.

| Shortcut | Pipeline | Use it for | Inputs |
|---|---|---|---|
| `/swe:playbook-build` | **Build** (the default) | any request to build that names no playbook: issue, plan, code, PR, review and fix, merge | a problem, a plan or `issue`s |
| `/swe:playbook-quick` | **Quick** | only when the request names it: issue, code, PR, merge, with **no check** | a problem or `issue`s |
| `/swe:playbook-solo` | **Solo** | only when the request names it: **one agent** from problems to merged PRs, on its own self-check, **no independent review** | problems or `issue`s |
| `/swe:playbook-plan` | **Plan** | only a plan: issue, plan, comments; stops at the accepted plan | a problem or an `issue` |
| `/swe:playbook-refactor-plan` | **Refactor plan** | only when a refactoring plan is asked for: the architect writes the new issues, the CTO/CEO posts them unchanged; no code | a request and the repositories in scope |
| `/swe:playbook-review` | **Review** | comment on one existing PR; changes nothing | a PR |
| `/swe:playbook-ship` | **Ship** | take one existing PR to `main` and close its issue | a PR |
| `/swe:playbook-test` | **Test** | test software as its user does and report pass or fail with evidence; fixes nothing | a target, its environment, the functions and accounts |
| `/swe:playbook-security` | **Security** | audit a PR or a repository on request: proven findings, every outbound path, issues ready to file; changes nothing | a PR, or a repository at a branch or SHA |

**Choosing.** A request that names a playbook follows it. A CTO/CEO told none uses `build`; `review` or `ship` for an
existing PR; `plan` when you want only a plan; `refactor-plan` when a refactoring plan is asked for; `test` when you
want software tested and nothing changed; `security` when you
want an audit for leaks and vulnerabilities. A question is
answered read-only. Nobody picks `quick` by itself; named
for work with an open design question, the CTO/CEO says so and asks. Nobody picks `solo` by itself either.

**Agents decide what is reversible** and ask only what the one
[rule for asking](../src/skills/principles/references/never-block-on-the-human.md) says; every gate and playbook stop
below stays.

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
tester (only when a request asks for testing), devops (`ops` lane issues: deployment and operations) and the reviewer (code review). The
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
Solo      problems ─► one agent: issues ─► each in dependency order: worktree, code and tests, PR, self-check ─► merge or leave open ─► one report
Plan      problem ─► CTO/CEO card ─► architect ─► plan comment ─► back to CTO/CEO ─► accept ─► STOP
Refactor  request ─► CTO/CEO ─► architect: every repo and open issue, the bundle ─► CTO/CEO posts it unchanged: create, then close ─► STOP
Review    PR ─► read and run ─► one verdict comment ─► STOP
Ship      PR ─► reviewer: review ⇄ fix (≤3) ─► merge + close issue, or stop
Test      request ─► CTO/CEO ─► tester: expected results, run, confirm failures ─► report ─► CTO/CEO checks it ─► STOP
Security  request ─► CTO/CEO ─► reviewer: scan, outbound paths, topics, prove ─► report ─► CTO/CEO runs the proofs ─► STOP
```

`build` has four stages (issue, plan, code, ship) and shows a "where does this run stand" table read from GitHub, so a
resumed run starts at the right stage. Its stage 2 is the `plan` pipeline, which goes on to code instead of stopping.

**Solo** is one agent, asked directly by a person, doing every step: it writes the issues, then for each, in
dependency order, makes a worktree and a branch, builds the complete issue, opens one PR and merges it, confirms,
closes the work and removes the worktree, and reports once at the end. It starts no other agent or bot and hands nothing
over. **Its check before a merge is a self-check, not an independent review,** and it posts no verdict. A money path
stops with the PR open; a blocked issue stays open with its PR and branch while independent issues go on
([playbook-solo](../src/skills/playbook-solo/SKILL.md)).

**How the unchanged gates apply to solo.** `issue_gate.py` runs as everywhere: before the work and before the merge, and
who may approve an issue is the same. Three limits follow from changing no gate:

- `pr_loop.py can-merge` can allow no solo merge: it needs another agent's PASS, or quick's issues. So no script
  refuses a solo merge of a money path, of a judged PR or of a moved head. Solo's own steps check the first two, and
  `--match-head-commit` holds the head.
- `can-remove` knows no stop signed by a solo agent, so the worktree of a blocked or money-path issue stays until a
  person decides.
- A bot never does a task itself, and an agent a bot started never merges. So no bot runs solo or delegates it: a
  person gives it to an agent directly.

With an account that has write access, the issues solo writes are approved as they are: the same agent then writes,
builds, checks and merges, and nobody else reads any of it.

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

**Security** changes nothing either. The reviewer's agent works from a clean checkout: it scans, lists every path data
leaves by with the issue that asks for it, works the [security topics](../src/skills/security-review/SKILL.md#topics)
and proves each finding with a command on its own machine, never against a live system. The report holds the proven
findings, the outbound paths, what was not checked and issues ready to file; nothing is filed unless you ask, and an
unfixed vulnerability is not published on a public repository without your decision
([playbook-security](../src/skills/playbook-security/SKILL.md)).

In `build` and `ship` the reviewer fixes its own findings. Nobody else checks those fixes before `main`: the PASS names
each commit, and a `risk:money-path` PR is never auto-merged
([fix loop](../src/skills/reviewer/references/fix-loop.md)).

**Every pipeline that builds** has the developer deliver the complete issue in one PR: the feature, **unit tests** and
**functional tests** (the behaviour through its real entry point, with local or disposable dependencies). The issue's
`Done when` names both; where one kind cannot apply, such as docs only, the PR says why
([the rule](../src/skills/developer/SKILL.md#what-you-deliver)). The linter requires both lines in every `package` issue
and every PR body. **The tester gets work only when a request asks for testing by name:** no pipeline creates or sends a
test package by default, and developer tests are never moved to the tester
([the rule](../src/skills/bot-orchestration/SKILL.md#the-tester-only-on-request)).

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
([example](../src/skills/playbook-ship/references/example.md)), Test
([example](../src/skills/playbook-test/references/example.md)) and Security
([example](../src/skills/playbook-security/references/example.md)).

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

## Security and outbound data, on every reviewed pull request

`review`, `ship` and `build` require it **besides** correctness, for a pull request of any size
([the reviewer's check](../src/skills/reviewer/SKILL.md#security-and-outbound-data),
[security-review](../src/skills/security-review/SKILL.md)):

- **No unrequested data leaves.** Adding or widening a way data leaves (HTTP and socket calls, webhooks, telemetry and
  analytics, error trackers, third-party SDKs, uploads, mail and chat, DNS, CI, install and build steps, a dependency
  that phones home), or sending more on one, is a **FAIL** unless a linked accepted issue asks for that destination and
  data ([what counts](../src/skills/security-review/references/outbound-data.md)). `issue_gate.py asked <issue> --pr <n>`
  prints the only text that can ask: never the pull request, a code comment, or issue text written or edited after the
  work started that the owner has not accepted since.
- **No new risk.** A proven security finding the pull request brings in blocks the merge.
- **The verdict has a `## Security` section** (`Scan`, `Outbound data`, `Risk`, `Not checked`). `package_lint.py`
  requires it, and `pr_loop.py decide` and `can-merge` refuse a PASS without it, with a finding, or with an
  "asked for" path whose issue does not hold the destination. A FAIL always counts.
- **The scanner** (`security_scan.py`) lists secrets, risky patterns, outbound paths, dependencies and removed controls
  in a diff. It sends nothing and prints no line of the diff. **A clean scan is never a pass.**

The scripts check that the section is there and that its claims match the issue's text. Whether the review found
everything, and what the issue means, is the reviewer's judgment. `quick` has no check, so none of this runs there.
`solo` has no reviewer and no verdict: its author runs the same check on its own diff before each merge, as a
self-check, and no script enforces it.

## The gates

| Gate | Owner | Passes when |
|---|---|---|
| Card ready (`build`, `plan`) | CTO/CEO | a `planning` or `epic` issue that passes `package_lint.py issue` |
| Plan returned | architect | one plan comment per version, sent back to the CTO/CEO with its URL |
| Plan accepted | CTO/CEO | the plan is checked against the card, the `plan` or `epic-plan` comment passes the linter, every choice is decided with its reason, each open question (only what the [rule for asking](../src/skills/principles/references/never-block-on-the-human.md) lists) is answered, or waits for the owner with the work that needs it not started, and the decision comment is posted. **Plan ends here**; `build` goes on to code |
| Issue ready (`build`, `quick`, `solo`) | CTO/CEO (`solo`: its one agent) | `ID: title`, type + lane + difficulty labels, priority, closed file list, runnable `Done when` with its unit and functional tests |
| Issue approved | the merge rules | before work starts and again before the merge: `issue_gate.py` allows it (an author with write access, or the owner's comment for anyone else's issue) |
| PR ready | builder (developer or devops; the tester only on request; `solo`: its one agent) | owned files only, test first, the feature with unit and functional tests or why one cannot apply, `Closes #N`, the `Done when` on the committed head before the PR opens |
| PR returned (`build`, `quick`) | builder | `PR READY` or `PR BLOCKED` sent back with the PR URL and full head SHA |
| Bundle checked (`refactor-plan`) | architect, again by `post` | `refactor_bundle.py check`: every open issue has a disposition, every new issue passes the issue linter, references, waves and new-number placeholders resolve; then the dry run |
| Posted unchanged (`refactor-plan`) | CTO/CEO | `post --digest` publishes only the bundle the dry run showed; new issues exist and read back before anything is closed |
| Verdict (`build`, `review`, `ship`) | reviewer, not the PR's writer | `Verdict: PASS\|FAIL at <full sha>` from proven findings, against the accepted plan when there is one, with its `## Security` section; a new push needs a new verdict |
| Security and outbound data (`build`, `review`, `ship`) | reviewer | no proven finding the PR brings in; every added or widened outbound path asked for by a linked accepted issue (`issue_gate.py asked`); `pr_loop.py` refuses a PASS that says otherwise or has no security section |
| Audit proofs (`security`) | CTO/CEO | each finding's command reproduces on the audited SHA; nothing changed, filed or published unasked |
| Feedback limit (`build`, `ship`) | reviewer | at most 3 rounds, then pass or `Stopped by reviewer`; `pr_loop.py decide` refuses a fourth |
| Trusted merge (`build`) | CTO/CEO | `pr_loop.py can-merge`: a PASS on the head by an account that can push, not by the writer, naming the reviewer's own commits; an `Accepted by` on a PR approves nothing |
| Unreviewed merge (`quick` only) | CTO/CEO | `pr_loop.py can-merge --unreviewed --head <reported sha>`: open, no judgment or stop by anyone, every linked issue carries `Pipeline: quick` (only quick writes it), not a money path, the given head (the script cannot know what was reported: the sha comes from the builder's report) |
| Self-checked merge (`solo` only) | the one agent, on its own PR | on one head: every commit its own and no verdict or stop on the PR, no money path, the `Done when`, the security-review check with no proven finding and no unasked outbound data, `merge rules: allowed`, required checks green, not behind, no conflict. **Not an independent review**; no verdict |
| Worktree removed (`build`, `quick`, `ship`, `solo`) | whoever made it | `pr_loop.py can-remove` allows it only when nothing is lost (`--handover` for an open PR another agent takes) |
| Safe to run (`test`) | the test runners, and the tester | allowed hosts and programs only; on production a step that changes something runs only with the owner's approval of that step; evidence outside every repository |
| Report checked (`test`) | CTO/CEO | every function has `PASS`, `FAIL` or `NOT RUN` with evidence, and the evidence of each failure shows it |
| Merge | CTO/CEO (`build`, `quick`), reviewer (`ship`) or the one agent (`solo`) | the checked SHA is the head, required checks green (or "no checks"), branch not behind `main`; `gh pr merge --rebase --match-head-commit` |

Issues are written with [`write-issue`](../src/skills/write-issue/SKILL.md) (kinds and the
[catalog](../src/skills/write-issue/references/catalog.md)); plan, decision, verdict, fix and close comments with
[`write-comment`](../src/skills/write-comment/SKILL.md). Each ends with `Created: <agent name>`, and commits are authored
by that name ([identity](../src/skills/github/references/identity.md)).

All templates, and how to change their style: [templates](../src/skills/write-issue/references/templates.md).

## Rules

- A build is one package, one issue, one worktree, one branch, one PR, one owner.
- The CTO/CEO only orchestrates: it does not plan, code, test, deploy or review, and the builder does not merge
  (`solo`, which no bot runs, is the exception). A project that reserves the merge for a person wins.
- Only `build` and `ship` let the reviewer edit, and only to fix its posted findings. `review` never edits; `quick` and
  `solo` have no reviewer.
- `test` and `security` fix no code, open no branch or PR and merge nothing; fixing what they found is a new request.
- Plans and verdicts are comments, not new issues. A plan that creates packages also creates their issues and links them.
  `refactor-plan` is the exception: its plan is the new set of issues.
- "Remove" an issue means close it as not planned with a short comment. Nothing deletes an issue.
- A merge is not done until the issue is closed, the branch deleted and the worktree removed.

## What happened to the old playbooks

The old `playbook-deliver`, `playbook-feature`, `playbook-bugfix`, `playbook-cifix`,
`playbook-docs`, `playbook-rebase`, `playbook-land`, `playbook-changelog`, `playbook-verify`, the old solo pipeline and the
`playbook` dispatcher are removed (today's `playbook-solo` is a new pipeline that shares only the name), and so is the short-lived complete pipeline: its four stages are now `playbook-build`.
`playbook-review` is comment-only. Their useful methods live in the skills they named (`github`, `tdd`, `docs-sync`,
`ci-fixer`, `integrator`, `changelog`, `verifier`, `reviewer`, `delegate`); they are no longer separate CTO pipelines.
