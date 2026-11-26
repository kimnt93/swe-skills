# Identity: everything carries the agent's name

All agents may share one account and one machine. So the **name** says who did the work: on every commit, and on the
last line of every issue, comment, review and PR body.

## Your agent name

The name your instructions give you ("You are ..."), written exactly, for example `Release Bot (Developer)`. A delegated
worker uses the name its brief gives it; a brief without one is incomplete, so ask. It is never the account name, the
machine's `git config user.name`, a model name or "assistant".

Pass it with `--author` on each call, or set `AGENT_NAME` (shells may not keep it between calls).

## Commit

Never plain `git commit`. Every command that writes history goes through the script:

```bash
S=<this skill>/scripts/agent_identity.py
python3 $S git --author "<agent name>" -- commit -m "feat(api-03): add the cancel route"
python3 $S git --author "<agent name>" -- rebase origin/main        # also merge, cherry-pick, revert
python3 $S check --author "<agent name>" --base origin/main        # before every push: 0 problems
```

It sets the author **and** the committer through the environment and leaves the git configuration alone (worktrees share
it). The email is `<slug of the name>@agents.invalid`, a reserved domain, so the host shows the agent's name instead of
a person's account. A project that needs a real address sets `AGENT_EMAIL`.

**A wrong author on your own unpushed commit:** `python3 $S git --author "<agent name>" -- commit --amend
--reset-author --no-edit`. Never rewrite another agent's commits. When two agents really committed on one branch (a
reviewer named as fixer), give `--also-author "<other name>"` to `check` and to `pr_lint.py`.

## Issues, comments, reviews, PR bodies

The last line is the signature:

```text
Created: <agent name>
```

```bash
python3 $S stamp --author "<agent name>" note.md      # adds it; refuses to re-sign another agent's text
```

`package_lint.py` and `pr_lint.py` fail a text without it, and, with `AGENT_NAME` set, a text signed by another name.
Run them before every `gh issue create`, `gh issue comment`, `gh pr create`, `gh pr comment` and `gh pr review`.

## Merges keep the author

Merge by **rebase**. A rebase merge puts the branch's own commits on `main` with their author, so the agent's name
stays; the merging account is only the committer. A squash or a merge commit is a **new** commit whose author the host
takes from the account's profile, so the agent's name is lost: use neither.

Every commit on the branch therefore lands on `main`, so each one is a Conventional Commit under an agent's name. Check
after the merge: `git log origin/main -<number of commits> --format='%an | %s'`.

## Limits

These are checks the agent runs. The host does not enforce them: to enforce them there, run
`pr_lint.py pr <number>` as a required check.
