# Pick the tier

The bot rates the **issue**, picks the tier **before** it starts the agent, and writes the tier in the PR.

| Difficulty ([catalog](../../write-issue/references/catalog.md)) | Tier | Typical work |
|---|---|---|
| `simple` | **light** | rename, config, one small test, a docs line, a one-file fix |
| `medium` | **standard** | a normal feature, API, refactor or migration across files; reproducing a bug |
| `hard` | **strong** | open design inside the issue, concurrency, hard bugs |

**Always strong, whatever the label:** a money path, authentication or security, data that can be lost, a contract
between repositories, or work that **failed twice** at a lower tier.

## Which CLI and model is a tier

This skill names **no CLI and no model**: they change. Each team keeps **one** table that says, for each tier, the Orca
agent id, the model and the effort, and what to use when one is out of quota. Read it before every start: the team's
routing table or model-routing skill, or the project's agent table (`swe-cli models show`; there `developer-junior` is
light and standard work and `developer-senior` is strong).

- No table, or a tier it does not cover: **ask the owner**. Never make up a model.
- The agent cannot start, or is out of quota: use the table's fallback. No fallback: report `BLOCKED`. Never move a
  strong job to a weaker tier to get it started.
- Screens that must be looked at need an agent that can see them: use what the table names for UI work.

## Escalate on evidence

| What happened | Next |
|---|---|
| the connection or process dropped | the same brief, same tier |
| out of context | a smaller slice, same tier |
| wrong approach, or the evidence command still fails | one retry at the next tier, with the failure in the brief |
| two failures | stop, report to the delegating bot, re-plan |

## Never delegated to an agent a bot started

The merge, the decision (scope, priority, design, trade-off), the verdict on the bot's own work, and the acceptance
criteria: an agent may not weaken them.
