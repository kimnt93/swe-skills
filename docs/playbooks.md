# Playbooks

There are **five pipelines**. They use the `work-package` formats and the `github` rules. Nothing is built or merged
unless the [merge rules](../src/skills/github/references/pull-requests.md#merge-rules) allow it, and no PR's author
merges it.

| Shortcut | Pipeline | Use it for | Inputs |
|---|---|---|---|
| `/swe:playbook-plan` | **Plan** | new feature, cross-file change, hard bug, a shape not yet settled | a problem or an `issue` |
| `/swe:playbook-quick` | **Quick** | ready to build, `simple` or `medium`; the CTO/CEO checks it | a problem or `issue`s |
| `/swe:playbook-complete` | **Complete** | features, `hard` work, an accepted plan; a reviewer reviews and fixes | a problem, a plan or `issue`s |
| `/swe:playbook-review` | **Review** | comment on one existing PR; changes nothing | a PR |
| `/swe:playbook-ship` | **Ship** | take one existing PR to `main` and close its issue | a PR |

## Bots and agents

A **bot** is a standing member that orchestrates; an **agent** is a coding CLI a bot starts for one job. Bots delegate to
bots with a handoff and report back with a status. Agents report only to their bot and never to each other. When a bot
has a role (developer, reviewer, architect), the job goes to that bot, and it runs its own agents. The CEO bot → developer
bot → agents → pull request → status flow, the message templates and the linter are in
[bot-orchestration](../src/skills/bot-orchestration/SKILL.md).

## DAGs

```text
Plan      problem ─► CTO/CEO card ─► architect ─► plan comment ─► back to CTO/CEO ─► accept ─► STOP
Quick     problem ─► issue(s) ─► dev worktree ─► PR ⇄ CTO/CEO (≤3 rounds) ─► merge or stop ─► remove worktree
Complete  problem ─► issue(s) ─► dev ─► PR, handover ─► reviewer: review ⇄ fix (≤3) ─► CTO/CEO trusts ─► merge or stop
Review    PR ─► read and run ─► one verdict comment ─► STOP
Ship      PR ─► reviewer: review ⇄ fix (≤3) ─► merge + close issue, or stop
```

In `complete` and `ship` the reviewer fixes its own findings. Nobody else checks those fixes before `main`: the PASS
names each commit, and a `risk:money-path` PR is never auto-merged
([fix loop](../src/skills/reviewer/references/fix-loop.md)).

The Plan messages travel through Orca orchestration. The
[commands](../src/skills/playbook-plan/references/orchestration.md) and a
[complete example](../src/skills/playbook-plan/references/example.md) (card, brief, plan comment, return, acceptance)
ship with the skill.

Quick ([commands](../src/skills/playbook-quick/references/orchestration.md),
[example](../src/skills/playbook-quick/references/example.md)), Complete
([commands](../src/skills/playbook-complete/references/orchestration.md),
[example](../src/skills/playbook-complete/references/example.md)) and Ship
([example](../src/skills/playbook-ship/references/example.md)) ship their own.

## Merge rules

A pull request merges only when it links an issue of its repository and every linked issue is approved: the repository
owner commented `Accepted by owner.`, the owner is its author, or its board status is `Todo` or `In Progress`. A closed
issue (done, not planned, duplicate), a `duplicate` or `wontfix` label or a refusing board status refuses it. When the
`gh` login lacks the scope for project boards, the check goes on without them and says so: no board status refuses or
approves. Any other failure to read the board refuses. The same check runs before any work starts. Agents never approve
for the owner. [Full rules](../src/skills/github/references/pull-requests.md#merge-rules).

## The gates

| Gate | Owner | Passes when |
|---|---|---|
| Card ready (Plan) | CTO/CEO | a `planning` or `epic` issue that passes `package_lint.py issue` |
| Plan returned | architect | one plan comment per version, sent back to the CTO/CEO with its URL |
| Issue ready (build) | CTO | `ID: title`, type + lane + difficulty labels, priority, closed file list, runnable `Done when` |
| Plan accepted | CTO/CEO | the `plan` or `epic-plan` comment passes the linter, every open question is answered, and the decision comment is posted. **Plan ends here** |
| PR ready | developer | owned files only, test first, `Closes #N`, evidence from the card's verify command on the committed head |
| PR returned (`quick`, `complete`) | developer | `PR READY` or `PR BLOCKED` sent back with the PR URL and head SHA |
| Accepted (`quick`) | CTO/CEO | checked at the head: lint, checks, diff, `Done when`; the decision names the SHA |
| Verdict (`review`, `ship`, `complete`) | reviewer, not the PR's writer | `Verdict: PASS\|FAIL at <full sha>` from proven findings; a new push needs a new verdict |
| Feedback limit (`quick`, `ship`, `complete`) | whoever judges | at most 3 rounds, then pass or `Stopped by`; `pr_loop.py decide` refuses a fourth |
| Trusted merge (`complete`) | CTO/CEO | `pr_loop.py can-merge`: a PASS on the head, not by the writer, naming the reviewer's own commits |
| Worktree removed (`quick`, `ship`, `complete`) | whoever made it | `pr_loop.py can-remove` allows it only when nothing is lost |
| Issue approved | the repository owner | before work starts and again before the merge: `issue_gate.py` allows it ([merge rules](../src/skills/github/references/pull-requests.md#merge-rules)) |
| Merge | CTO/CEO (`quick`, `complete`) or reviewer (`ship`) | the checked SHA is the head, green required checks, branch not behind `main`; `gh pr merge --match-head-commit` or the project's documented gate |

Issues are written with [`write-issue`](../src/skills/write-issue/SKILL.md) (kinds and the
[catalog](../src/skills/write-issue/references/catalog.md)); plan, decision, verdict, fix and close comments with
[`write-comment`](../src/skills/write-comment/SKILL.md). Each ends with `Created: <agent name>`, and commits are authored
by that name ([identity](../src/skills/github/references/identity.md)).

All templates, and how to change their style: [templates](../src/skills/write-issue/references/templates.md).

## Rules

- A build is one package, one issue, one worktree, one branch, one PR, one owner.
- The CTO does not code and the developer does not merge. A project that reserves the merge for a person wins.
- Only `complete` and `ship` let the reviewer edit, and only to fix its posted findings. `review` never edits.
- A `quick` issue that turns out to need a design decision or hard work stops and becomes `plan` or `complete`.
- Plans and verdicts are comments, not new issues. A plan that creates packages also creates their issues and links them.
- A merge is not done until the issue is closed, the branch deleted and the worktree removed.

## What happened to the old playbooks

The old `playbook-deliver`, `playbook-feature`, `playbook-bugfix`, `playbook-cifix`,
`playbook-docs`, `playbook-rebase`, `playbook-land`, `playbook-changelog`, `playbook-verify`, `playbook-solo` and the `playbook` dispatcher are
removed. `playbook-review` is now comment-only; building with a reviewer is `playbook-complete`. Their useful methods live in the skills they named (`github`, `tdd`, `docs-sync`, `ci-fixer`, `integrator`,
`changelog`, `verifier`, `reviewer`, `delegate`); they are no longer separate CTO pipelines.
