# Branches and commits

## Branch

**The name is a rule, not a habit.** `<type>/<issue>-<slug>`: a type from the list below, the **number of a real
issue**, then a lowercase slug of letters, digits and hyphens. `pr_lint.py` fails any other name and the merge gate
refuses it. Never invent a number, never use a run id or a date in its place.

**No issue yet? Create one first, then branch.** Check `gh issue list --search "<words>"` for a duplicate; if none,
write the goal and the done-predicate to a file and run
`gh issue create --title "<type>: <goal>" --body-file <file>` (labels per the **project** skill). Use the number it prints.
Work that is not your card's issue (a bug you found, a missing doc, a follow-up) becomes its own new issue, not a
silent extra change on this branch.


```bash
git fetch origin
git switch -c <type>/<issue>-<slug> origin/main      # feat/42-cancel-order, fix/57-dup-fills
```

Types: `feat` `fix` `refactor` `perf` `test` `docs` `chore` `ci` `build`. One branch per issue. In
a `swe-cli` run, the card's worktree branch is named the same way (`--branch feat/42-cancel-order`).

## Commit

```bash
git add <the files of this unit>        # never `git add -A` blindly: check `git status` first
git commit -m "feat(orders): add CancelOrder use case" -m "Rejects orders that are already filled."
```

- **Conventional Commit subject:** `<type>(<scope>): <subject>`: imperative, at most 72 characters,
  no period. Scope = the area (`orders`, `api`, `web`, `ml`). `!` after the scope marks a breaking change.
- **One logical unit per commit,** green on its own (`make verify` or at least the unit's tests).
- A body only when the why isn't obvious; never restate the subject.
- No generated files, build output, `.env`, keys.

## Push

```bash
git push -u origin HEAD
```

**Check after push:** `git status -sb` shows `## <branch>...origin/<branch>` with nothing ahead.

## Keep up with main

```bash
git fetch origin && git rebase origin/main     # your own branch only
git push --force-with-lease                    # only on a branch only you push to
```

Never rebase or force-push a branch another agent or person pushed to: ask its owner. Resolve
conflicts by keeping both intents; re-run `make verify` after.
