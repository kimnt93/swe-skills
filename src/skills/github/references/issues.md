# Issues

An issue is the unit of work everyone can see. One workflow card ↔ one issue.

## Create

Use the `write-issue` skill: the kind (epic, planning card, package), the catalog values, the body and the lint run.
The body ends with `Created: <agent name>`.

**Check after create:** `gh issue view <n> --json number,title,labels,url`.

## Before any work

An agent starts work on an issue (a worktree, a branch, code) only when this allows it:

```bash
python3 <github skill>/scripts/issue_gate.py issue <number> --repo <owner>/<repo>   # 'implementation: allowed'
```

**Never implement** an issue that is done, not planned or duplicate. An open issue also needs the approval of the
[merge rules](pull-requests.md#merge-rules): as shipped, an issue **opened by an account with write access** (its role on
the repository is `admin`, `maintain` or `write`) is approved as it is, and **nobody has to accept it**. A `MEMBER` or
`COLLABORATOR` with only read or triage access is not enough. An issue the owner's account
created and a board status `Todo` / `In Progress` approve nothing by themselves: they are off while agents share the
owner's account (the `approvals` list in [merge-rules.json](../assets/merge-rules.json)).

**Refused as not approved** (an outsider's or a read-only account's issue, or its author's permission could not be read): report the issue link
and give the owner this one line, which works in any shell, then stop. The owner posts it, never an agent:

```bash
gh issue comment <number> -R <owner>/<repo> --body "Accepted by owner."
```

The full form is the [template](../assets/owner-acceptance.template.md):

```text
Accepted by owner.

Notes: none
```

The first line is what counts. `Notes:` can hold limits for the developer. The acceptance covers the issue as the owner
read it: an edit of its body or a rename of its title after the comment voids it, and the owner reads the issue again
and posts the line again. To withdraw it, hide or delete the comment, or close the issue as not planned.

## Work on it

- Reference it from the branch (`feat/<n>-...`), the card body (`issue: #<n>`) and the PR (`Closes #<n>`).
- Progress or a blocker: a comment (`gh issue comment <n> --body-file note.md`), never an edit of the
  original goal. Comments use the `write-comment` skill.

## Close

It closes itself when the PR with `Closes #<n>` merges. Close by hand only for "won't do" or a
duplicate, with the reason: `gh issue close <n> --reason "not planned" --comment "<why>"`.
Reopen when a merged fix turns out not to meet the acceptance: `gh issue reopen <n>`.

**Check after close:** `gh issue view <n> --json state,stateReason`.

## Labels

Only the values in the `write-issue` catalog, plus the project's existing area labels (`gh label list`).
