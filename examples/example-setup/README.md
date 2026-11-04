# example-setup

What `swe-cli project create example-setup` + `swe-cli project example-setup add <jlogger url>` leave on disk, with the
notes and agents filled in. The upstream `jlogger/` is tracked here as a git submodule (`git clone --recurse-submodules`, or `git submodule update --init`); `project add` makes the same clone.

```text
example-setup/
  AGENTS.md        the manager's instructions (open a terminal here and run `swe-cli orchestrate example-setup`)
  PROJECT.md       stack, commands, conventions, gotchas; the manager keeps it under 2000 words
  project.yaml     the repos: jlogger -> github kimnt93/jlogger
  models.yaml      agents {cli, model, reasoning}: claude plans and builds, omp reviews
  roles.yaml       which agent and skills each workflow role uses
  workflows/       feature, bugfix, docs, card, ci-fix, conflict, changelog, verify (YAML DAGs)
  skills/learn/    the project's own skill for folding run lessons into PROJECT.md
  changelog/       project.md: every merged PR of every repo
  jlogger/         the upstream repo (git submodule; `project add` makes the same clone)
```

Rebuild it: `bash examples/example-setup/setup.sh ~/Documents/me`.

## Run a workflow

```bash
cd ~/Documents/me/example-setup
swe-cli flow graph feature example-setup
swe-cli flow run example-setup feature --goal "In jlogger add a .version file containing 0.1.0"
swe-cli flow status example-setup
```

Plan (claude opus) -> one card: build (claude sonnet, own worktree, opens the PR) -> checks -> review (omp, another
family) -> report. The report lists the PR as ready. Merging waits for you (`swe-cli flow merge`), and jlogger has no
required check yet, so the gate would refuse it.
