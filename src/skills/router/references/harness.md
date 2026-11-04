# Harness map

The skills in this stack say *what* to do in harness-neutral words. This table says *how* in
each harness. If a row has no way to do it, say so in your reply and continue.

| The skill says | Claude Code | omp | Codex |
|---|---|---|---|
| start a subagent at tier T | the `Agent` tool with `subagent_type: "@PLUGIN@:worker"`; `model` and `effort` from `swe-cli models cmd claude <T>` (`opus`/`sonnet`/`haiku`) | the `task` tool; tiers map to omp roles (`@slow`, `@task`, `@smol`) | its subagent tool, or `codex exec` in a separate worktree |
| a cross-family review or a multi-model panel | not possible in-harness: have the project's manager run `swe-cli delegate review <project> <card>` | not possible in-harness: `swe-cli delegate review <project> <card>` | same as omp |
| a read-only subagent | `Agent` with `subagent_type: "@PLUGIN@:adversary"` to break a change, or `"Explore"` to map code; say "do not edit files" in the brief | the `scout` agent | a brief that says read-only; check `git status` after |
| a separate worktree | `Agent` with `isolation: "worktree"` | `task.isolation.enabled` in omp config | `git worktree add` |
| ask the human | `AskUserQuestion` (plain text in `-p` mode) | ask in plain text | ask in plain text |
| a todo list | `TodoWrite` | the `todo` tool | in the reply |
| wake me later / keep going | `/loop` | `--max-time`, or a scheduled `swe-cli flow run` | a scheduled `swe-cli flow run` |
| a decision trail | a `.trail.tsv` in the worktree (one row per decision) | same | same |
| a project-local skill | `.claude/skills/<name>/` | `.omp/skills/<name>/` or `.claude/skills/<name>/` | `.agents/skills/<name>/` |
| this session's transcripts | `~/.claude/projects/<workspace-slug>/*.jsonl` | `~/.omp/agent/sessions/<workspace-slug>/` | `~/.codex/sessions/` |

Read transcripts only for the current workspace. Never glob across other workspaces.
