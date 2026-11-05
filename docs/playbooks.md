# Playbooks

A playbook is a workflow you start with one shortcut. Say the request to the manager, or type the shortcut. Each
`play-*` skill restates the goal and its proof, then hands the run to the manager, which runs `swe-cli flow run`.
`/swe:play` lists them, or starts any workflow by name (a project's own `workflows/` too).

| Shortcut | Workflow | Use it for | Inputs |
|---|---|---|---|
| `/swe:play-deliver` | `delivery` | any code goal, one repo or several, merged to main without a human (the default) | `goal` |
| `/swe:play-bugfix` | `bugfix` | a defect with a repro: failing test first | `goal` |
| `/swe:play-docs` | `docs` | `docs/` stale or missing; no planner | `repo`, `mode` = `follow` or `rewrite` |
| `/swe:play-cifix` | `ci-fix` | a red required check on an open PR | `pr`, `repo` |
| `/swe:play-rebase` | `conflict` | a PR behind main or conflicting | `pr`, `repo` |
| `/swe:play-changelog` | `changelog` | a PR missing its change log entry | `pr`, `repo` |
| `/swe:play-verify` | `verify` | nightly or after merges; edits nothing | `repo` |
| `/swe:play-review` | `review` | check any PR at its head, read-only | `pr`, `repo` |
| `/swe:play-land` | `land` | take an existing PR, a human's too, to main | `pr`, `repo` |
| `/swe:play-solo` | none: this chat does every step | one goal or issue, plan only or plan to merged PR, no subagent | `goal`, `mode` = `full` or `plan` |
| (DEV mode) | `task` | one task to an open PR; you review and merge | `goal` |

`feature` stays for a goal you want to merge by hand at the end.

## DAGs

```text
delivery  plan ─► cards (one lane each, in parallel) ─► report
lane      code ─► docs ─► build(PR) ─► [wait for providers ─► sync] ─► checks ⟲ci-fix ─► review ⟲fix ─► merge
bugfix    plan ─► card (code ─► docs ─► PR ─► checks ─► review) ─► report
docs      write ─► checks ⟲ci-fix ─► review ⟲fix ─► report
ci-fix    fix ─► checks ─► review ─► report
conflict  integrate ─► review ─► report
changelog add ─► checks ─► review ─► report
verify    verify ─► report
review    review ─► report                                   (read-only)
land      integrate ─► checks ⟲ci-fix ─► review ⟲fix ─► merge ─► report
task      code ─► docs ─► build(PR) ─► checks ⟲ci-fix ─► report
solo      (in this chat, no subagent) issue ─► plan ─► branch ─► code ─► docs ─► verify ─► PR ─► self-review ⟲fix ─► checks ⟲fix ─► merge
```

## Rules

- A shortcut starts one workflow and does none of its steps. The manager picks any other workflow.
- `delivery` and `land` merge by themselves: set `autopilot.auto_merge` in `config.yaml`. `money-path` always waits
  for the requester.
- Every code card updates `docs/` before its PR opens (the `docs-sync` skill). Other repos read `docs/README.md` first.
- A project's `PROJECT.md` opens with a `# Map` of its repos and dependencies; the planner uses it.
- `play-solo` is the exception: it starts no workflow and no subagent, so the review is the author's own (the `interrogate`
  skill, one adversary at a time) and the merge still goes through `swe-cli merge`; `mode=plan` stops after the plan and creates nothing.
- Naming: `play-*` skills start a workflow (`play-solo` runs the steps in your chat); every other skill is knowledge loaded into your chat.
