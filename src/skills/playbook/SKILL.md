---
name: playbook
description: "Dispatcher for the three CTO pipelines. Use playbook-plan to plan a new feature, cross-file change or hard bug (it stops at the accepted plan), playbook-review to build an accepted plan or risky work with a reviewer PASS/FAIL fix loop and merge, and playbook-quick for a genuinely simple issue."
metadata:
  group: start
  summary: "Three playbooks: Plan, Review, Quick; pick by scope and risk"
---

# Playbook

There are **three** playbooks. Pick one; do not invent a fourth. All three use the `write-issue`, `write-comment` and `work-package`
formats and the `github` rules. `plan` decides **how** and ends at an accepted plan; `review` and `quick` end at the reviewer/gate
merge.

| Playbook | Use it for | Pipeline |
|---|---|---|
| **`playbook-plan`** | new feature, cross-file change, hard bug, a shape not yet settled | CTO card → architect plan comment → sent back to the CTO → accepts → **stop** |
| **`playbook-review`** | building an accepted plan; risky or money-path code, code the author did not write, likely errors | accepted plan → child cards → PRs → reviewer PASS/FAIL → fixes → re-review → merge |
| **`playbook-quick`** | docs, one-file fix, small test, mechanical change; **not** a new feature or cross-file work | CTO issue → developer PR → reviewer/gate merge, no plan |

```text
plan     problem ─► card ─► architect comment ─► back to CTO ─► accept ─► stop
review   accepted plan ─► dev(s) ─► PR ─► PASS/FAIL ─► fix ─► re-review ─► merge
quick    issue ─► dev ─► PR ─► reviewer/gate merge
```

## Pick in one minute

- Is a design decision, a boundary, a schema or a contract still open? Use **`plan`** first.
- Is there an accepted plan to build, or is the work risky, money-path, code you did not write, or likely to fail a
  review? Use **`review`** (which runs `plan` first when no accepted plan exists).
- Is it docs, one file, a small test or a mechanical fix that a competent developer can finish without planning? Use **`quick`**.
- If `quick` grows, stop and move the issue to `plan` or `review`; never merge a scope-grown quick card.

## Invariants

- The issue is the contract: `ID: title`, type + lane + difficulty labels, a priority, `Goal`, `Done when`.
- Every issue, comment and PR body ends with `Created: <agent name>`; every commit is authored by that name.
- The architect plans in one issue comment per plan version and sends it back; the CTO accepts in one comment.
- `plan` never continues into code. The developer does not merge.
- In `review` and `quick`, the verdict is `PASS`/`FAIL` at one full SHA. A new push needs a new one.
- Only the role the playbook names merges, never the author: after a PASS at the
  current SHA, with green required checks and no conflict.
- Comments are [evidence](../write-comment/SKILL.md), not chat; no secrets, no text interpolation into shell.
- One package, one worktree, one PR; clean the worktree and branch after merge.

## Roles

| Role | Skill | Does | Does not |
|---|---|---|---|
| CTO/CEO | the playbook + `manager` | writes the issues, sends them, accepts the plan | code, review, merge by author |
| Architect | `architect`, `planner` | analysis and plan comment, then the return to the CTO | code, merge, accept its own plan |
| Developer | `developer` + language skill | one package, test first, PR | merge, edit outside owned files |
| Reviewer/gate | `reviewer` | PASS/FAIL at SHA, merge gate | edit during review, self-approve a fix |
| Delegate | `delegate`, `orca-cli` | start the configured agent in a worktree | choose models outside the project table |
| Triage | `github`, `intake` | issues/comments/links | design or code |

## Reply

State the chosen playbook and the issue. For `plan`: the plan comment, the acceptance or what it waits for, and that
nothing was built. For `review` and `quick`: each PR, the verdict or decision with its SHA, and the merge result. Add any decision
waiting on the CTO.
If a pipeline stopped, say which gate stopped it and the one next action.
