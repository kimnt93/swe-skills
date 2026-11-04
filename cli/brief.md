# Start

Start with the {plugin} skill ({start}). Read `PROJECT.md` in the project directory for the project's stack and conventions.

# Card

- Card `{card}` of project `{project}`, repo `{repo}`
- Goal: {goal}
- Risk: {risk}
- Issue: {issue}
- Branch: `{branch}`
- Base: `{base}` (origin/main when this card started)
- Files you may change: {files}

{hotspots}
# Rules

- Work only inside this worktree (`{worktree}`) and only in the files listed. Anything else is a new
  card: stop and say so. Never push to main.
- Small conventional commits (the github skill). One feature function, a small diff.
- Before you open the PR run `{fleet} delegate sync-branch --verify`. It fetches, rebases on the latest
  origin/main and runs `make verify`. If it reports conflicts, stop and name the files; do not resolve
  conflicts with another card's work.
- If the branch was already pushed, push the rebased branch with `--force-with-lease` (your own branch only).
- Done means `make verify` exits 0 on the committed head, the PR is open with "Closes #{issue}" and
  `{fleet} delegate scope {project} {card}` reports no file outside the list.

# Last line

Exactly one of:

- `CARD DONE <head sha> <pr url>`
- `CARD BLOCKED <one-line reason>`
