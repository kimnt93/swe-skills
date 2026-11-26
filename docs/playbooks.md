# Playbooks

There are **three CTO pipelines**. They all use the `work-package` formats and the `github` rules. **Plan** decides how
and ends at an accepted plan; **Review** and **Quick** end at the reviewer/gate merge. None lets
the author merge.

| Shortcut | Pipeline | Use it for | Inputs |
|---|---|---|---|
| `/swe:playbook-plan` | **Plan** | new feature, cross-file change, hard bug, a shape not yet settled | a problem or an `issue` |
| `/swe:playbook-review` | **Review** | building an accepted plan with an independent PASS/FAIL review and fix round; risky or money-path work, code the author did not write | an accepted plan or an `issue` |
| `/swe:playbook-quick` | **Quick** | docs, one-file fix, small test, mechanical change; **no** new feature or cross-file work | `issue` or `goal` |

`/swe:playbook` lists the three. There is no other playbook.

## DAGs

```text
Plan     problem ─► CTO/CEO card ─► architect (bot or worker) ─► plan comment ─► back to CTO/CEO ─► accept ─► STOP
Review   accepted plan ─► child cards ─► dev(s) ─► PR ─► reviewer PASS/FAIL ─► fixes ─► re-review ─► merge
Quick    CTO issue ─► dev ─► PR ─► reviewer/gate merge
```

The Plan messages travel through Orca orchestration. The
[commands](../src/skills/playbook-plan/references/orchestration.md) and a
[complete example](../src/skills/playbook-plan/references/example.md) (card, brief, plan comment, return, acceptance)
ship with the skill.

## The gates

| Gate | Owner | Passes when |
|---|---|---|
| Card ready (Plan) | CTO/CEO | a `planning` or `epic` issue that passes `package_lint.py issue` |
| Plan returned | architect | one plan comment per version, sent back to the CTO/CEO with its URL |
| Issue ready (build) | CTO | `ID: title`, type + lane + difficulty labels, priority, closed file list, runnable `Done when` |
| Plan accepted | CTO/CEO | the `plan` or `epic-plan` comment passes the linter, every open question is answered, and the decision comment is posted. **Plan ends here** |
| PR ready | developer | owned files only, test first, `Closes #N`, evidence from the card's verify command on the committed head |
| Review (`review`) | reviewer (different family) | `Verdict: PASS at <full sha>` and no open finding; a new push needs a new verdict |
| Merge | reviewer/gate | the checked SHA is the head, green required checks, branch not behind `main`; `gh pr merge --match-head-commit` or the project's documented gate |

Issues are written with [`write-issue`](../src/skills/write-issue/SKILL.md) (kinds and the
[catalog](../src/skills/write-issue/references/catalog.md)); plan, decision, verdict, fix and close comments with
[`write-comment`](../src/skills/write-comment/SKILL.md). Each ends with `Created: <agent name>`, and commits are authored
by that name ([identity](../src/skills/github/references/identity.md)).

All templates, and how to change their style: [templates](../src/skills/write-issue/references/templates.md).

## Rules

- A build is one package, one issue, one worktree, one branch, one PR, one owner.
- The CTO does not code; the developer does not merge; the reviewer does not edit during review. - In `review`, the default fixer is the author; if the CTO assigns the reviewer as fixer, a different reviewer or the CTO
  posts the PASS for the new SHA. Never self-approve.
- A `quick` card that grows to a new feature, a shared file or a contract change stops and becomes `plan` or `review`.
- Plans and verdicts are comments, not new issues. A plan that creates packages also creates their issues and links them.
- A merge is not done until the issue is closed, the branch deleted and the worktree removed.

## What happened to the old playbooks

The old `playbook-deliver`, `playbook-feature`, `playbook-bugfix`, `playbook-review` (review-only), `playbook-cifix`,
`playbook-docs`, `playbook-rebase`, `playbook-land`, `playbook-changelog`, `playbook-verify` and `playbook-solo` are
removed. Their useful methods live in the skills they named (`github`, `tdd`, `docs-sync`, `ci-fixer`, `integrator`,
`changelog`, `verifier`, `reviewer`, `delegate`); they are no longer separate CTO pipelines.
