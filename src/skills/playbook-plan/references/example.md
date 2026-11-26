# Example: from a problem to an accepted plan

A complete run for one problem: "users cannot export the orders they filtered". The project, files and names are made
up; the shape is what to copy. `ORCA` is as in [orchestration](orchestration.md).

| # | Who | What | File |
|---|---|---|---|
| 1 | CTO/CEO | writes the planning card and creates the issue | [card](../assets/example/card.md) |
| 2 | CTO/CEO | sends the brief to the architect, ends the turn | [brief](../assets/example/architect-brief.md) |
| 3 | Architect | analyses and posts one plan comment on the issue | [plan comment](../assets/example/plan-comment.md) |
| 4 | Architect | sends the result back to the CTO/CEO | [return report](../assets/example/return-report.md) |
| 5 | CTO/CEO | reads the comment, answers the open questions, accepts, **stops** | [acceptance](../assets/example/acceptance.md) |

## The issue afterwards

```text
Issue #42  EXPORT-00: Export the filtered order list as CSV          labels: enhancement, backend, medium, orders
  body       planning card (CTO)
  comment 1  Architecture & Planning      Created: Architect (example)
  comment 2  Accepted by CTO              Created: CTO (example)
  state      open; no branch, no PR
```

## Commands, in order

```bash
# 1. CTO/CEO
AGENT_NAME="CTO (example)" python3 <work-package skill>/scripts/package_lint.py issue --kind planning \
    --title "EXPORT-00: Export the filtered order list as CSV" \
    --label enhancement --label backend --label medium --label orders --body-file card.md
gh issue create --repo <owner>/<repo> --title "EXPORT-00: Export the filtered order list as CSV" \
    --label enhancement --label backend --label medium --label orders --body-file card.md

# 2. CTO/CEO
ORCA bot list
ORCA bot chats                     # note the id on the "(this chat)" line and put it in the brief
ORCA orchestration send --to "bot:<architect>" --type question \
    --subject "PLAN EXPORT-00: export the filtered order list" --body-file brief.md

# 3. Architect
python3 <work-package skill>/scripts/package_lint.py comment --kind plan --body-file plan.md
gh issue comment 42 --repo <owner>/<repo> --body-file plan.md

# 4. Architect: answer the question it was sent
ORCA orchestration reply --id <msg_id> --body-file report.md

# 5. CTO/CEO
gh issue view 42 --repo <owner>/<repo> --comments
python3 <work-package skill>/scripts/package_lint.py comment --kind decision --body-file acceptance.md
gh issue comment 42 --repo <owner>/<repo> --body-file acceptance.md
```

## The same run with a worker

Only steps 2 and 4 change: `ORCA orchestration worker-start --spec-file brief.md --agent <agent> --worktree current`,
and the architect reports with `worker_done` as its dispatch preamble says.

## A parent issue (epic)

The same steps with the [epic](../../write-issue/assets/example/epic.md) and the
[epic plan](../../write-comment/assets/example/epic-plan.md): `--kind epic`, then `comment --kind epic-plan`.
