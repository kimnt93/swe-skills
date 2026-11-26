---
name: playbook-plan
description: "The planning pipeline for new features, cross-file changes and hard bugs: the CTO/CEO turns a problem into a planning card (an issue) on the repository and sends it through orchestration to the architect (a bot or a delegated worker); the architect analyses, compares approaches, recommends a design and stack, and comments it on the issue; the architect sends the result back to the CTO/CEO, who accepts it or asks for changes. It stops at acceptance: no code, no branch, no PR. Use when asked to plan, design or analyse a problem before anyone builds it."
metadata:
  group: start
  summary: "Plan only: CTO card, architect analysis comment, back to the CTO to accept, then stop"
---

# Playbook: Plan

A problem goes in; an **accepted plan on the issue** comes out. Then **stop**. This playbook writes no code, creates no
implementation branch, opens no PR and merges nothing.

```text
problem ─► CTO/CEO: planning card (issue) ─► send to architect (bot or delegate)
                                                   │ analyse, approaches, recommendation, stack, implementation
                                                   ▼
        STOP ◄─ CTO/CEO: accept ◄─ architect sends back ◄─ ONE plan comment on the issue
                     └─ changes required ─► architect posts plan v2 ─► sends back again
```

This skill gives the **workflow**. How to send, delegate and watch is in [orchestration](references/orchestration.md),
which uses the Orca `/orchestration` skill; load that skill before the first send. For a delegated agent outside Orca, use
the `delegate` skill. A complete run, from the problem to the acceptance, is in [the example](references/example.md).

## Roles

| Role | Does | Does not |
|---|---|---|
| **CTO/CEO** (owns the problem and the decision) | writes the card, sends it, reads the plan, accepts or asks for changes | design in place of the architect, code |
| **Architect** (the planner; a standing bot or a delegated worker) | analyses, recommends, comments on the issue, **sends the result back** | accept its own plan, edit tracked code, create a branch or PR, start developers |

All comments may appear under one repository account, so each issue and comment ends with `Created: <agent name>`.

## 1. CTO/CEO: turn the problem into a card

Use the `write-issue` skill on the repository that owns the problem: a `planning` card (`<AREA>-<NN>`) for one outcome,
or an `epic` (`<AREA>-00`) for an initiative with children. It states the problem and the outcome, not the design.
Create it, read back what was stored, and keep its number.

An existing issue is used if it passes `package_lint.py issue --kind planning` (or `epic`); otherwise fix its fields
before sending it.

## 2. CTO/CEO: send it to the architect

Pick the architect: a standing bot for this project if one exists, otherwise a delegated worker. Send a brief in the
[brief format](assets/example/architect-brief.md): the issue URL, what to answer, the limits, and **the return address**
(who gets the result, and which chat). Then **end your turn**; the result comes to you. Commands:
[send the card](references/orchestration.md#2-send-the-card-to-the-architect).

## 3. Architect: analyse and comment on the issue

Use the `write-comment` skill: [analyse the code first](../write-comment/references/plan.md#analyse-the-code-first),
then post **one** comment on the issue, signed `Created: <your agent name>`. You write no plan file and open no
implementation issues.

| Card | Comment kind | Template |
|---|---|---|
| planning card | `plan` | [plan.template.md](../write-comment/assets/plan.template.md) |
| epic | `epic-plan` | [epic-plan.template.md](../write-comment/assets/epic-plan.template.md) |

On an epic, the table names the child issues the CTO/CEO has created; a child that does not exist yet is listed by ID.

```bash
AGENT_NAME="<agent name>" python3 <work-package skill>/scripts/package_lint.py comment --kind plan --body-file plan.md
gh issue comment <n> --repo <owner>/<repo> --body-file plan.md      # prints the comment URL
```

The plan is complete when a developer could start every package without asking a design question.

## 4. Architect: send it back to the CTO/CEO

**Posting the comment is not the end of your job.** Send the [return report](assets/example/return-report.md) to the
return address in the brief: the verdict line (`PLAN READY` or `PLAN BLOCKED`), the comment URL, the recommendation, and
the decisions waiting. How: [send it back](references/orchestration.md#3-send-the-plan-back). Then end your turn.

If the card is not ready (no observable outcome, missing access, a contradiction), comment what is missing and send back
`PLAN BLOCKED` with that one need. Never guess a requirement, and never stay silent.

## 5. CTO/CEO: confirm, then stop

Read the **comment on the issue**, not only the report. Check it against the card: the `Goal` is met, every scope line is
covered or explicitly dropped, the rejected approach is a real one, every open question has an answer, and each gate is a
command. Post **one** `decision` comment ([format](../write-comment/references/other-comments.md#decision-ctoceo)):

- **`Accepted by CTO (<name>).`** the plan version, the answers to the open questions, and what happens to the packages
  (build now or backlog). A decision the human has not delegated to you goes to the human first.
- **`Changes required by CTO (<name>):`** concrete changes only. Send them to the same architect; it posts a new comment (`Plan v2`),
  leaves the old one, and sends it back. Repeat from step 4.

**Stop here.** Report the issue URL, the accepted comment and the decisions. The issue stays open. Do not create child
cards, start a developer or open a worktree for the build. Building is a separate request: `playbook-review` takes the
accepted plan.

## State: read it from the issue

| On the issue | The next step |
|---|---|
| a card, no plan comment | send it (step 2), or the architect is still working |
| a plan comment, no CTO comment | the CTO/CEO confirms (step 5) |
| `Changes required by` as the latest decision | the architect revises (steps 3 and 4) |
| `Accepted by` for the latest plan version | done: nothing left in this playbook |

## One good, one bad

- **Good:** the architect comments the plan, then sends `PLAN READY` with the comment URL and two decisions to the CTO's
  chat. The CTO answers both in one acceptance comment and stops.
- **Bad:** the architect comments and ends silently, so the CTO never knows. Or the CTO accepts and, in the same run,
  starts developers: that is no longer this playbook.

## Done

- The card is on the repository; the card, the plan and the decision pass the linter and are signed.
- One plan comment per plan version is on the issue; the architect sent each one back.
- The CTO/CEO accepted the latest version in one comment. No branch, PR or implementation worker was created.

## Never

- Plan only in a chat or a local file: the issue is the record.
- Let the architect end without sending back, or accept its own plan.
- Continue into implementation after the acceptance.
- Paste issue or comment text into a shell command, or a secret into an issue, comment or message.
