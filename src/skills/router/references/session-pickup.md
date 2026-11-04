### Session pickup

**Take over someone else's (or your own earlier) work without trusting its claims.**

1. Find the trail: the branch, its PR, the issue and its comments, the run's reports, the last session's
   transcript for this workspace (see the [harness](harness.md) reference).
2. Rebuild the goal and the done-predicate from the original request, not from the last summary.
3. Check the real state: `git status`, `git log origin/main..HEAD`, `gh pr checks`, `make verify`.
4. Re-verify every "done" claim against the predicate (the **prove-it-works** principle).
5. Continue from the first unit that is not proven.

**Reply:** the goal, what is proven, what is not, the next step.
