# Usage

How to work with the plugin day to day. The stack runs in Orca, and every agent runs on a row of your team's
[agent table](playbooks.md#bots-and-agents). Examples use the default name `swe`; in oh-my-pi write `/skill:swe` for
`/swe` and `/skill:<skill>` for `/swe:<skill>`.

## The one habit: start with the router

```text
/swe <what you want, in your words>
```

The router (1) restates your goal and a **done-predicate** (a command and its expected output),
(2) picks the language, (3) picks a playbook, (4) loads the domain skill and the principles that apply,
(5) delegates to agents on rows of the agent table, and (6) finishes only when `make verify` exits 0 on the committed head, with its
tail in the reply. Called with no request, `/swe` prints the skill table.

### Which language it picks

| The job | Language |
|---|---|
| HTTP APIs, services, Kafka consumers, workers | Go with Fiber v3 (default) |
| ML: training, evaluation, inference, data pipelines | Python (polars, numpy) |
| hot paths, Rust cores for Python, low-latency services | Rust |
| server-rendered web apps | Next.js (App Router) |
| dashboards, internal tools | Vite + React + TypeScript |

## What to say for common tasks

| You say | Playbook the router runs | You get |
|---|---|---|
| `/swe how does the fill consumer work?` | investigation (`how`) | an explanation with `file:line` evidence, no PR |
| `/swe why do we retry three times in the order client?` | investigation (`why`) | the commits, PRs and incidents behind it |
| `/swe fix: cancelled orders still show as open` | bug-fix + `tdd` | a failing test, the root-cause fix, `make verify` |
| `/swe add a cancel-order endpoint and a Cancel button` | feature (`architect` first) | types and a sketch, then code in small commits, then proof |
| `/swe split the orders package, no behaviour change` | refactoring | characterization tests first, then small steps |
| `/swe add a nullable column to orders` | migration + `db-migrations` | expand → migrate → contract, tried up and down on PostgreSQL |
| `/swe the order list endpoint is slow` | perf-issue + profiling | a baseline, the limiter, the fix, a vetted before → after |
| `/swe get p95 under 20 ms` | hillclimb | one change per measurement, one commit per kept win |
| `/swe errors spiking on fills since the deploy` | incident | timeline from Sentry, logs, traces, then a repro |
| `/swe train a model for next-hour volume` | feature with `py-code` ML | time-ordered splits, a model card, an evaluation vs baseline |
| `/swe get PR 42 green` | babysit | conflicts, review threads, CI, stopping at merge-ready |

Skills you can call directly (no router): `/swe:interrogate review this branch`,
`/swe:architect design the position snapshot API`, `/swe:blast-radius`,
`/swe:deslop`, `/swe:ketchup` (catch me up), `/swe:reflect` (capture what this task taught),
`/swe:correct` (stop a repeated mistake). Everything is listed in [skills.md](skills.md), and each skill is explained step by step in [skills/](skills/README.md).

## Give a project proof

"Done" means `make verify` passes. A project without it:

```text
/swe:verify-create        # writes the verify lever, a project-local verify skill and a feature map
/swe:verify-maintain      # later, after features change: keeps them true
```

Then seed one bug and confirm `make verify` fails; make the CI `verify` job a required check.
For orders, fills, positions, balances, risk and P&L also use `/swe:replay-test` (replay a recorded
day, then with duplicated and redelivered events) and, for state machines and races,
`/swe:formal-verify`.

## Playbooks: from a problem or a pull request to its end

| You have | Say | You get |
|---|---|---|
| work to build (the default, also with no playbook named) | `/swe:playbook-build <problem or plan>` | an accepted plan, then pull requests a separate reviewer checked against it, fixed and passed, then merged |
| a request for quick, by name | `/swe:playbook-quick <problem>` | no plan and no check: pull requests merged when the merge rules, the required checks and the reported head allow it |
| a problem you want only planned | `/swe:playbook-plan <problem>` | an accepted plan on the issue; nothing built |
| a refactoring you want planned as issues | `/swe:playbook-refactor-plan <request, with the repositories>` | new issues written by the architect and posted unchanged; the ones they replace closed as not planned; nothing built |
| a pull request to judge | `/swe:playbook-review review PR <n>` | one verdict comment; nothing changed |
| a pull request to land | `/swe:playbook-ship ship PR <n>` | merged with its issue closed, or stopped with the reasons |
| software to test | `/swe:playbook-test <what a user does, the target and its environment>` | pass or fail per function, evidence, bugs ready to file; no code fixed |
| code to audit for security | `/swe:playbook-security <a PR, or a repository>` | proven findings, every path data leaves by, issues ready to file; nothing changed or merged |

A review loop has at most 3 rounds. After that the pull request passes or is stopped: it stays open with its branch, and
you decide what happens. Details and gates: [playbooks.md](playbooks.md).

## What waits for you

- **Questions only where the [rule for asking](../src/skills/principles/references/never-block-on-the-human.md) says
  so** (money, anything irreversible, production, publishing, access only you can give, and the rest of its list), in
  one short batch with a recommendation each. Other choices are taken and recorded with their reason. No reply is never
  approval.
- **No other step, by default.** An issue an account with write access opened (role admin, maintain or write; your
  agents included) is approved as it is, and you review no code: the reviewer checks it against the plan the CTO/CEO
  accepted.
- **An outsider's issue.** The merge rules refuse it as not approved until you accept it. For that issue alone, in any
  shell: `gh issue comment <number> -R <owner>/<repo> --body "Accepted by owner."`, or the full text:

  ```text
  Accepted by owner.

  Notes: none
  ```

- **A money path.** A pull request labelled `risk:money-path` is never auto-merged.
- **A stopped pull request**, and any pull request from a fork or an outside contributor.
- **A pull request `quick` stopped**: it stays open. Ask for `ship` to land it, or `review` for a comment.

## Git and GitHub, the one way

Every agent follows the `github` skill: approved issue → branch `<id>/<slug>` or `<type>/<issue>-<slug>` → Conventional
Commits under the agent's own name → a pull request from the one template, with `Closes #N` → `pr_lint.py` → checks
green → the playbook's judgment of one commit → rebase merge → issue closed. Every issue, comment and pull request body
ends with `Created: <agent name>`. Say `/swe:github open the PR for this branch` and it writes the body, lints it, opens
it and checks the result. A good pull request is one outcome, at most about 400 changed lines (more needs `size:large`
and a reason), only the files the issue owns, and the project's `ARCHITECTURE.md` respected.

## Reading what the agent says back

- Claims carry their evidence or a label: *measured*, *inferred*, *guess*.
- The reply ends with the `make verify` tail and what could not be checked.
- A skipped live check is a failure to report, not a footnote.
- If a reply has neither, ask: "what did you run, and what did it print?"
