# Playbooks

There are **three CTO pipelines**. Every repository change is one of them. They all use the `work-package` issue and PR
format, the `github` rules and the reviewer/gate merge; none of them lets the author merge.

| Shortcut | Pipeline | Use it for | Inputs |
|---|---|---|---|
| `/swe:playbook-plan` | **Plan** | new feature, cross-file change, hard bug, a shape not yet settled | `issue` or `goal` |
| `/swe:playbook-review` | **Review** | the plan pipeline plus an independent PASS/FAIL review and fix round; risky or money-path work, code the author did not write | `issue` or `goal` |
| `/swe:playbook-quick` | **Quick** | docs, one-file fix, small test, mechanical change; **no** new feature or cross-file work | `issue` or `goal` |

`/swe:playbook` lists the three. There is no other playbook.

## DAGs

```text
Plan     CTO issue ─► architect plan comment ─► CTO accepts ─► dev(s)/subagents ─► PR ─► reviewer/gate merge
Review   Plan ─► reviewer PASS/FAIL at SHA ─► author fixes findings ─► re-review ─► reviewer/gate merge
Quick    CTO issue ─► dev ─► PR ─► reviewer/gate merge
```

## The gates

| Gate | Owner | Passes when |
|---|---|---|
| Issue ready | CTO | `ID: title`, lane + difficulty + area labels, closed file list, runnable `Done when` |
| Plan accepted | CTO | architect's one plan comment has packages/waves/contracts/verify/risks; CTO accepts in one comment |
| PR ready | developer | owned files only, test first, `Closes #N`, evidence from the card's verify command on the committed head |
| Review | reviewer (different family) | `Verdict: PASS at <full sha>` and no open finding; a new push needs a new verdict |
| Merge | reviewer/gate | PASS at the current SHA, green required checks, branch not behind `main`; merges through `swe-cli merge` or the documented gate |

The exact issue, plan, verdict, fix and close comments are in
[`work-package/references/comments.md`](../src/skills/work-package/references/comments.md).

## Rules

- One package, one issue, one worktree, one branch, one PR; one owner.
- The CTO does not code; the developer does not merge; the reviewer does not edit during review.
- In `review`, the default fixer is the author; if the CTO assigns the reviewer as fixer, a different reviewer or the CTO
  posts the PASS for the new SHA. Never self-approve.
- A `quick` card that grows to a new feature, a shared file or a contract change stops and becomes `plan` or `review`.
- Plans and verdicts are comments, not new issues. A plan that creates packages also creates their issues and links them.
- A merge is not done until the issue is closed, the branch deleted and the worktree removed.

## What happened to the old playbooks

The old `playbook-deliver`, `playbook-feature`, `playbook-bugfix`, `playbook-review` (review-only), `playbook-cifix`,
`playbook-docs`, `playbook-rebase`, `playbook-land`, `playbook-changelog`, `playbook-verify` and `playbook-solo` are
removed. Their useful methods live in the skills they named (`github`, `tdd`, `docs-sync`, `ci-fixer`, `integrator`,
`changelog`, `verifier`, `reviewer`, `delegate`); they are no longer separate CTO pipelines.
