---
name: playbook-complete
description: "The complete build pipeline with a separate reviewer: the CTO/CEO turns a problem or an accepted plan into approved issues, each developer implements one in its own worktree, opens a PR and hands it over, a reviewer (another agent) reviews, fixes what it finds and passes it within 3 rounds or stops it, and the CTO/CEO trusts that verdict and merges without reviewing again. Use for features, hard work or building an accepted plan. For small work the CTO/CEO checks itself use playbook-quick; for one existing PR use playbook-ship."
metadata:
  group: start
  summary: "Complete: CTO issues, developer PRs, a reviewer reviews and fixes, CTO trusts and merges"
---

# Playbook: Complete

A problem goes in; each issue ends **merged** or **stopped**. It is `playbook-quick` with the judging moved to a
**reviewer**: the reviewer reviews **and fixes**, and the CTO/CEO **trusts its verdict** and merges.

```text
problem ─► CTO/CEO: issues, approved ─► developer: own worktree, one PR ─► hands over, removes its worktree
                                                                              │
          CTO/CEO sends it to a reviewer ◄────────────────────────────────────┘
                    │
          reviewer: review ⇄ fix, at most 3 rounds
                    ├─ PASS ────► CTO/CEO trusts it ─► merges ─► confirms ─► reviewer removes its worktree
                    └─ Stopped ─► CTO/CEO reports it (PR and branch stay) ─► reviewer removes its worktree
```

The reviewer's own fixes are **checked by nobody else** before `main`: that is the trade this playbook makes. The PASS
names them, and a `risk:money-path` PR is never auto-merged.

Commands: [orchestration](references/orchestration.md) (Orca `/orchestration`; outside Orca, the `delegate` skill). A
full run: [example](references/example.md).

## Roles

| Role | Does | Does not |
|---|---|---|
| **CTO/CEO** | writes the issues, sends the work, hands each PR to a reviewer, **trusts the verdict**, merges, confirms | review the diff again, edit code |
| **Developer** | builds one issue in its own worktree, opens the PR, hands it over, removes its worktree | merge, fix after the handover |
| **Reviewer** (a different agent, from a different model family when the project has one) | reviews the PR, **fixes its findings**, passes or stops it | judge code it wrote first, merge, change the issue |

The developer, the reviewer and the CTO/CEO sign with different agent names.

## When to use it

| The work | Playbook |
|---|---|
| a design choice is still open | `playbook-plan` first, then build the accepted plan here |
| features, `hard` work, races, security, unfamiliar code, an accepted plan | **complete** |
| `simple` or `medium` work the CTO/CEO will check itself | `playbook-quick` |

## 1. CTO/CEO: issues, approved

As [playbook-quick step 1](../playbook-quick/SKILL.md#1-ctoceo-turn-the-problem-into-issues): one `package` issue per PR,
a parent `epic` for two or more, waves and shared contracts written down. From an accepted plan, each of its packages is
one issue. **Run the gate on every issue** and send only what it allows; for the rest give the repository owner the
[acceptance comment](../github/references/issues.md#before-any-work) and end your turn. Never post it yourself.

## 2. CTO/CEO: send each issue to a developer

The [developer brief](assets/example/developer-brief.md), with the developer's name and your return address. A wave is
sent only after what it depends on is **merged**. Then end your turn.

## 3. Developer: build, open, hand over

1. Steps 1 to 5 of [playbook-quick step 3](../playbook-quick/SKILL.md#3-developer-one-issue-one-worktree-one-pr): the
   gate first, **its own worktree**, owned files, test first, commits under its name, the linters, the PR, green checks.
2. **Hand over.** The branch now belongs to the reviewer. Prove that everything is on GitHub:

   ```bash
   python3 <github skill>/scripts/pr_loop.py can-remove --worktree <path> --pr <n> --repo <owner>/<repo> --handover
   ```

3. Send the [handover report](assets/example/return-report.md) and remove the worktree
   (`ORCA worktree rm --worktree path:<path>`; refused: keep it, do not force it). A worker inside it reports
   first and removes it last.

The developer is then finished. Cancelled or `PR BLOCKED` before that: report and keep the worktree.

## 4. CTO/CEO: hand the PR to a reviewer

Do **not** read the diff or run the commands: that is the reviewer's job. Send the
[reviewer brief](assets/example/reviewer-brief.md) to an agent that wrote none of the PR, then end your turn.

## 5. Reviewer: review and fix

Follow the [review and fix loop](../reviewer/references/fix-loop.md): own worktree on the PR branch, a
`FAIL ... Round k of 3.` before each fix, **at most 3 rounds**, then a PASS that names its own commits, or
`Stopped by reviewer`. Send the CTO/CEO the [review report](assets/example/review-report.md): `REVIEW PASSED` or
`REVIEW STOPPED`, the PR, the head SHA, the verdict link, rounds used and the commits it pushed.

## 6. CTO/CEO: trust the verdict, merge, confirm

**Trust it: do not review again.** Check only that it is a real verdict on what you are about to merge:

```bash
python3 <github skill>/scripts/pr_loop.py can-merge --pr <n> --repo <owner>/<repo>   # PASS on this head, not the writer's
python3 <github skill>/scripts/issue_gate.py pr <n> --repo <owner>/<repo>            # merge rules: allowed
gh pr checks <n> --repo <owner>/<repo>                                               # required checks green
gh pr view <n> --repo <owner>/<repo> --json headRefOid,mergeable,mergeStateStatus    # not behind, no conflict
gh pr merge <n> --repo <owner>/<repo> --rebase --match-head-commit <passed sha> --delete-branch
```

Anything refused: do not merge. A branch behind `main` or a red check goes **back to the reviewer**, whose new head needs
a new PASS. `risk:money-path`: ask a person to merge. Asking for this playbook gives the CTO/CEO the merge; a project that
reserves it for a person wins.

Then confirm as [playbook-quick step 6](../playbook-quick/SKILL.md#6-ctoceo-merge-then-confirm-the-merge) (`MERGED`, the
issue `CLOSED`), post the [merge comment](assets/example/merge.md) and tell the reviewer `MERGED`. It
[removes its worktree](../reviewer/references/fix-loop.md#remove-your-worktree). Merge in dependency order, then send
the next wave. When every child is merged, run the parent's `Done when` on `main` and close the parent.

## 7. The loop breaks

The reviewer posts [`Stopped by reviewer`](assets/example/stopped.md), marks the issue blocked and removes its worktree.
**The PR stays open, the branch stays on GitHub, the issue stays open.** The CTO/CEO does not merge, overrule or restart
it: it reports the verdict to the human. Work that depends on it is not sent; other issues carry on.

## One good, one bad

- **Good:** the CTO receives `REVIEW PASSED`, sees `can-merge` and the gate allow it and the checks green, merges that SHA.
- **Bad:** the CTO re-reads the diff and asks for changes, or merges a head pushed after the PASS.

## Done

- Every issue is **merged** (a PASS on the merged head, the merge confirmed, the issue closed) or **stopped**.
- No PR got more than 3 rounds; no developer, reviewer or check worktree is left; no worker is running.
- The human has one report: what merged, what stopped, and **which commits only the reviewer saw**.

## Never

- Build or merge for an issue the gate refuses, or write the owner's acceptance.
- Let a developer or the reviewer's author judge its own PR, or one agent be both developer and reviewer.
- Merge without `can-merge`, on a new head, with a red or missing required check, or with an admin override.
- Auto-merge a money path, ask for a fourth round, or close a stopped PR.
