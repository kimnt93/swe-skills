# Example run

The owner asks the CTO bot for one rule for filtering orders across two repositories. The names are examples.

| # | From → to | What happens | Message |
|---|---|---|---|
| 1 | CTO bot → architect bot | passes the request and both repositories on; ends its turn | [handoff](../assets/example/architect-brief.md) |
| 2 | architect bot → its agent | briefs an agent on the `planner/architect` row | [agent brief](../assets/example/agent-brief.md) |
| 3 | agent → architect bot | writes the [bundle](../assets/example/bundle/bundle.json); `check` and `plan` pass | `worker_done` |
| 4 | architect bot → CTO bot | runs both commands itself and reports | [return report](../assets/example/return-report.md) |
| 5 | CTO bot | runs `plan`, then `post` with the reported digest | the commands below |
| 6 | CTO bot → owner | reports and stops | the parent, the new issues, what stayed open and why |

## The CTO bot's commands

```bash
ORCA orchestration send --to "bot:<architect>" --chat new --type handoff \
    --subject "<parent chat name>" --body-file architect-brief.md      # opens the child chat; record its id
# the status arrives; then, with the directory and digest it names:
python3 <this skill>/scripts/refactor_bundle.py plan <bundle dir>
python3 <this skill>/scripts/refactor_bundle.py post <bundle dir> --digest <digest>
```

`post` prints each issue it creates and closes, then the summary:

```text
New: <owner>/<api repo>#101, <owner>/<api repo>#102, <owner>/<web repo>#44, <owner>/<api repo>#103
Parent: <owner>/<api repo>#101
Closed as not planned (3): <owner>/<api repo>#12, <owner>/<web repo>#7, <owner>/<web repo>#9
Not closed (reported):
  - <owner>/<api repo>#15: open linked pull request <url>; never closed automatically
```

Here `#15` stays open: its pull request is somebody's work. The CTO bot reports it and leaves the choice to the owner.

## If it stops half way

Run the same `post` again. `plan` first shows which new issues exist (`exists as #n`); only the missing ones are
created, and an issue that already has its closing comment gets no second one.
