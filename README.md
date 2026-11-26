# swe-skills

A software-engineering plugin for coding agents. One entry command (`/swe`) picks the language for the job, routes the task to
tested skills and engineering principles, and does not finish until the project's `make verify` passes. Eight **playbooks**
(`/swe:playbook-<name>`) cover the path from a problem or a pull request to its end, testing running software and
auditing its security, run by a team of bots in **Orca**.

## The stack

| Layer | What it is |
|---|---|
| **Orca** | where every agent runs: workspaces, one git worktree per task, and orchestration (who started whom, messages, waiting) |
| **Orca bots** | standing role holders (CTO/CEO, architect, developer, tester, devops, reviewer) that orchestrate: they hand each task to an agent or another bot |
| **Harnesses** | the coding CLIs that Orca runs agents in; the plugin installs into each (`make harness` lists them) |

Which harness, model and reasoning effort an agent runs on comes from one place, the team's
[agent table](#the-agent-table).

| The job | Language |
|---|---|
| HTTP APIs, services, Kafka consumers | **Go**, Fiber v3 (default) |
| ML, data pipelines (Pathway, Dagster) | **Python** |
| hot paths, Rust cores for Python | **Rust** |
| web apps and dashboards | **Next.js**, or **Vite + React + TypeScript** |

The full stack is in [STACK.md](STACK.md).

## Quick Install

Install across all detected AI agent harnesses with one command:

```bash
curl -fsSL https://raw.githubusercontent.com/kimnt93/swe-skills/main/install.sh | bash
```

Or install from local source:

```bash
git clone https://github.com/kimnt93/swe-skills.git && cd swe-skills
./install.sh
# or via Makefile
make install
make cli
```

## Use

### 1. Playbooks (`/swe:playbook-<name>`)

Exactly eight. A request that names one follows it; with none named, the CTO/CEO uses **`build`**. Every one that
builds ends with the merge.

| You have | Playbook | What happens | Ends |
|---|---|---|---|
| work to build (**the default**) | [`build`](src/skills/playbook-build/SKILL.md) ([example](src/skills/playbook-build/references/example.md)) | CTO/CEO card → the architect plans it carefully → the CTO/CEO checks the plan against the card and accepts → the developer, tester or devops opens a PR each → a **reviewer** checks it against the plan and fixes, at most 3 rounds → the CTO/CEO trusts the PASS | merged or stopped |
| a request that names `quick` | [`quick`](src/skills/playbook-quick/SKILL.md) ([example](src/skills/playbook-quick/references/example.md)) | CTO/CEO issues, no plan → one worktree and PR each → the CTO/CEO merges on mechanical conditions only: **no check** of the code | merged or stopped |
| a problem you want only planned | [`plan`](src/skills/playbook-plan/SKILL.md) ([example](src/skills/playbook-plan/references/example.md)) | CTO/CEO card → architect comments the plan → back to the CTO/CEO | at the accepted plan; nothing built |
| a refactoring you want planned as issues | [`refactor-plan`](src/skills/playbook-refactor-plan/SKILL.md) ([example](src/skills/playbook-refactor-plan/references/example.md)) | the architect reads every repository and open issue and writes the new issues → the CTO/CEO posts them unchanged: new ones first, then the replaced ones closed as not planned | at the posted issues; no code, nothing deleted |
| a PR you want judged | [`review`](src/skills/playbook-review/SKILL.md) | read it, run it when safe, post one `PASS` or `FAIL` comment | at the comment; nothing changed |
| a PR you want on `main` | [`ship`](src/skills/playbook-ship/SKILL.md) ([example](src/skills/playbook-ship/references/example.md)) | one reviewer reviews, fixes and re-reviews, at most 3 rounds, then merges | merged and issue closed, or stopped |
| software you want tested | [`test`](src/skills/playbook-test/SKILL.md) ([example](src/skills/playbook-test/references/example.md)) | the tester writes the expected results, uses it as its user does (a real browser with screenshots and a video of every click; real inputs for an API or CLI) and runs each failure again | at a short report: pass or fail per function, evidence, bugs ready to file; no code fixed |
| code you want audited for security | [`security`](src/skills/playbook-security/SKILL.md) ([example](src/skills/playbook-security/references/example.md)) | the reviewer's agent scans a PR or a repository, lists every path data leaves by and proves each finding locally | at a report: proven findings and issues ready to file; no code changed, nothing merged |

```text
/swe:playbook-build limit requests per API key
/swe:playbook-quick users misread order times; fix it
/swe:playbook-plan users cannot export the orders they filtered; plan it
/swe:playbook-refactor-plan plan the refactor of the order code in orders-api and orders-web
/swe:playbook-review review PR 54
/swe:playbook-ship ship PR 54
/swe:playbook-test test that a customer can sign in and get a price on staging
/swe:playbook-security audit the orders service for leaks and vulnerabilities
```

**Every reviewed pull request gets a security check** besides the check that it is correct
([security-review](src/skills/security-review/SKILL.md)). One that adds or widens a way data leaves (a call, telemetry,
an SDK, an upload, a CI or install step) **fails unless its accepted issue asks for that destination and data**; a
proven security finding blocks the merge; and a `PASS` without the verdict's security section is refused. A scanner
lists what to look at first. It is an aid: a clean scan is never a pass. `quick` has no check, so it has none of this.

**By default you approve and review no code.** The weight is on the plan: the architect plans carefully, the CTO/CEO
checks it against the card, and the reviewer checks the code against the accepted plan. The CEO or CTO only
orchestrates: it writes the issues and runs the playbook, and never plans, codes, tests, deploys or reviews code itself.
In `build` and `ship`, nobody else checks the reviewer's own fixes before `main`. The final `PASS` names those commits,
and a `risk:money-path` pull request is never auto-merged ([fix loop](src/skills/reviewer/references/fix-loop.md)).
`quick`, which runs only when you name it, has no check at all: the issue's `Done when` and the required checks are all
there is.

### Bots and agents

A **bot** is a standing member; an **agent** is one run of a harness that a bot starts for one job. The bot orchestrates:

```text
CEO bot ─ issue ─► developer bot ─ brief ─► agent (one issue, own worktree)
   ▲                  │    ▲                  │
   └──── status ──────┘    └──── report ──────┘        agents never message each other
```

Bots delegate with a handoff and report back with a status. The developer bot takes the agent table's row for the
issue, checks the agent's work and its pull request, and reports. Replies and status reports are short. Rules, message
templates and a linter: [bot-orchestration](src/skills/bot-orchestration/SKILL.md).

### The agent table

The CTO/CEO holds one table with the rows `simple`, `medium`, `hard` and `planner/architect`, each with a harness, a
model and a reasoning effort. This repository ships only the empty
[template](src/skills/bot-orchestration/assets/agent-table.template.md); each team fills its own copy outside any public
repository. It is the only place that sets harness, model and effort: every brief and handoff takes them from it. Rows
may be the same. **There is no default**: a missing table, row or cell stops the run and asks.

```bash
swe-cli agents init               # copy the empty template to ~/.config/swe/agent-table.md; never overwrites
swe-cli agents check              # every row is there and filled
swe-cli agents row medium         # what a medium brief runs on
```

`$AGENT_TABLE`, or the `agent_table` key of `config.json`, names a table kept somewhere else
([cli/README.md](cli/README.md#configuration)).

### Merge rules: only approved work

Nothing is built or merged unless the pull request links an issue of the same repository and **every linked issue is
approved**. As shipped (`"approvals": ["trusted_author", "owner_comment"]` in
[merge-rules.json](src/skills/github/assets/merge-rules.json)), **an issue opened by an account with write access needs
no approval**: its role on the repository is `admin`, `maintain` or `write`, so the issues your team and its agents open
go ahead without you. A `MEMBER` or `COLLABORATOR` with only read or triage access is not enough, and a failed lookup
approves nothing. Only such an issue, or an outsider's, waits for your comment
([template](src/skills/github/assets/owner-acceptance.template.md)); for that issue, from your own account, in any shell:
`gh issue comment <number> -R <owner>/<repo> --body "Accepted by owner."`. An issue the owner's account created
(`owner_author`) and a project board status of `Todo` or `In Progress` (`board_status`) approve nothing by themselves:
they are off while agents share the owner's account. A missing, empty or unknown `approvals` value refuses everything.

```text
Accepted by owner.

Notes: none
```

An issue that is closed (done, not planned or duplicate), labelled `duplicate` or `wontfix`, or marked `Done`,
`Not planned`, `Duplicate` or `Canceled` on a board is refused whatever else says yes. Agents often share the owner's
account, so text signed by an agent never counts as the owner's. The check uses your `gh` login as it is. If GitHub
answers that the login lacks the scope for project boards, it goes on without the board and says so: a board status then
does not refuse ([what is not checked](src/skills/github/references/pull-requests.md#merge-rules)). Any
other failure to read the board refuses.

```bash
python3 src/skills/github/scripts/issue_gate.py issue <number> --repo <owner>/<repo>   # may it be built?
python3 src/skills/github/scripts/issue_gate.py pr <number> --repo <owner>/<repo>      # may it be merged?
```

These checks are run by the agents; GitHub does not enforce them. Full rules:
[merge rules](src/skills/github/references/pull-requests.md#merge-rules); the names are in
[merge-rules.json](src/skills/github/assets/merge-rules.json).

### One style for issues, comments, commits and pull requests

- Issues are written with [`write-issue`](src/skills/write-issue/SKILL.md), comments with
  [`write-comment`](src/skills/write-comment/SKILL.md), pull requests from one template.
- Every commit is authored by the agent's name, and every issue, comment and PR body ends with `Created: <agent name>`
  ([identity](src/skills/github/references/identity.md)). Merges are by rebase, so the name stays on `main`.
- The linters read the Markdown templates: edit a file to change the style
  ([the list and how](src/skills/write-issue/references/templates.md)).

### 2. One task, one worker (`/swe:delegate`)

`/swe:delegate` writes a brief that stands alone, starts one Orca worker on a row of the agent table, and reads its diff
and runs the check before anything lands ([delegate](src/skills/delegate/SKILL.md)):

```text
/swe:delegate add pagination to the orders table
/swe:delegate fix the race in cache eviction
```

### 3. CLI (`swe-cli`)

```bash
swe-cli update        # pull the latest code, rebuild the plugin, reinstall it into harnesses
swe-cli playbooks     # list the eight playbooks and their slash commands
swe-cli agents        # check the team's agent table (also: path, row <row>, init)
swe-cli delegate      # start one Orca worker for a brief, on a row of the agent table
swe-cli config show   # show config.json
swe-cli doctor        # check git, gh, Orca, the harness CLIs and the agent table
```

All commands and `config.json`: [cli/README.md](cli/README.md). `make cli` links the command.

## Documentation

| Read | When |
|---|---|
| [docs/getting-started.md](docs/getting-started.md) | install, first task, troubleshooting |
| [docs/usage.md](docs/usage.md) | what to say for each kind of task |
| [docs/playbooks.md](docs/playbooks.md) | the eight playbooks, their gates and rules |
| [docs/skills/](docs/skills/README.md) | each skill in detail |
| [docs/harnesses.md](docs/harnesses.md) | every supported harness and how it installs |
| [docs/runbooks.md](docs/runbooks.md) | the steps that need you: agent table, local install, publish |
| [docs/development.md](docs/development.md) | make targets, build settings, layout, enforced rules |
| [cli/README.md](cli/README.md) | every `swe-cli` command |
