# pm-jlogger

A **project manager** setup around the upstream repo `jlogger` (mode `pm`): you talk to a manager, it runs workflows
(plan, build, review, merge) with one agent per node. Built with:

```bash
swe-cli project create pm-jlogger --mode pm       # AGENTS.md, PROJECT.md, config.yaml, workflows/, skills/, changelog/
swe-cli project pm-jlogger add https://github.com/kimnt93/jlogger     # the upstream clone (a git submodule here)
```

```text
pm-jlogger/
  AGENTS.md        the manager's instructions (open a terminal here: `swe-cli orchestrate pm-jlogger`)
  PROJECT.md       stack, commands, conventions, gotchas; kept under 2000 words by the manager
  project.yaml     the repos: jlogger -> github kimnt93/jlogger
  config.yaml      mode, agents {cli, model, reasoning}, roles; the one file that says who runs what
  workflows/       feature, bugfix, docs, card, ci-fix, conflict, changelog, verify (YAML DAGs)
  skills/learn/    the project's own skill for folding run lessons into PROJECT.md
  changelog/       project.md: every merged PR of every repo
  jlogger/         the upstream repo (git submodule)
```

| Agent | cli | model | reasoning | used for |
|---|---|---|---|---|
| planner | claude | claude-opus-5-5 | high | splitting the goal into cards (the only strong model) |
| developer-junior | claude | claude-haiku-5-5 | high | cards with a clear description (the default) |
| developer-senior | claude | claude-sonnet-5-5 | high | medium or complex cards |
| reviewer-junior | claude | claude-haiku-5-5 | high | the default review: fast check of the PR against its issue |
| reviewer-senior | claude | claude-sonnet-5-5 | medium | deeper review: complex cards, someone else's code |
| documenter | omp | google-antigravity/gemini-3.8-flash | medium | docs |
| manager, scribe, ci-fixer, integrator, verifier | claude | sonnet / haiku | medium | the rest |

Rebuild it: `bash examples/pm-jlogger/setup.sh ~/Documents/me`. Run a workflow:

```bash
cd ~/Documents/me/pm-jlogger
swe-cli flow run pm-jlogger feature --goal "In jlogger add a .version file containing 0.1.0 (the pyproject version)"
swe-cli flow status pm-jlogger
```

Plan -> one card: build (own worktree, opens the PR) -> checks -> review (reviewer-junior) -> report: the PR is ready.
jlogger has no CI, so no check can vouch for a PR: the gate merges it only on your approval (`swe-cli flow merge --approved`), after the reviewer's PASS. The same holds for gorouter, whose only workflow runs on releases.
