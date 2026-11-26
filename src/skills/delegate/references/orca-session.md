# The Orca worker

Load the Orca `/orchestration` skill first; the installed guide and `ORCA <command> --help` win over this page.

## The executable

`ORCA` is the executable that skill resolves to: `$ORCA_CLI_COMMAND` when set, else `orca-ide` (`orca-dev` in an Orca
development checkout), and a bare `orca` **only inside an Orca terminal**. On Linux a bare `orca` elsewhere is the
GNOME screen reader. `delegate.py` follows the same rule and stops when it finds none.

## Start

```bash
python3 <this skill's folder>/../bot-orchestration/scripts/agent_table.py row medium     # harness, model, effort
ORCA orchestration worker-start --spec-file brief.md --agent <harness> --model <model> --effort <effort> \
    --worktree new-child --repo <repo> --name <id-lowercase> --json
```

`delegate.py` runs exactly the second command. The three values are the row's cells; drop `--effort` only when the
cell says `none`. `ORCA orchestration worker-start --help` says which harness ids Orca knows and which take a model or
an effort. When Orca cannot give a worker its row's values, report `BLOCKED`; do not start it on others.

## While it works

```bash
ORCA orchestration worker-list                                      # state of your workers
ORCA orchestration send --to dispatch:<dispatch_id> --subject "<what changes>" --body-file steer.md
ORCA orchestration reply --id <msg_id> --body-file answer.md        # answer its question
```

## After it reports

Check the diff and run the check in its worktree (`ORCA worktree ps` shows the path). Then:

```bash
ORCA orchestration worker-release --dispatch <dispatch_id>          # closes its terminal, not its worktree
ORCA worktree rm --worktree path:<path>                             # only when nothing in it is left to land
```

Before removing a worktree, make sure its work is committed and pushed, or already landed:
`git -C <path> status --short` and `git -C <path> log --oneline @{upstream}..HEAD` print nothing. Never force it.
