# swe-cli (`<plugin>-cli`)

The plugin's command. It updates the plugin, checks the machine and the team's agent table, and starts one Orca worker
for a brief. `make cli` links it into `~/.local/bin`.

## Commands

```bash
swe-cli update [harness...] [--no-pull] [--dry-run]
                                      # pull the latest code, rebuild the plugin, reinstall it into harnesses
swe-cli playbooks                     # list the playbooks and their slash commands
swe-cli agents [check]                # every row of the team's agent table is there and filled
swe-cli agents path                   # where the team's table is looked for
swe-cli agents row <row>              # simple | medium | hard | planner/architect
swe-cli agents init [file]            # copy the empty template; never overwrites
swe-cli delegate --brief <file> [--row <row>] [--repo <repo>] [--name <name>] [--worktree <where>] [--dry-run]
                                      # start one Orca worker for a brief, on a row of the agent table
swe-cli config [show|path|init]       # show config.json, print its path, or create it (never overwrites)
swe-cli doctor                        # check git, gh, python3, Orca, the harness CLIs and the agent table
swe-cli changelog show                # print CHANGELOG.md
swe-cli changelog check <pr>          # does CHANGELOG.md mention the pull request?
swe-cli name                          # print the plugin name (default: swe)
```

## Configuration

Two files, both the user's own:

| File | What it holds |
|---|---|
| the **agent table** | harness, model and reasoning effort per row: the only place that sets them |
| `config.json` | where the agent table is, when it is not in the default place |

`config.json` is `$SWE_CONFIG`, else `~/.config/swe/config.json` (`$XDG_CONFIG_HOME` is honoured). Nothing is read from
the working directory.

```json
{
  "agent_table": ""
}
```

The agent table is, first match: `--table`, `$AGENT_TABLE`, the `agent_table` key of `config.json`, then
`agent-table.md` beside the default `config.json`. A named file that does not exist stops the search. There is no
default agent: a missing table, row or cell stops with a message to ask the owner.

## Delegation

`swe-cli delegate` (the script of the [`delegate`](../src/skills/delegate/SKILL.md) skill) reads the row named by
`--row` or by the brief's `Row:` line and runs `orca orchestration worker-start` with that row's harness, model and
reasoning effort. It has no option that chooses any of them. Run it with `--dry-run` first: it prints the command and
starts nothing. It checks nothing for you afterwards: read the diff and run the check before anything lands.
