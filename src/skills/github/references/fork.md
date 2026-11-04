# Working on a fork

Some projects work in a fork of another repository. `origin` is the fork; `upstream` is the original.
Cards branch from the fork's `main`, and the fork's `main` follows upstream. Which of the two PR targets
applies is set per project in its `AGENTS.md` (default: PRs merge inside the fork).

## Once per clone

```bash
git remote add upstream https://github.com/<upstream-owner>/<repo>.git   # or the SSH URL
git remote -v                                                             # origin = fork, upstream = original
gh repo set-default <fork-owner>/<repo>                                   # gh targets the fork unless --repo says otherwise
```

## Before every card: bring the fork's main up to date

Run in the central clone (it stays on `main`, clean):

```bash
git fetch upstream --prune
git merge --ff-only upstream/main          # fails if the fork's main has diverged: stop and report
git push origin main                       # only the fork's main, and only a fast-forward
```

A failed `--ff-only` means the fork's `main` has commits upstream does not: never force it. Report it to the
human; do not start cards until they decide.

## Opening the PR

- **Inside the fork (default):** `gh pr create --repo <fork-owner>/<repo> --base main --head <branch> ...`.
- **To upstream** (only when the project says so): `gh pr create --repo <upstream-owner>/<repo> --base main
  --head <fork-owner>:<branch> ...`. Upstream's contribution rules (template, commit style, CLA) win over ours.
- Issues and labels live in the repo the PR targets. `Closes #N` only closes an issue in that same repo.

## Rules

- Never push to `upstream`, and never push `main` of the fork except as the fast-forward above.
- A card's branch is based on the fork's `origin/main` after the sync above; the card list's files are checked
  against open cards as usual.
- After upstream merges your PR, sync again before the next card; delete the fork branch.
