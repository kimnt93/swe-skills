### Babysit

**Get a PR to merge-ready. Never merge.**

1. Declare the mode: `drive` (loop until merge-ready), `check` (one status pass), or `threads`
   (answer review comments only).
2. Work the lowest unmerged PR of a stack only. Fixes for PRs higher in the stack wait.
3. In order:
   1. **conflicts**: report which branch needs a rebase; the PR's owner rebases;
   2. **review threads**: verify each claim against the code, fix real ones with a failing test
      first, reply to the rest with the concrete reason;
   3. **CI**: read the failing job's log (`gh pr checks <pr>`, `gh run view <id> --log-failed`).
4. Classify CI failures before re-running: a failure in code the diff doesn't touch is a stale base
   (`git merge-base --is-ancestor origin/main HEAD`); a flake earns one re-run (`gh run rerun --failed`);
   a second identical failure is real.
5. Batch every fix into one push. Re-check after each push.
6. Stop at merge-ready: required checks green, threads resolved, approvals present. Merging is the
   human's call, or `fleet merge` on the board.

**Reply:** the PR, its state, what you fixed, what waits on a human.
