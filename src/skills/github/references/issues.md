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

**Never implement** an issue that is done, not planned or duplicate. An open issue also needs one approval of the
[merge rules](pull-requests.md#merge-rules): the owner's acceptance comment, the owner as its author, or board status
`Todo` / `In Progress` (counted only when the check could read the board).

**Not approved yet:** report the issue link and give the owner this comment to post
([template](../assets/owner-acceptance.template.md)), then stop. The owner posts it, never an agent:

```text
Accepted by owner.

Notes: none
```

The first line is what counts. `Notes:` can hold limits for the developer. To withdraw it, hide or delete the comment, or
close the issue as not planned.

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
