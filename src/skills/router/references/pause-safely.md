### Pause safely

**Stop so that someone else can resume without guessing.**

1. Finish or revert the unit in progress; never leave a half-applied migration or a red branch
   without saying so.
2. Commit work in progress on its branch with a `wip:` commit, and push it (never to `main`).
3. Write the handoff where the next agent will look (the PR body, the card comment): the goal, the
   done-predicate, what is proven, what is not, the next step, and any running process to stop.
4. Stop processes you started (dev servers, compose stacks, port-forwards) unless the handoff says
   they must stay up.

**Reply:** the handoff text and its location.
