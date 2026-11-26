# Issues

An issue is the unit of work everyone can see. One workflow card ↔ one issue.

## Create

Use the `write-issue` skill: the kind (epic, planning card, package), the catalog values, the body and the lint run.
The body ends with `Created: <agent name>`.

**Check after create:** `gh issue view <n> --json number,title,labels,url`.

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
