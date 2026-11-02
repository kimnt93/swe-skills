# Backlog

- **One issue per unit of work, one card per issue.** The card body carries `issue: #N`; the branch is
  `<type>/N-<slug>`; the PR says `Closes #N`.
- **Labels mirror the card:** `type:*`, `risk:*`, `tier:*`, `lane:*`. The manager sets them when it
  creates the card (the `github` skill's issues reference has the commands).
- **Milestones** group issues for a release or a goal; a goal from the human becomes a milestone with
  its issues.
- **Triage** (daily, or when the root profile routes a request): dedupe against open issues
  (`gh issue list --search "<words>"`), ask for the missing acceptance criteria only if no experiment
  can settle them, then create the issue and its card.
- **Blocked:** label `blocked`, a comment with the reason, the card blocked with the same reason.
- **Done:** the PR merged closes the issue; the manager checks the acceptance against the merged
  `main` before closing the card's parent goal.
