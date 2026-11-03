---
name: fleet-worker
description: "How a lane profile (claude or omp) works a kanban card with the @PLUGIN@ plugin: implement it through `fleet lane run` and hand it to the other lane for review, or, in the review lane, review it through `fleet lane review`, give a verdict for one head SHA and, when autopilot allows the card's risk class, merge through `fleet merge`. Use whenever you are a lane profile working a kanban card."
metadata:
---

# Fleet worker

You drive a coding CLI through `fleet lane`. The CLI works with the `@PLUGIN@` plugin.
**You never edit code yourself.** Your lane is your profile name (`claude` or `omp`); the other
lane is the other one.

Start with `kanban_show`. Write the card body to `.fleet/card.md` in the workspace. Read
`issue:`, `risk:`, `tier:` and `may write:` from it (defaults: `standard`, `mid`). Git and GitHub work
follows the `github` skill: the card's branch is `<type>/<issue>-<slug>`; the repo is the project's
(`gh repo view --json nameWithOwner`).

## Implement (the card is ready or running, not in review)

1. Run `fleet lane run <your lane> <tier> .fleet/card.md`. It can take up to 90 minutes. Wait for it.
2. Read `.fleet/evidence.json`.
3. If `verify_exit` is 0, `uncommitted` is empty and `commits` is not empty:
   - write the PR body (`.fleet/pr.md`: Why, What changed, Scope, Blast radius, Verification with the
     `verify_tail`, and `Closes #<issue>`), run `pr_lint.py local --body .fleet/pr.md --allow '<may write>'`
     until it reports 0 problems, push the branch, open the PR (`gh pr create --body-file .fleet/pr.md`
     with labels `risk:*` and `lane:*`), and run `pr_lint.py pr <number>`;
   - call `kanban_request_review` with `reviewer` = the other lane, and `metadata` = the evidence
     plus `published_pr` and `risk`.
4. Otherwise call `kanban_block` with the reason and the last 40 lines of `verify_tail`. If the
   agent made no commits, say so.

## Review (you were spawned in the review lane)

The `sdlc-review` skill is also loaded. Follow its lifecycle; this section says how to gather
the evidence.

1. Check out the PR head and record its SHA.
2. Run `fleet lane review <author lane> .fleet/card.md`. The author lane is the other lane.
3. Read `.fleet/review.json`:
   - `verify_exit` is not 0: request changes with the verify tail.
   - `reviewer_edited_files` is true: discard the edits (`git checkout -- . && git clean -fd`),
     treat the review as failed, and run it once more.
   - For each finding in `report`, re-run its command yourself. Keep it only if the output
     reproduces the failure and breaks the card's goal.
4. Verdict for that SHA only:
   - Kept findings: `kanban_request_changes` with each finding's command and output.
   - Also check the submit rules: `pr_lint.py pr <number>`; its problems are findings.
   - Post the verdict on the PR: `gh pr review <n> --comment --body-file .fleet/verdict.md`, first line
     `Verdict: PASS at <sha>` or `Verdict: CHANGES at <sha>`.
   - No kept findings and verify passed: run
     `fleet merge <pr> --repo <owner>/<repo> --risk <risk> --sha <sha>`.
     - Exit 0 (merge armed) or exit 3 (`REFUSED`: autopilot doesn't cover this risk class, or
       checks aren't green yet): either way, call `kanban_complete` with `metadata.published_pr`,
       the head SHA, and the `fleet merge` output. A refused merge waits for the human.
     - Any other exit: `kanban_block` with the output.
   - A new push after your verdict needs a new review.

## Never

Push to main. Merge by hand (only `fleet merge` merges; without the human's approval it refuses
money-path and any risk autopilot doesn't cover). Approve a SHA you did not verify. Change files
outside the card's `may write`, or breach the project's `ARCHITECTURE.md`. Put secrets or raw logs beyond the tails in metadata.
