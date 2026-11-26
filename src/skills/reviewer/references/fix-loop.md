# The review and fix loop

For `playbook-build` and `playbook-ship`: **the reviewer reviews, fixes what it found, and passes the result.**
Nobody else checks the reviewer's own fixes before they reach `main`. That is why the limits here are strict and the PASS
names every commit the reviewer pushed.

```text
review head ─► no finding ─────────────────────────────► Verdict: PASS (names your commits)
     ▲    └─► findings, rounds left ─► Verdict: FAIL Round k of 3 ─► fix ─► push ─► fix comment ─┐
     └───────────────────────────────────────────────────────────────────────────────────────────┘
          └─► findings after round 3, or a stop reason ─► Stopped by reviewer
```

## Before the first review

All must hold; if one does not, change nothing and report it:

- `issue_gate.py pr <n> --repo <owner>/<repo>` (the `github` skill) allows it. Never fix work for an issue that is done,
  not planned, duplicate or not approved.
- You wrote none of the pull request.
- Its code is [safe to run](../SKILL.md#before-you-run-anything-from-it), so it is on a branch of this repository.
- Nobody else is working on the branch: its developer has handed it over, and no worktree of another agent is changing
  it (`ORCA worktree ps`).

**Your own worktree**, on your own local branch that tracks the PR's branch:

```bash
git fetch origin <pr branch>
ORCA worktree create --repo <repo> --name review-pr-<n> --branch review/pr-<n> --base-branch origin/<pr branch>
# outside Orca: git worktree add -b review/pr-<n> <dir> origin/<pr branch>
```

## Each turn

1. Where the loop stands: `python3 <github skill>/scripts/pr_loop.py state --pr <n> --repo <owner>/<repo>`.
2. [Review](../SKILL.md#steps) the whole head, your earlier fixes included.
3. **No finding:** post the PASS ([below](#the-pass)).
4. **Findings, rounds left:** post `Verdict: FAIL at <sha>. Round <k> of 3.` **before** you change anything, with every
   finding you have. Check it first: `pr_loop.py decide --pr <n> --repo <owner>/<repo> --body-file verdict.md`.
5. Fix: a failing test first when there is code, then the smallest change. Commit under your name
   (`agent_identity.py git --author "<you>" -- commit ...`), run the issue's `Done when` on that commit, then
   `git push origin HEAD:<pr branch>`.
6. Post the `fix` comment (`Fixed in <sha>:`, one line per finding, `New head:`) and go to 1.

**At most 3 rounds**, so at most 3 fixes and 4 reviews. The count includes any earlier `Changes required` decision on
this PR, and never resets.

## What a fix may touch

- Only the findings you posted, in the files the issue owns.
- **Never make your own check easier:** do not delete, skip or weaken a test, check or lint rule to get a PASS. If a test
  is itself wrong, say so as a finding, and keep it testing the goal.
- Never edit the issue, widen the scope or add a dependency the issue does not allow.

## Stop at once

Post `Stopped` without using more rounds when a fix needs a file outside the owned list, a design decision or a changed
goal; when you cannot push; when a linked issue becomes done, not planned or duplicate; or when someone else pushes to
the branch while you work.

## Behind `main`

`python3 <github skill>/scripts/agent_identity.py git --author "<you>" -- rebase origin/main`, then
`git push --force-with-lease=<pr branch>:<old head> origin HEAD:<pr branch>`. Allowed only because the branch was handed
to you. A rebase keeps each commit's author. It is not a round, and **the new head needs a new verdict**. A conflict
follows the `integrator` skill; one outside the owned files is a stop.

## The PASS

`Verdict: PASS at <40-character sha>` with Verified, Gate and Residual. If you pushed any commit, `Residual` **names each
one** by its short SHA, so whoever relies on your verdict sees what had a single pair of eyes:

```text
## Residual
- pushed by the reviewer and checked by nobody else: 4f2c9a1, 9b8a7c6
```

`pr_loop.py decide` refuses a PASS that leaves one out, or that the pull request's writer signed. With `pr_lint.py`, add
`--also-author "<you>"`.

## Stopped

`Stopped by reviewer (<name>). PR #<n> at <40-character sha>.` is the final feedback: one `Blocking` section per thing
still wrong with its smallest fix, the `Gate` output, and under `Residual` what a person has to decide. Then post
`Status: blocked` on the issue with the link. **The PR stays open, its branch stays on GitHub, the issue stays open.**
Restarting is the human's decision. Push anything left, then
[remove your worktree](#remove-your-worktree).

## Remove your worktree

After a confirmed merge or a `Stopped`:

```bash
python3 <github skill>/scripts/pr_loop.py can-remove --worktree <path> --pr <n> --repo <owner>/<repo>
ORCA worktree rm --worktree path:<path>          # outside Orca: git worktree remove <path>
```

Refused: keep it and fix the reason. Never `--force` or `--delete-branch`. A worker running inside the worktree reports
first and removes it as its last command.
