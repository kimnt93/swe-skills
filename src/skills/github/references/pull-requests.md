# Pull requests

## Open

Write the body to a file first (`pr.md`):

```markdown
## Why
<the problem, 1–3 sentences>

## What changed
- <1–3 bullets, the real symbols or endpoints>

## Scope
<what it covers and what it leaves out>

## Blast radius
<who or what it touches, and why that is safe>

## Verification
- `make verify`: <result>
- <the live check or the test that proves the behaviour>

Closes #42
```

```bash
python3 <github skill>/scripts/pr_lint.py local --body pr.md --allow 'internal/orders/**'
gh pr create --base main --head "$(git branch --show-current)" \
  --title "feat(orders): cancel an open order" --body-file pr.md \
  --label "risk:standard" --label "lane:claude"
```

The title is the squash commit's subject: same Conventional Commit rules. Open it ready (not draft).
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

Only through the gate, after the other model family's review passed on the current head:

```bash
fleet merge <number> --risk <low|standard|money-path> --sha <verified head sha>             # autopilot
fleet merge <number> --risk <...> --sha <verified head sha> --approved                       # the human said merge
```

The gate squash-merges with `--match-head-commit`, so a later push can't sneak in.

**Check after merge:**

```bash
gh pr view <number> --json state,mergeCommit,closingIssuesReferences   # state MERGED
git fetch origin && git log origin/main -1 --oneline                    # the squash commit
gh issue view <issue> --json state                                       # CLOSED
gh run list --branch main --limit 1                                      # CI on main started / green
```
