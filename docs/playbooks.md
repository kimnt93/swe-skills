# Playbooks

There are **three CTO pipelines**. They all use the `work-package` formats and the `github` rules. **Plan** decides how
and ends at an accepted plan; **Review** ends at the reviewer/gate merge and **Quick** at the CTO/CEO's merge. None lets
the author merge.

| Shortcut | Pipeline | Use it for | Inputs |
|---|---|---|---|
| `/swe:playbook-plan` | **Plan** | new feature, cross-file change, hard bug, a shape not yet settled | a problem or an `issue` |
| `/swe:playbook-review` | **Review** | building an accepted plan with an independent PASS/FAIL review and fix round; risky or money-path work, code the author did not write | an accepted plan or an `issue` |
| `/swe:playbook-quick` | **Quick** | ready to build with no design question; one problem may be several issues | a problem or `issue`s |

`/swe:playbook` lists the three. There is no other playbook.

## DAGs

```text
Plan     problem ─► CTO/CEO card ─► architect (bot or worker) ─► plan comment ─► back to CTO/CEO ─► accept ─► STOP
Review   accepted plan ─► child cards ─► dev(s) ─► PR ─► reviewer PASS/FAIL ─► fixes ─► re-review ─► merge
Quick    problem ─► CTO/CEO issue(s) ─► dev worktree ─► PR ⇄ CTO/CEO (≤3 rounds) ─► merge + confirm ─► remove worktree
                                                          └─ still wrong ─► Stopped ─► remove worktree (PR and branch stay)
```

The Plan messages travel through Orca orchestration. The
[commands](../src/skills/playbook-plan/references/orchestration.md) and a
[complete example](../src/skills/playbook-plan/references/example.md) (card, brief, plan comment, return, acceptance)
ship with the skill.

Quick ships its own [commands](../src/skills/playbook-quick/references/orchestration.md) and a
[complete example](../src/skills/playbook-quick/references/example.md): one problem, two issues, one round of feedback,
merged.

## The gates

| Gate | Owner | Passes when |
|---|---|---|
| Card ready (Plan) | CTO/CEO | a `planning` or `epic` issue that passes `package_lint.py issue` |
| Plan returned | architect | one plan comment per version, sent back to the CTO/CEO with its URL |
| Issue ready (build) | CTO | `ID: title`, type + lane + difficulty labels, priority, closed file list, runnable `Done when` |
| Plan accepted | CTO/CEO | the `plan` or `epic-plan` comment passes the linter, every open question is answered, and the decision comment is posted. **Plan ends here** |
| PR ready | developer | owned files only, test first, `Closes #N`, evidence from the card's verify command on the committed head |
| Review (`review`) | reviewer (different family) | `Verdict: PASS at <full sha>` and no open finding; a new push needs a new verdict |
| PR returned (`quick`) | developer | `PR READY` or `PR BLOCKED` sent back with the PR URL and head SHA |
| Accepted (`quick`) | CTO/CEO | checked at the head: lint, checks, diff, `Done when`; the decision names the SHA |
| Feedback limit (`quick`) | CTO/CEO | at most 3 `Changes required` rounds, then accept or `Stopped by`; `quick_loop.py decide` refuses a fourth |
| Worktree removed (`quick`) | developer | after the confirmed merge or the stop; `quick_loop.py can-remove` allows it only when nothing is lost |
| Merge | reviewer/gate (`review`) or CTO/CEO (`quick`) | the checked SHA is the head, green required checks, branch not behind `main`; `gh pr merge --match-head-commit` or the project's documented gate |

Issues are written with [`write-issue`](../src/skills/write-issue/SKILL.md) (kinds and the
[catalog](../src/skills/write-issue/references/catalog.md)); plan, decision, verdict, fix and close comments with
[`write-comment`](../src/skills/write-comment/SKILL.md). Each ends with `Created: <agent name>`, and commits are authored
by that name ([identity](../src/skills/github/references/identity.md)).

All templates, and how to change their style: [templates](../src/skills/write-issue/references/templates.md).

## Rules

- A build is one package, one issue, one worktree, one branch, one PR, one owner.
- The CTO does not code; the developer does not merge; the reviewer does not edit during review. In `quick` the CTO/CEO
  merges, unless the project reserves the merge for a person.
- In `review`, the default fixer is the author; if the CTO assigns the reviewer as fixer, a different reviewer or the CTO
  posts the PASS for the new SHA. Never self-approve.
- A `quick` issue that turns out to need a design decision or hard work stops and becomes `plan` or `review`.
- Plans and verdicts are comments, not new issues. A plan that creates packages also creates their issues and links them.
- A merge is not done until the issue is closed, the branch deleted and the worktree removed.

## What happened to the old playbooks

The old `playbook-deliver`, `playbook-feature`, `playbook-bugfix`, `playbook-review` (review-only), `playbook-cifix`,
`playbook-docs`, `playbook-rebase`, `playbook-land`, `playbook-changelog`, `playbook-verify` and `playbook-solo` are
removed. Their useful methods live in the skills they named (`github`, `tdd`, `docs-sync`, `ci-fixer`, `integrator`,
`changelog`, `verifier`, `reviewer`, `delegate`); they are no longer separate CTO pipelines.
