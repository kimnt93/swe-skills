# Pull requests

## Open

Every pull request has **one** body format, whatever its branch:
[pr.template.md](../../work-package/assets/pr.template.md). Copy it to a file (`pr.md`), replace every `<...>` and sign
it `Created: <author>`. No "Generated with" or other tool footer: remove it if your harness adds one. To change the
style, edit the template ([templates](../../write-issue/references/templates.md)); the linters read it.

```bash
python3 <github skill>/scripts/pr_lint.py local --body pr.md --allow 'internal/orders/**'
gh pr create --base main --head "$(git branch --show-current)" \
  --title "feat(orders): cancel an open order" --body-file pr.md \
  --label "risk:standard"
```

The title follows the same Conventional Commit rules as a commit subject. Open it ready (not draft).
`Closes #N` closes the issue on merge; use `Refs #N` for partial work.

**Check after open:**

```bash
gh pr view --json number,url,headRefOid,isDraft,mergeable,labels
python3 <github skill>/scripts/pr_lint.py pr <number>
gh pr checks <number> --watch              # wait for CI; read the failure, never just re-run
```

## Update

New commits on the same branch, pushed. Edit the body with `gh pr edit <n> --body-file pr.md`. A push
after a review needs a new review: the verdict covers one head SHA.

## Merge

Who merges, and after which check of the head, is the playbook's choice. Never the author. A project whose rules reserve the merge for a person wins.

Before: the checked SHA is still the head, required checks are green, the branch is not behind `main`.

```bash
gh pr view <number> --json headRefOid,mergeable,mergeStateStatus
gh pr checks <number>
gh pr merge <number> --repo <owner>/<repo> --rebase --match-head-commit <checked sha> --delete-branch
```

`--match-head-commit` stops a later push from slipping in. Never `--admin`; a refusal is a finding, not an obstacle.
**Always `--rebase`**: it keeps each commit's author ([why](identity.md#merges-keep-the-author)). A branch with a merge
commit cannot be rebased: its author rebases it on `main`, and the new head is checked again.

**Check after merge:**

```bash
gh pr view <number> --json state,mergeCommit,closingIssuesReferences   # state MERGED
git fetch origin && git log origin/main -<commits> --format='%an | %s'   # every author is an agent name
gh issue view <issue> --json state                                       # CLOSED
gh run list --branch main --limit 1                                      # CI on main started / green
```
