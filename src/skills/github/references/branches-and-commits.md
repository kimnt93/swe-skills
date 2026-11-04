# Branches and commits

## Branch

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
