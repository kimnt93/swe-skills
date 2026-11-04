# Delegation: sessions in git worktrees

How a project's orchestrator hands work to Claude Code, Codex or oh-my-pi, and how several agents code in one
repository (or several) with few conflicts. The commands are `swe-cli delegate` and `swe-cli orchestrate` (see
`cli/bin/delegate`); the orchestrator's rules are in the `manager` skill.

## Why sessions and worktrees

- The orchestrator is any CLI agent (Claude Code, Codex, oh-my-pi) started in the project directory by
  `swe-cli orchestrate <project>`. It does not code: it starts the coding CLIs as processes.
- A **session** per card (a tmux session, or an Orca terminal with `launcher: orca`) is something the orchestrator
  can drive (start, hand over a brief, send keys, read the screen) and you can watch and take over.
- A **git worktree** per card gives each agent its own checkout and branch from one clone, so many agents code at
  once without sharing files. The CLI starts fresh each card: no memory crosses projects.

## The commands

```bash
swe-cli project add orders --dir ~/work/orders --repo api=acme/orders-api --repo web=acme/orders-web
swe-cli doctor <project>                       # git credentials, tmux or Orca, CLIs, gh, the state of each clone
swe-cli orchestrate <project> [--agent A]       # the project's manager agent, in its directory
swe-cli delegate start <project> <card> --repo api --files internal/orders/,go.mod \
     --goal "<outcome, acceptance command, shared decisions>" --branch feat/41-cancel-order --issue 41 \
     [--agent developer] [--cli C] [--model M] [--reasoning R] [--risk standard] [--dry-run]
swe-cli delegate status <project> [<card>] [--fetch]   # table, or one card's JSON
swe-cli delegate send <project> <card> "<text>"        # type into the session
swe-cli delegate review <project> <card>               # the other CLI, read-only, same worktree
swe-cli delegate scope <project> <card>                # files changed outside the card's list (exit 8)
swe-cli delegate sync-branch [--verify]                # in a worktree: fetch, rebase on origin/main, make verify
swe-cli delegate stop|cleanup <project> <card>         # cleanup after the PR is MERGED (or --force)
tmux attach -t <project>-<card>                      # watch or take over (launcher tmux); in Orca: the terminal titled so
```

`start` does, in order: refuse overlapping cards and taken branch names; **fetch (and stop if it fails)**; base on
`origin/main`; `git worktree add -b`; mark the worktree trusted for Claude Code; start the CLI in a session with
its model, effort and compaction point; wait for the prompt (answering Codex's and Claude's trust dialogs); write the
brief (`cli/brief.md`) to `.swe/brief.md` in the worktree and tell the CLI to read it. The agent ends with one line,
`CARD DONE <sha> <pr url>` or `CARD BLOCKED <reason>`, which `status` reads from the pane.

Exit codes: 4 fetch failed, 5 overlap or hotspot, 6 rebase conflict (branch unchanged), 7 uncommitted changes,
8 files outside the list, 9 the CLI never showed its prompt, 10 no `make verify` in the repo, 11 the branch name is taken.

## Layout

```text
~/work/<project>/            the project directory (dir: in projects.yaml)
  api/  web/                 central clones, one per repo: on main, clean, never edited
  .wt/<repo>/<branch>/       one worktree per card: api/feat-41-cancel-order/, web/fix-42-null-fill/, ...
~/.swe/<project>/<card>.json   what the orchestrator knows: repo, branch, worktree, session, files, base SHA, CLI
```

`SWE_WORKTREES` (replaces `<dir>/.wt`) and `SWE_STATE` change the second and the last.

## Several projects, one repo

Two projects can clone the same GitHub repo, each into its own directory (say a product and an experiment on the same
service). That is allowed; the conflicts are solved in branches: `swe-cli delegate start` compares the new card with the
open cards of every project on the same GitHub repo (files and hotspots, exit 5), refuses a branch name that exists
locally, on origin or in another project's card (exit 11), and bases each card on a fresh `origin/main`. Each
project's worktrees are separate checkouts, so nothing is shared on disk.

## Keeping conflicts small

Starting from the latest `main` is necessary, not sufficient. Most conflicts come from two agents editing the same
files in the same hours, so:

| When | Rule | What it prevents |
|---|---|---|
| planning | each card lists its files; a card that overlaps an open card, or touches a **hotspot** another card holds, is refused and waits | the main cause of conflicts |
| start | fetch must succeed; base is `origin/main`; the base SHA is recorded | starting stale |
| working | one feature function, about 400 changed lines, branches live hours | drift |
| before the PR | `swe-cli delegate sync-branch --verify` (fetch, rebase, `make verify`); `scope` reports nothing outside the list | late conflicts, scope creep |
| merge | `swe-cli merge` refuses a branch that is behind or in conflict with `main`; squash only, one at a time | merging a stale branch |

**Hotspots** are files that collide between unrelated features: migrations (two agents take the same number),
lockfiles, generated clients, route registries, `CHANGELOG`. List them under `hotspots:` in `cli/projects.yaml`.

**Conflicts go to a person.** `sync-branch` aborts the rebase, leaves the branch as it was and names the files;
the manager reports them; you (or the card that owns those files) resolve them. Git sees text conflicts only: two
branches that change the same behaviour in different files merge cleanly, and `make verify` after the rebase is what
catches them.

## Viewing the sessions with Orca

Set `launcher: orca` in the project's `config.yaml`. `swe-cli project sync` registers each clone in Orca (`orca-ide repo add`),
Orca then lists the worktrees, and `swe-cli delegate start` opens each card as an Orca terminal in its worktree, titled
`<project>-<card>`, so you see the sessions beside the branches. Orca must be running on the machine (`orca-ide open`);
the terminal handle is kept in `~/.swe/orca-handles.json`. Sessions started over SSH on a machine without a running
Orca need the default `launcher: tmux`.

Call `orca-ide`, not `orca`: on Linux `/usr/bin/orca` is usually the GNOME screen reader, and `orca terminal list
--json` against it hangs or prints nothing, notably over SSH. Other viewers for tmux sessions (Webmux, Claude Squad)
are optional and not run by this repo.

## When something goes wrong

| Symptom | What to do |
|---|---|
| `cannot fetch origin` (exit 4) | credentials: use an SSH remote or `gh auth setup-git`; `swe-cli doctor <project>` |
| refused for overlap (exit 5) | wait for the holder to merge and `cleanup`, or split the work so the files differ |
| `status` shows `stopped` | the CLI exited; `tmux` kept the last output (`remain-on-exit`); read it, then restart the card |
| quota or login error in the pane | the orchestrator tells you and asks: wait, or `cleanup --force` and `start --cli <other>` |
| the CLI shows a dialog the orchestrator cannot answer | attach to the session (tmux, or the Orca terminal), answer it, detach |
