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
2. **Every linked issue is approved.** As shipped, an issue is approved when it was **opened by an account with write
   access** to the repository, or when the repository owner **accepted it with a comment** from the
   [acceptance template](../assets/owner-acceptance.template.md).

**What now needs no approval:** an issue opened by an account that can push to the repository: its role is `admin`,
`maintain` or `write`. The merge rules approve it as it is, agent-written or not: nobody has to accept it and nobody has
to review its code for the rules to allow the merge. **What still needs the owner:** everyone else's issue: an outsider,
an organization member with the default read access, a collaborator with the read or triage role, a custom role, an app
or bot account, and any issue whose author's permission cannot be read. Being a `MEMBER` or `COLLABORATOR` is not
enough: those author associations say nothing about write access. For such an issue alone the owner posts one line,
which works in any shell:

```bash
gh issue comment <number> -R <owner>/<repo> --body "Accepted by owner."
```

The approvals do not replace the playbook: `risk:money-path` is never merged automatically, a playbook's own review still
runs, and a project whose rules reserve the merge for a person wins.

The `approvals` list in [merge-rules.json](../assets/merge-rules.json) says which approvals count; any one of them is
enough:

| `approvals` value | What counts | Shipped |
|---|---|---|
| `trusted_author` | an issue whose author can push: `gh api repos/<owner>/<repo>/collaborators/<login>/permission` answers `role_name` `admin`, `maintain` or `write`, with the base `permission` GitHub maps it to (`admin`, `write`, `write`) and `user.permissions.push` true. `read`, `triage`, a custom role, a failed lookup or any odd answer approves nothing | on |
| `owner_comment` | the owner's comment on the issue, from the [acceptance template](../assets/owner-acceptance.template.md), while the issue's body and title are as the owner saw them: a body edit or a title rename at or after the comment (GraphQL `lastEditedAt`, `RenamedTitleEvent`), or edits that cannot be read, and it approves nothing until the owner accepts again | on |
| `owner_author` | an issue the owner created | off |
| `board_status` | board status `Todo` or `In Progress` | off |

`owner_author` and `board_status` are **off while agents share the owner's account**: an issue that account created and
a board status set from it may be an agent's work. `trusted_author` approves the issues of accounts that could push the
code themselves, the agents' included, so that the owner approves nothing by default. **The gh login** that runs the
check must be able to read the repository's collaborator permissions: give it write access to the repository (a classic
token needs the `repo` scope). Without that the lookup fails, and only the owner's comment approves. A project that wants every issue accepted
by hand lists `["owner_comment"]` alone. A missing or empty `approvals`, or a value not in the table, refuses every issue
and says why.

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
  owner, it carries **no agent's** `Created:` line, and **nobody changed the issue after it**: the check reads when the
  body was last edited and the title last renamed, and an edit at or after the comment's time voids it (the refusal says
  so and gives the line to accept again). If that history cannot be read, the comment approves nothing; run the check
  again. An issue whose author has write access needs no comment, so its edits are not read.
- **A pull request links issues of its own repository only.** A closing reference to another repository's issue is
  refused by `issue_gate.py pr` and by both forms of `pr_loop.py can-merge`; it is never read as the same number here.
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
- Refused: do not merge. Report the reason and the one thing the owner can do; when only an approval is missing, that
  is the one line above.

## Merge

Who merges is the playbook's choice: in `playbook-build` the CTO/CEO on the reviewer's PASS; in `playbook-quick` the
CTO/CEO on the mechanical conditions alone, with no check of the code; in `playbook-ship` the reviewer after its PASS;
`playbook-plan` and `playbook-review` merge nothing. Never the PR's author. A project whose rules reserve the merge for a person wins.

Before: the [merge rules](#merge-rules) allow it, the checked SHA is still the head, required checks are green, the branch is
not behind `main`.

```bash
python3 <github skill>/scripts/pr_loop.py can-merge --pr <number> --repo <owner>/<repo>   # the judgment is on this head
python3 <github skill>/scripts/issue_gate.py pr <number> --repo <owner>/<repo>
gh pr view <number> --json headRefOid,mergeable,mergeStateStatus
gh pr checks <number> --required
gh pr merge <number> --repo <owner>/<repo> --rebase --match-head-commit <checked sha> --delete-branch
```

**Whose verdict counts.** `can-merge` counts a refusal (FAIL, `Changes required`, `Stopped`) from any owner, member or
collaborator, and a `Verdict: PASS` only when its author can also push (the same permission lookup as the merge rules'
`trusted_author`): a read-only member's PASS approves nothing, and a failed lookup never drops a refusal. An old
`Accepted by CTO ... PR #<n>` approves nothing.

**A PASS counts only with its security check.** `can-merge` and `decide` refuse a PASS without the `## Security`
section of the [security-review](../../security-review/SKILL.md) skill, one with a proven finding, one whose scan is of
another head or did not run, and one with an outbound path that no linked issue asks for: each `asked for by #<n>` line
is checked against the text `issue_gate.py asked <n> --repo <owner>/<repo> --pr <pr>` prints. A FAIL counts without it.

In `playbook-quick` nobody judged the head, so its first line is the unreviewed form of `can-merge`, with the head
the developer reported ([quick, step 5](../../playbook-quick/SKILL.md#5-ctoceo-merge-then-confirm)). Only quick uses it,
and the script holds it to that: it refuses any PR that carries a judgment or a stop, and any PR whose linked issues do
not all carry the `Pipeline: quick` line that only quick writes. It cannot know which head was reported: the CTO/CEO
takes that SHA from the builder's report.

`gh pr checks <number> --required` printing `no checks reported` and exiting 1 means the repository has **no** checks,
not that one failed: report "no checks".

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
