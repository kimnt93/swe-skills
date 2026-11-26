# Branch, commits, pull request

## Branch

`<id-lowercase>/<slug>`: `api-03/cancel-order`. The slug is 2 to 5 lowercase words joined by hyphens. Branch from the newest
`main` (after the packages this one depends on have merged). One package, one branch, one worktree.

## Commits

`<type>(<id-lowercase>): <summary>`, small and ordered. Types: `feat fix refactor perf test docs chore ci build`.
Summary in the imperative, at most 72 characters, no trailing period. Commit with the `github` skill's `agent_identity.py git` so your agent name is the author and committer. Commit early and push: an agent that stops
(quota, crash) must have left its work on the remote.

## Pull request

Title, shaped like a commit subject: `feat(api-03): add the cancel route`. Open it ready, to `main`, with the labels of the
issue. The body is the one [PR template](../assets/pr.template.md), the same for every pull request
([templates](../../write-issue/references/templates.md)).

Rules:

- The diff stays inside the issue's *Owned files*; a file outside that list is a finding, not a favour (say why under
  `## Scope` if the issue's owner allowed it).
- `## Verification` is real: the *Done when* commands, run on the head, with their results. A claim without a command is
  not evidence. The full output goes in the PR comment that judges the head.
- Problems found in the spec or the card go under `## Scope`; the author does not edit the spec.
- The author **never merges**. Someone other than the author reads the diff and runs the commands again (`playbook-quick`: the
  CTO/CEO; `playbook-complete` and `playbook-ship`: the reviewer); the role the playbook names merges, by rebase, after checks are green and the branch
  is not behind `main`. Their comments use the one [PR comment](../../write-comment/references/other-comments.md).
- Delete the branch after the merge. Remove the worktree when its package is merged.

## Check

`package_lint.py branch`, `commit`, `pr` before each push and before `gh pr create`; afterwards
`gh pr view <n> --json title,headRefName,labels,mergeable,url`.
