# Runbooks

The steps that need you: your logins, your machine, your approval. Each ends with a command whose output proves it
worked.

| # | Runbook | You must |
|---|---|---|
| 1 | [Fill the agent table](#1-fill-the-agent-table) | choose harness, model and effort for each row |
| 2 | [Install or remove the plugin locally](#2-install-or-remove-the-plugin-locally) | restart open sessions |
| 3 | [Publish the plugin to teammates](#3-publish-the-plugin-to-teammates) | create the publish remote |

## 1. Fill the agent table

### Goal

The CTO/CEO holds one filled table, the only place that sets which harness, model and reasoning effort an agent runs
on. Do this before the first agent starts, and again when a model ships or is retired.

### Steps

1. `make cli`, then `swe-cli agents init`. It copies the empty
   [template](../src/skills/bot-orchestration/assets/agent-table.template.md) to `~/.config/swe/agent-table.md` and
   never overwrites. To keep it elsewhere, name it in `$AGENT_TABLE` or in the `agent_table` key of `config.json`
   ([cli/README.md](../cli/README.md#configuration)). Keep it outside any public repository.
2. Log in to each harness the table names (interactive, once each), and `gh auth login`.
3. Fill the rows `simple`, `medium`, `hard` and `planner/architect`: the Orca agent id, the model id that harness takes
   and the reasoning effort (`none` when you set none). `orca orchestration worker-start --help` says what it accepts.
   Rows may name the same harness and model.
4. To change a model later, edit the row. Nothing else sets a model. Before you change it for real work, compare old and
   new on past tasks with the router's [`eval`](skills/router.md#eval) method.

### Verify

```bash
swe-cli agents check          # every row is there and filled
swe-cli agents row medium     # what a medium brief runs on
swe-cli doctor                # git, gh, Orca, the harness CLIs and the table
```

## 2. Install or remove the plugin locally

### Goal

The plugin is installed in your harnesses: `/swe` works in Claude Code, Codex and omp.

### Steps

1. Check for an older plugin that uses the same marketplace or skill names: `claude plugin list`, `omp plugin list`.
   Remove it from its own repository.
2. `make claude codex omp` (or `make install` for every harness detected on the machine).
3. In a fresh session in any git repository: `/swe` prints the grouped skill table (Claude Code), `/skill:swe` (omp).
4. The install also puts the command `swe-build-slot` in `~/.local/bin` (`make install BIN_DIR=<dir>` elsewhere). If it
   warns that the directory is not on PATH, add it with the line it prints; it edits no shell profile. On Windows
   without make: `py scripts\build.py`, then `py dist\swe\scripts\install.py install --bin-only` (a
   `swe-build-slot.cmd` launcher in `%USERPROFILE%\.local\bin`).

### Verify

```bash
make status
claude plugin list | grep swe@swe-skills
cd / && swe-build-slot --status    # the command, from any directory
```

### Undo

`make claude codex omp REMOVE=1`

### Notes

Claude Code, Codex and omp read the plugin from `dist/swe`: a `make build` updates them in place (start a new session to
see it), and a `make clean` breaks them until the next `make claude codex omp`.

## 3. Publish the plugin to teammates

### Goal

Teammates install the plugin without this source repository.

### What exists

`scripts/publish.sh` (`make publish`, `PUSH=1` to push): builds, validates, requires a `CHANGELOG.md` entry for the
version, syncs `dist/<name>/` into a publish repository (`PUBLISH_DIR`, default `~/src/<name>-plugin`), commits
`release: <name> <version>` and tags `v<version>`. It refuses a dirty publish repository and a changed release under an
existing tag.

### Steps

1. Decide visibility: the domain skills describe conventions of your own, so a private repository is the safe default.
2. Create the remote (for example `gh repo create <owner>/<name>-plugin --private`) and add it:
   `git -C ~/src/<name>-plugin remote add origin <url>`.
3. Bump `PLUGIN_VERSION` in `plugin.env`, add the `CHANGELOG.md` entry, then `make publish PUSH=1`.
4. Teammates: `claude plugin marketplace add <owner>/<name>-plugin` and `claude plugin install <name>@<name>-skills`.
   Each fills their own agent table (runbook 1).

### Verify

```bash
PUBLISH_DIR=$(mktemp -d) bash scripts/publish.sh    # after step 3's entry: a release commit and its tag
```

Without a `## <version>` heading in `CHANGELOG.md` for `PLUGIN_VERSION`, it stops and says so.
