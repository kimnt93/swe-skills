---
name: playbook
description: "Dispatcher for the three CTO pipelines. Use playbook-plan for a new feature or cross-file change, playbook-review when the plan pipeline also needs a reviewer PASS/FAIL fix loop, and playbook-quick for a genuinely simple issue. All three use the work-package issue/PR format and end at the reviewer/gate merge."
metadata:
  group: start
  summary: "Three playbooks: Plan, Review, Quick; pick by scope and risk"
---

# Playbook

There are **three** playbooks. Pick one; do not invent a fourth. All three use the `work-package` issue and PR format, the
`github` rules and the reviewer/gate merge. The CTO owns the issue and acceptance; the developer owns the PR; the reviewer
owns the verdict and the merge gate.

| Playbook | Use it for | Pipeline |
|---|---|---|
| **`playbook-plan`** | new feature, cross-file change, hard bug, a shape not yet settled | CTO issue → architect plan comment → CTO accepts → delegated PRs → reviewer/gate merge |
| **`playbook-review`** | the plan pipeline plus an independent review round; risky or money-path code, code the author did not write, likely errors | plan pipeline → reviewer PASS/FAIL → author fixes → re-review → merge |
| **`playbook-quick`** | docs, one-file fix, small test, mechanical change; **not** a new feature or cross-file work | CTO issue → developer PR → reviewer/gate merge, no plan |

```text
plan     issue ─► plan comment ─► CTO accept ─► dev(s) ─► PR ─► reviewer/gate merge
review   plan pipeline ─► PASS/FAIL ─► fix ─► re-review ─► merge
quick    issue ─► dev ─► PR ─► reviewer/gate merge
```

## Pick in one minute

- Does the issue need a design decision, more than one package, a shared file or a new contract? Use **`plan`**.
- Is it risky, money-path, code you did not write, or likely to fail a review? Use **`review`** (which includes the plan).
- Is it docs, one file, a small test or a mechanical fix that a competent developer can finish without planning? Use **`quick`**.
- If `quick` grows, stop and move the issue to `plan` or `review`; never merge a scope-grown quick card.

## Invariants

- The issue is the contract: `ID: title`, lane + difficulty + area labels, `Goal`, owned files, `Done when`.
- The architect plans in one issue comment; the CTO accepts in one comment; the developer does not merge.
- The review verdict is `PASS`/`FAIL` at one full SHA; a new push needs a new verdict.
- The reviewer/gate merges only after a PASS at the current SHA, green required checks and no conflict.
- Comments are [evidence](../work-package/references/comments.md), not chat; no secrets, no text interpolation into shell.
- One package, one worktree, one PR; clean the worktree and branch after merge.

## Roles

| Role | Skill | Does | Does not |
|---|---|---|---|
| CTO | the playbook + `manager` | writes/accepts the package, accepts the plan, routes and merges decisions | code, review, merge by author |
| Architect | `architect`, `planner` | plan comment, packages/waves, contracts | code, merge |
| Developer | `developer` + language skill | one package, test first, PR | merge, edit outside owned files |
| Reviewer/gate | `reviewer` | PASS/FAIL at SHA, merge gate | edit during review, self-approve a fix |
| Delegate | `delegate`, `orca-cli` | start the configured agent in a worktree | choose models outside the project table |
| Triage | `github`, `intake` | issues/comments/links | design or code |

## Reply

State the chosen playbook, the issue/PR, the reviewer verdict and SHA, the merge result, and any decision waiting on the CTO.
If a pipeline stopped, say which gate stopped it and the one next action.
