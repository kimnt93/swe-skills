# Plans

What has been built (with the command that proves it still works), and the few steps that need a
human. Everything an agent could do alone is done.

## How an agent uses this directory

1. Read `AGENTS.md`, then this file.
2. A `done` plan is a record: run its **Verify** after any change that could break it.
3. A `human` plan is a runbook: do every step you can, stop at the first step that needs the
   human (a login, a choice, an approval), and say exactly what they must do.
4. New work gets a new numbered plan (template below), in its own commit, before the code.
5. When a step is wrong, fix the plan in its own commit and say why in its `Log`.

## Status

| # | Plan | Status | Needs a human for |
|---|---|---|---|
| 00 | [architecture](00-architecture.md): the system and its decisions | reference | — |
| 01 | [plugin-build](01-plugin-build.md): build any name, validate, install, package | done | — |
| 02 | [process-skills](02-process-skills.md): router, principles, 13 process skills, 14 playbooks | done | — |
| 03 | [enforcement](03-enforcement.md): prose rules turned into checks | done | — |
| 04 | [fleet-kit](04-fleet-kit.md): `models.yaml` for every agent, the `fleet` command, the merge guard | done | — |
| 05 | [publish](05-publish.md): release the built plugin | done | choosing the publish remote |
| 06 | [install-local](06-install-local.md): `/swe` in Claude Code, omp, Hermes | done | restarting open sessions |
| 07 | [pilot-verify](07-pilot-verify.md): `make verify` in one real service | human | picking the service, the required CI check |
| 08 | [fleet-live](08-fleet-live.md): logins, bootstrap, the first cards | human | logins, merging the first PRs |
| 09 | [autopilot](09-autopilot.md): auto-merge a trusted risk class | human | the switch, weekly sampling |
| 10 | [model-upgrade](10-model-upgrade.md): a new model ships | runbook | changing the managers' model |

## Plan template

```markdown
# NN — title

status: todo | done | human | runbook

## Goal
One paragraph: the outcome and who notices it.

## Steps
1. ... (each step ends in a state you can check)

## Verify
Commands and the output that proves the goal.

## Log
- YYYY-MM-DD: what landed.
```
