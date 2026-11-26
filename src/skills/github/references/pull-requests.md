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

## Merge rules

A pull request may be merged only when **both** hold:

1. **It links an issue** of this repository: `Closes #N`, or `Refs #N` for partial work.
2. **Every linked issue is approved.** As shipped, **only the repository owner's comment** on the issue, from the
   [acceptance template](../assets/owner-acceptance.template.md), approves it.

The `approvals` list in [merge-rules.json](../assets/merge-rules.json) says which approvals count; any one of them is
enough:

| `approvals` value | What counts | Shipped |
|---|---|---|
| `owner_comment` | the owner's comment on the issue, from the [acceptance template](../assets/owner-acceptance.template.md) | on |
| `owner_author` | an issue the owner created | off |
| `board_status` | board status `Todo` or `In Progress` | off |

The other two are **off while agents share the owner's account**: an issue that account created and a board status set
from it may be an agent's work. A project where agents have their own accounts may list them again; each then works as
the table says. A missing or empty `approvals`, or a value not in the table, refuses every issue and says why.

**These refuse it, whatever else says yes:** the issue is closed (done, not planned or duplicate), it is labelled
`duplicate` or `wontfix`, or its board status is `Done`, `Not planned`, `Duplicate` or `Canceled`. The same rules decide
whether work on an issue may **start** ([before any work](issues.md#before-any-work)). The status and label names are in
merge-rules.json too.

```bash
python3 <github skill>/scripts/issue_gate.py pr <number> --repo <owner>/<repo>      # must end 'merge rules: allowed'
```

- **Agents may share the owner's account**, so an issue or comment with an agent's `Created: <name>` line is never the
  owner's. An agent **never** writes the acceptance comment, signs as the owner, or moves an unapproved issue to `Todo`
  or `In Progress`. The script cannot tell who typed an unsigned comment: this is the agent's duty.
- The acceptance counts only when it is the comment's **first line**, the comment is **not hidden**, its author is the
  owner, and it carries **no agent's** `Created:` line.
- With `owner_author` on, the owner leaves the `Created:` line out of their own issues, or signs it with their account
  name.
- **The check uses the `gh` login as it is.** When GitHub answers that the login lacks the scope to read project
  boards, the check goes on without the board and its output says `the board was not read`. The closed state, the
  refusing labels and the owner's comment (and authorship, when `owner_author` is on) work as before. **Not checked
  then:**
  - a board `Done` or `Not planned` (or `Duplicate`, `Canceled`) on an issue that is **still open**: it does not
    refuse. To stop such an issue, close it or give it a refusing label;
  - **approval by board status**, when `board_status` is on: `Todo` or `In Progress` approves nothing. The issue
    needs another approval that is on, such as the owner's comment.
- **Any other failure to read the board refuses** everything: the board may say done or not planned. Run the check
  again; do not merge until it reads the board or reports the missing scope.
- Refused: do not merge. Report the reason and the one thing the owner can do.

## Merge

Who merges is the playbook's choice: in `playbook-quick` the CTO/CEO after its own `Accepted by`; in
`playbook-complete` the CTO/CEO on the reviewer's PASS; in `playbook-ship` the reviewer after its PASS. Never the PR's
author. A project whose rules reserve the merge for a person wins.

Before: the [merge rules](#merge-rules) allow it, the checked SHA is still the head, required checks are green, the branch is
not behind `main`.

```bash
python3 <github skill>/scripts/pr_loop.py can-merge --pr <number> --repo <owner>/<repo>   # the judgment is on this head
python3 <github skill>/scripts/issue_gate.py pr <number> --repo <owner>/<repo>
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
