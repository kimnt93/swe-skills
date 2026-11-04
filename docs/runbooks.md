# Runbooks

Operations that need you: your real repo, your logins, your approval. Everything the agents could build is
built and tested; these are the steps that use it. Do them in order 1 → 3; 4 to 6 any time. Each ends with
commands whose output proves it worked.

| # | Runbook | You must |
|---|---|---|
| 1 | [Give one real service proof](#1-give-one-real-service-proof) | pick the service; make the CI check required |
| 2 | [Bring the fleet live](#2-bring-the-fleet-live-on-that-service) | log in to the providers; restart the gateway; merge the first PRs |
| 3 | [Turn on autopilot](#3-turn-on-autopilot) | flip the switch after 20 clean merges; sample weekly |
| 4 | [A new model ships](#4-a-new-model-ships) | approve a change of the managers' model |
| 5 | [Publish to teammates](#5-publish-the-plugin-to-teammates) | create the publish remote |
| 6 | [Install or remove locally](#6-install-or-remove-the-plugin-locally) | restart open sessions |

## 1. Give one real service proof

### Goal

One real service has hands and eyes: `make verify` runs its static gates **and** a live probe, CI
requires it, and it provably fails on real bugs. Nothing is parallelised on the board before this
holds for the repo the board works on.

### Steps

1. Ask the human for the pilot service (a Go or Python API). Work on a branch in a worktree.
2. In that repo run `/swe:verify-create`. It generates `.agents/skills/verify-<service>/` with a
   feature map of the top 3–5 features, copies `verify.mk`, and vendors the check scripts into
   `tools/skills/`. In the Makefile: `include verify.mk`; set `RUN`, `E2E` and `SERVICE`.
3. `make verify` passes on the clean branch.
4. **Verify the verifier.** On three throwaway branches seed one bug each: a logic bug a test
   should catch; a contract break (`/healthz` body or port); a bad migration (`CREATE INDEX` without
   `CONCURRENTLY` on an existing table). `make verify` must fail on each, for the right reason.
5. Add the `verify` job from the `deployment-setup` workflow template. **Human:** make
   `Validate / verify` a required check on the default branch.
6. For money-path services, add a replay (`/swe:replay-test`): a recorded stream, a replay
   entrypoint, a golden file, and the duplicate and redelivery checks in `make verify`.
7. Open the PR with the `opening-a-pr` playbook.

### Verify

```bash
make verify; echo "exit=$?"                         # 0 on the clean branch, non-zero on each seeded bug
gh api repos/<owner>/<repo>/branches/main/protection --jq '.required_status_checks.contexts'
```

## 2. Bring the fleet live on that service

### Goal

The project's orchestrator runs real cards on the pilot repo: card → delegated session in a worktree → `make verify` →
PR → optional cross-family review → human merge. One card, then 3, then about 10 in parallel.

### Steps

1. `bash cli/tests/selftest.sh` passes (add `--hermes` only if you use Hermes). `make cli`.
2. **Human logins** (interactive), once each: `claude auth login`, `codex login`, `omp login openai-codex`, `gh auth login`
   (whichever CLIs you use). Only with Hermes enabled: on the Hermes **default** profile `hermes auth add gemini`
   (a non-Claude provider: Claude cannot be the Hermes orchestrator); `/sync` (or `swe-cli sync`) shares the keys
   ([context-and-sync.md](context-and-sync.md)).
3. Pick exact ids with `omp models ls`; edit `cli/models.yaml` (`orchestrator`, `launcher`, `workers`); then
   `swe-cli models check` reports only logins.
4. `swe-cli bootstrap` (projects, model roles, context limits; with Hermes also root, managers, board settings).
5. **Add the pilot project:** `swe-cli project add <name> --dir ~/work/<name> --repo <repo>=<owner>/<repo> --description "..."`
   (it creates the directory and clones the repo; with Hermes also the manager `pm-<name>` and the board), then
   `swe-cli models check` = 0 problems. Start the orchestrator with `swe-cli orchestrate <name>` and ask it to adopt the
   repo (the `project` skill: `setup_repo.sh`, templates, `ARCHITECTURE.md`).
6. **One card:** `swe-cli doctor <name>` is clean, then a small `risk: low`, `tier: mid` card started by the orchestrator
   (issue first, then `swe-cli delegate start`; see [delegation.md](delegation.md)). Watch with
   `tmux attach -t <name>-<card>` (or the Orca terminal) and `swe-cli delegate status <name>`. Check the PR, `make verify`, and the
   cross-family review (`swe-cli delegate review`) and its verdict SHA. **Human** merges.
7. Fix whatever broke, with a test in `cli/tests/selftest.sh`, before the next step.
8. Three independent cards with disjoint files, across two CLIs, then about five; then one rough goal given to the orchestrator and split by it.

### Verify

```bash
swe-cli models check                                   # 0 problem(s)
hermes kanban diagnostics --board <name>            # no errors, nothing stranded
swe-cli delegate status <name>                         # every card: state, outcome, behind main
gh pr list --state merged --repo <owner>/<repo>       # merged PRs
```

### Done when

20 cards merged with 0 reverts, and at least one review returned `request_changes` with a proven
finding that was then fixed.

## 3. Turn on autopilot

### Goal

Low-risk cards merge without a human click; the human samples afterwards. Everything is built: this
is a configuration change plus a sampling habit.

### What exists

- `swe-cli merge <pr> --risk <r> --sha <sha>`: merges only an allowed risk class, at the reviewer's
  verified SHA, with every required check passed; never money-path; never a PR without required
  checks. The manager calls it after a clean verdict, or with `--approved` when you say merge. It also refuses a branch that is behind or in conflict with `main`.
- `autopilot.auto_merge` in `cli/models.yaml`, empty by default.

### Steps

1. Gate: runbook 2 is done (20 clean merges). If not, stop.
2. Pin model ids in `cli/models.yaml` (replace the `opus` / `sonnet` / `haiku` aliases with full
   ids) so no model changes during an autopilot run. `swe-cli models check && swe-cli models apply`.
3. **Human:** set `autopilot.auto_merge: [low]`.
4. Add the sampling jobs with `hermes cron`: weekly, list the week's auto-merged PRs for the human to
   read; daily, a triage card for every red CI run on main.
5. After two weeks with no blocking defect in the samples, ask the human about `[low, standard]`.

### Verify

```bash
bash cli/tests/selftest.sh          # the merge guard cases
swe-cli models show | tail -1           # autopilot auto_merge: ['low']
hermes cron list
```

## 4. A new model ships

### When

A new model ships (say Opus 6), a model is retired, or a CLI's cost or quality changes.

### Steps

1. `claude update`: the `claude` workers' `opus` / `sonnet` / `haiku` aliases now mean the newest
   models, unless `cli/models.yaml` pins full ids.
2. Edit `cli/models.yaml` where needed: pinned worker ids, the omp workers, the board
   brains, `omp_roles`, the subagents' tiers.
3. `swe-cli models check`: 0 problems (each id exists where it runs, each provider is logged in).
4. `swe-cli models apply`, then `swe-cli models show`.
5. `make claude omp hermes`, so the plugin's subagents get the new models.
6. For a change to the managers' model (`board.manager`), run the router's `eval` playbook first: 10 past goals
   through the old and the new model, card graphs scored blind. Switch only if the new one is not
   worse. **Human** approves.
7. Clear per-card overrides that pin the old model: `hermes kanban set-model <id> none`.
8. Commit `chore(fleet): <model> for <agents>` with the `show` output in the body.

Skills never change in an upgrade: they name tiers, not models.

## 5. Publish the plugin to teammates

### Goal

Teammates install the plugin without this source repo.

### What exists

`scripts/publish.sh` (`make publish`, `PUSH=1` to push): builds, validates, requires a
`CHANGELOG.md` entry for the version, syncs `dist/<name>/` into a publish repo
(`PUBLISH_DIR`, default `~/src/<name>-plugin`), commits `release: <name> <version>` and tags
`v<version>`. It refuses a dirty publish repo and a changed release under an existing tag.

### Human steps

1. Decide visibility: the domain skills describe internal conventions, so a private repo is the
   safe default.
2. Create the remote (for example `gh repo create <owner>/<name>-plugin --private`) and add it:
   `git -C ~/src/<name>-plugin remote add origin <url>`.
3. Bump `PLUGIN_VERSION` in `plugin.env`, add the `CHANGELOG.md` entry, then `make publish PUSH=1`.
4. Teammates: `claude plugin marketplace add <owner>/<name>-plugin` and
   `claude plugin install <name>@<name>-skills`.

### Verify

```bash
PUBLISH_DIR=$(mktemp -d) bash scripts/publish.sh    # release + tag; a second run says "no change"
```

## 6. Install or remove the plugin locally

### Goal

The plugin is installed for the owner: `/swe` works in Claude Code and omp, and the skills are in
Hermes.

### Steps

1. Check for an older plugin that uses the same marketplace or skill names:
   `claude plugin list`, `omp plugin list`, `ls ~/.hermes/skills`. Remove it from its own repo.
2. `make claude omp hermes`.
3. In a fresh session in any git repo: `/swe` prints the grouped skill table (Claude Code),
   `/skill:swe` (omp), `hermes skills list | grep swe` (Hermes).

### Verify

```bash
make status
claude plugin list | grep swe@swe-skills
(cd /tmp && claude -p --model haiku "/swe" | grep -c '/swe:')    # > 10
```

### Undo

`make claude codex omp hermes REMOVE=1`

### Notes

Claude Code, Codex and omp read the plugin from `dist/swe`: a `make build` updates them in place
(start a new session to see it), and a `make clean` breaks them until the next `make claude codex omp`.
