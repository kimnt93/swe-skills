# The other comments

Every comment ends with `Created: <author>`, and none carries a "Generated with" footer.

## Comments on a pull request: one style

A verdict, a CTO/CEO decision on a PR, a fix and a merge all use **one** template,
[pr-comment.template.md](../assets/pr-comment.template.md): the headline, one or two sentences, then **Blocking** (only
when something fails), **Verified** (when it passes), **Gate** (commands and their output on that head) and
**Residual** (open notes, or `none`). See a [PASS](../assets/example/verdict-pass.md) and a
[FAIL](../assets/example/verdict-fail.md).

Only the headline and which sections apply differ:

## verdict (reviewer, on the PR)

`Verdict: PASS at <40-character sha>` or `Verdict: FAIL at <40-character sha>`; in a fix loop (`playbook-ship`,
`playbook-complete`) a FAIL ends `. Round <k> of 3.`, and the loop's end is `Stopped by reviewer (<name>). PR #<n> at
<sha>.` PASS: Verified, Gate, Residual. FAIL:
one Blocking section per finding, Gate, Residual (Verified for what did pass). There is no `CHANGES` verdict. A finding
without a command and its output is dropped. A verdict is never carried to a new SHA or posted by the author on their
own work.

## decision (CTO/CEO)

On a PR it covers one head SHA and names it, and uses the template like a verdict:

- `Accepted by CTO (<name>). PR #<n> at <40-character sha>.` (as PASS)
- `Changes required by CTO (<name>). PR #<n> at <40-character sha>. Round <k> of 3.` (as FAIL)
- `Stopped by CTO (<name>). PR #<n> at <40-character sha>.` (as FAIL): the feedback limit is reached; the final feedback

On a plan (an issue) it is short, and covers one plan version:

```text
Accepted by CTO (<name>). Plan v1. <what happens now: build wave 1 (IDs) with <owner>, or stays in the backlog>.
- <answer to each open question>

Created: <author>
```

or `Changes required by CTO (<name>):` with one concrete change per line. `CEO` replaces `CTO` when the CEO decides.

## fix (whoever the playbook names as fixer, on the same PR)

`Fixed in <sha>:`, one line per finding fixed, `New head: <sha>. Please re-review.`, then Gate and Residual. A reviewer
edits the branch only where the playbook names it as fixer (the
[fix loop](../../reviewer/references/fix-loop.md)); its PASS then names every commit it pushed.

## merge (whoever the playbook names)

`Merged by <who> at <sha> after PASS.` (`playbook-quick`: `after acceptance.`), what happened after (issue closed, branch
deleted, changelog), then Gate (the required checks and their state) and Residual.

## Comments on an issue

### status (progress or blocker)

```text
Status: <started|blocked|done>
Card: <ID>
Evidence: <PR link, commit, command output tail>
Next: <the one next action, or none>

Created: <author>
```

A blocker says what is needed and who owns it.

### close

`Closed: <the outcome and the link that proves it>`, or `Replaced by #<n>` with one line on why; then the signature.

### reply

An answer to a question or a review thread: the answer first, then the evidence, then the signature.
