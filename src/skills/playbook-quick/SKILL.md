---
name: playbook-quick
description: "The CTO pipeline for a genuinely simple change: CTO writes one simple work package, the developer implements it in one worktree and opens the PR, and the reviewer/gate checks the format, scope, checks and verify command and merges. No architect plan. Use for docs, a one-file fix, a small test or a mechanical change; not for new features or cross-file work."
metadata:
  group: start
  summary: "Quick pipeline: CTO issue, developer PR, reviewer merge gate, no planning"
---

# Playbook: Quick

The shortest safe pipeline. Use it only when the issue is already unambiguous and small: documentation, a one-file or
mechanical fix, a small test, a dependency-free cleanup. **No architect plan** is created. If the change needs a design
decision, more than one package, a new feature, a cross-file contract or a hard bug, stop and use `playbook-plan` or
`playbook-review`.

```text
CTO issue ─► developer ─► PR ─► reviewer/gate checks ─► merge
```

## 1. CTO: one simple package

Use the `work-package` skill. The issue must already have:

- `ID: outcome`, labels `lane`, `difficulty: simple`, and at least one area;
- `Goal`, `Read first`, `Owned files`, `Forbidden`, `Done when`, `Branch and PR`;
- a `Done when` command that a reviewer can run, and a file list with no shared hotspots.

Do **not** ask for a plan comment. If the issue lacks a runnable verify command or the file list is not closed, fix the
issue first; a missing plan is not the blocker.

**Stop and route elsewhere** when any is true:

| Signal | Go to |
|---|---|
| new user-visible behaviour, API, schema or route | `playbook-plan` |
| two or more packages, files shared with another open card, or a contract change | `playbook-plan` |
| a hard bug, race, money path or code the author did not write | `playbook-review` |
| the developer finds the work is bigger than `simple` | stop, comment the evidence, relabel; do not push on |

## 2. Developer: one worktree, one PR

Use the `developer` skill:

1. Branch from the newest `main` as `<id-lowercase>/<slug>`; work only in the owned files.
2. Test first when the change has code; otherwise run the card's existing check.
3. Run the card's `Done when` command on the committed head; clean the diff with `deslop`.
4. Commit with `<type>(<id-lowercase>): <summary>`, push, open the PR with the one
   [PR template](../work-package/assets/pr.template.md).
5. Comment the PR link on the issue. Do not merge.

## 3. Reviewer/gate: check and merge

The reviewer is a different model family from the author; it does not edit the branch. This is a **short gate**, not the
full review of `playbook-review`:

1. Read the issue and PR; check the title, labels, branch, `Closes #N`, owned files vs the diff and the PR size.
2. Run the card's exact verify command and inspect the required checks; confirm the docs/changelog exemption or entry.
3. Post `Verdict: PASS at <full sha>` or `Verdict: FAIL at <sha>` with evidence in the
   [comment format](../write-comment/references/other-comments.md).
4. On PASS, run the merge gate at that SHA ([the merge command](../github/references/pull-requests.md#merge), or the documented equivalent) with green
   checks and no conflict. On FAIL, send it back to the developer or use `playbook-review` if the finding is substantial.

After merge: confirm the issue closed, delete the branch, remove the worktree, and record the PR and verify output.

## Done

- The issue, PR and merge exist; the merged SHA passed the card's verify command.
- No plan was created; no branch/worktree/session remains.
- The change stayed inside the simple scope; a scope growth was routed to a planning playbook instead of merged.

## Never

- Use this for a new feature, a cross-file change, a schema/API contract or a hard bug.
- Skip the verify command because the diff is small.
- Merge with a red/absent required check, an open finding or a stale head.
- Let the developer merge its own PR.
