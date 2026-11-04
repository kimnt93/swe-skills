# Harness map

The skills in this stack say *what* to do in harness-neutral words. This table says *how* in
each harness. If a row has no way to do it, say so in your reply and continue.

| The skill says | Claude Code | omp | Codex | Hermes kanban worker |
|---|---|---|---|---|
| start a subagent at tier T | the `Agent` tool with `subagent_type: "@PLUGIN@:worker"`; `model` and `effort` from `fleet models cmd claude <T>` (`opus`/`sonnet`/`haiku`) | the `task` tool; tiers map to omp roles (`@slow`, `@task`, `@smol`) | its subagent tool, or `codex exec` in a separate worktree | `delegate_task` for a short answer; `kanban_create` for work that crosses agents |
| a cross-family review or a multi-model panel | not possible in-harness: ask for a review card on the board, or have the project's manager run `fleet delegate review <project> <card>` | not possible in-harness: `fleet delegate review <project> <card>` | same as omp | `fleet delegate review <project> <card>` (the other CLI, in tmux) |
| a read-only subagent | `Agent` with `subagent_type: "@PLUGIN@:adversary"` to break a change, or `"Explore"` to map code; say "do not edit files" in the brief | the `scout` agent | a brief that says read-only; check `git status` after | a card titled `scout:` at tier `low` |
| a separate worktree | `Agent` with `isolation: "worktree"` | `task.isolation.enabled` in omp config | `git worktree add` | card workspace `worktree` |
| ask the human | `AskUserQuestion` (plain text in `-p` mode) | ask in plain text | ask in plain text | `kanban_block(reason=...)` |
| a todo list | `TodoWrite` | the `todo` tool | in the reply | the `todo` tool, plus kanban comments |
| wake me later / keep going | `/loop` | `--max-time`, or a Hermes card | a Hermes card | a `--goal` card, or `hermes cron` |
| a decision trail | a `.trail.tsv` in the worktree (one row per decision) | same | same | kanban comments and run metadata |
| a project-local skill | `.claude/skills/<name>/` | `.omp/skills/<name>/` or `.claude/skills/<name>/` | `.agents/skills/<name>/` | `.hermes/skills/<name>/` or `.agents/skills/<name>/` |
| this session's transcripts | `~/.claude/projects/<workspace-slug>/*.jsonl` | `~/.omp/agent/sessions/<workspace-slug>/` | `~/.codex/sessions/` | `hermes sessions`, `hermes kanban runs <id>` |

Read transcripts only for the current workspace. Never glob across other workspaces.
