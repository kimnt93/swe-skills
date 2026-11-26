# Harness map

The skills in this stack say *what* to do in harness-neutral words. This table says *how* in
each harness. If a row has no way to do it, say so in your reply and continue.

| The skill says | Claude Code | omp | Codex |
|---|---|---|---|
| start a subagent on a row of the agent table | the `Agent` tool with `subagent_type: "@PLUGIN@:worker"`, given the row's model and effort | the `task` tool, given the row's model and effort | its subagent tool, given the row's model and effort |
| a review by another agent | an Orca worker on the issue's row (the `delegate` skill) | same | same |
| a read-only subagent | `Agent` with `subagent_type: "@PLUGIN@:adversary"` to break a change, or `"Explore"` to map code; say "do not edit files" in the brief | the `scout` agent | a brief that says read-only; check `git status` after |
| a separate worktree | `Agent` with `isolation: "worktree"` | `task.isolation.enabled` in omp config | `git worktree add` |
| ask the human | `AskUserQuestion` (plain text in `-p` mode) | ask in plain text | ask in plain text |
| a todo list | `TodoWrite` | the `todo` tool | in the reply |
| wake me later / keep going | `/loop` | `--max-time`, or a cron schedule | a scheduled delegation |
| a decision trail | a `.trail.tsv` in the worktree (one row per decision) | same | same |
| a project-local skill | `.claude/skills/<name>/` | `.omp/skills/<name>/` or `.claude/skills/<name>/` | `.agents/skills/<name>/` |
| this session's transcripts | `~/.claude/projects/<workspace-slug>/*.jsonl` | `~/.omp/agent/sessions/<workspace-slug>/` | `~/.codex/sessions/` |

The [agent table](../../bot-orchestration/references/routing.md) alone says which harness, model and effort a row
runs on. A subagent runs in your own harness: use it only when the row names this harness and the tool can set the
row's model and effort. Otherwise start an Orca worker on the row (the `delegate` skill). A missing row means stop and
ask.

Read transcripts only for the current workspace. Never glob across other workspaces.
