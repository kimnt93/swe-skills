# Issues

An issue is the unit of work everyone can see. One workflow card ↔ one issue.

## Create

Body file (`issue.md`):

```markdown
## Goal
<the outcome a user or caller can observe>

## Acceptance
- [ ] <a command and its expected output: the done-predicate>

## Notes
<context, links, decisions already made>
```

```bash
gh issue create --title "Cancel an open order" --body-file issue.md \
  --label "type:feat" --label "risk:standard" [--milestone "<m>"] [--assignee @me]
```

**Check after create:** `gh issue view <n> --json number,title,labels,milestone,url`.

## Work on it

- Reference it from the branch (`feat/<n>-...`), the card body (`issue: #<n>`) and the PR (`Closes #<n>`).
- Progress or a blocker: a comment (`gh issue comment <n> --body-file note.md`), never an edit of the
  original goal.

## Close

It closes itself when the PR with `Closes #<n>` merges. Close by hand only for "won't do" or a
duplicate, with the reason: `gh issue close <n> --reason "not planned" --comment "<why>"`.
Reopen when a merged fix turns out not to meet the acceptance: `gh issue reopen <n>`.

**Check after close:** `gh issue view <n> --json state,stateReason`.

## Labels (set up by the `project` skill)

`type:feat|fix|refactor|perf|docs|chore`, `risk:low|standard|money-path`, `cli:claude|omp`,
`tier:low|mid|top`, `size:large` (lifts the PR size limit; needs a reason in the PR).
