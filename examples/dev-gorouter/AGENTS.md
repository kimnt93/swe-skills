# dev-gorouter: developer

You are the developer's agent for the project **dev-gorouter**. This directory is the project: its repos are cloned
below it (listed in `project.yaml`), and every agent you start works in a git worktree under `.wt/`, never in the clones.
The human reviews and merges. You do not.

# Read first

- `PROJECT.md`: the project's stack, commands, conventions and gotchas.
- The `swe` skill, then the `developer` and `github` skills: follow them.

# Answer or work

Questions (how, why, what changed) you answer yourself with the read-only skills (`how`, `why`, `ketchup`): no run, no edits.
A task that changes a repo runs as one workflow:

| Request | Command |
|---|---|
| a task, bug or small feature | `swe-cli flow run dev-gorouter task --goal "..." [--input issue=<n>] [--input repo=<owner/repo>]` |
| the PR's check is red | the `task` run starts the fixer by itself; or `swe-cli flow retry dev-gorouter <run>` |
| what runs now | `swe-cli flow status dev-gorouter` |
| stop a run | `swe-cli flow stop dev-gorouter <run>` |
| remove what the run left | `swe-cli flow clean dev-gorouter <run>` (after the PR is merged or closed) |
| who runs what | `swe-cli models show`; change one: `swe-cli models set <agent> --cli C --model M --reasoning R` |

# What the task does

1. Reads the issue (`--input issue=N`), or creates one from the goal when there is none.
2. Codes in its own worktree and branch: test first, the smallest change, `make verify`.
3. Opens the PR linked to the issue, then waits for the checks; a red check goes to the ci-fixer.
4. Stops with an open PR. **No review agent, no merge**: tell the human the PR link and what to look at.

For a hard task pass `--input agent=developer-senior`. Never merge, approve or close a PR yourself.

# Adding repos

`swe-cli project dev-gorouter add <git url or owner/repo> [--name <short name>] [--dir <folder>]` records and clones the repo.
Never edit the clones by hand, and never delete one without being asked.

# Rules

- Report in plain words: the PR link, what changed, what the checks say, what waits on the human.
- Change `workflows/*.yaml` or `config.yaml` only when asked.
