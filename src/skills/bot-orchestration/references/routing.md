# Pick the row

Every agent runs on one row of the team's [agent table](../assets/agent-table.template.md). The row gives the harness,
the model and the reasoning effort. **That table is the only place that sets them:** no skill, brief, config file or
default adds another value.

The CTO/CEO holds the table: the team's own filled copy, kept outside this plugin and every public repository. The bot
that starts an agent reads the row **before** the start and copies it into the brief:

```bash
python3 <this skill>/scripts/agent_table.py row medium     # prints the Row and Run on lines of the brief
python3 <this skill>/scripts/agent_table.py check          # every row is there and filled
```

## Which row

| The agent | Row |
|---|---|
| writes a plan or a set of issues | `planner/architect` |
| builds, tests, deploys or reviews an issue labelled `simple` ([catalog](../../write-issue/references/catalog.md)) | `simple`: clear, small, no design choice |
| the same for a `medium` issue | `medium`: several files, a complete rule list |
| the same for a `hard` issue | `hard`: open design, concurrency, hard bugs |

**Always `hard`, whatever the label:** a money path, authentication or security, data that can be lost, or a contract
between repositories. Only the planning agent takes `planner/architect`.

A row is a rating of the work, not a promise about the agent. A team may put the same model on several rows, so never
assume that harder work gets another model: the card, the checks and the review stay as strict on every row.

## When the table does not answer

- **No table, a missing row or an unfilled cell:** stop and ask the owner. There is no built-in default, and another
  row is not a substitute. `agent_table.py` exits 1 and says what is missing.
- **The row's agent cannot start, is out of quota, or Orca cannot give it the row's model or effort:** report
  `BLOCKED`. Never swap the model, the effort or the row to get it started.
- **Screens must be looked at and the row's agent cannot see them:** report `BLOCKED`.

## Escalate on evidence

| What happened | Next |
|---|---|
| the connection or process dropped | the same brief, same row |
| out of context | a smaller slice, same row |
| wrong approach, or the evidence command still fails | one retry with the failure in the brief; rate the issue again only when the evidence shows it is harder than labelled |
| two failures | stop, report to the delegating bot, re-plan |

## Never delegated to an agent a bot started

The merge, the decision (scope, priority, design, trade-off), the verdict on the bot's own work, and the acceptance
criteria: an agent may not weaken them.
