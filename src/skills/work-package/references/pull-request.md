# Branch, commits, pull request

## Branch

`<id-lowercase>/<slug>`: `api-03/cancel-order`. The slug is 2 to 5 lowercase words joined by hyphens. Branch from the newest
`main` (after the packages this one depends on have merged). One package, one branch, one worktree.

## Commits

`<type>(<id-lowercase>): <summary>`, small and ordered. Types: `feat fix refactor perf test docs chore ci build`.
Summary in the imperative, at most 72 characters, no trailing period. Commit early and push: an agent that stops
(quota, crash) must have left its work on the remote.

## Pull request

Title = the squash commit line: `feat(api-03): add the cancel route`. Open it ready, to `main`, with the labels of the issue.

````markdown
## Summary

What the PR does and why, in one short paragraph and 3 to 6 bullets of what was added or changed.

## Files changed

- `path/one.rs` (new)
- `path/two.py`

## Done-when evidence

All commands ran from the repository root on commit `<sha>`.

### `<command 1>`

```
<the last lines of its output>
```

### `<command 2>`
...

Closes #<issue>
````

Rules:

- The files listed are exactly the files in the diff and a subset of the issue's *Owned files*. A file outside that list is a
  finding, not a favour.
- The evidence block is real: the commands from *Done when*, run on the head commit, with their output tails. A claim without
  output is not evidence.
- Problems found in the spec or the card go in the PR text under a line `Problems:`; the author does not edit the spec.
- The author **never merges**. A reviewer other than the author reads the diff and runs the commands again; the owner of the
  merge gate merges, by squash, after checks are green and the branch is not behind `main`. The verdict and fix format is
  [comments](comments.md).
- Delete the branch after the merge. Remove the worktree when its package is merged.

## Check

`package_lint.py branch`, `commit`, `pr` before each push and before `gh pr create`; afterwards
`gh pr view <n> --json title,headRefName,labels,mergeable,url`.
