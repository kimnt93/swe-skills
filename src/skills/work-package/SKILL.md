---
name: work-package
description: "Submit one delegable work package the same way every time: a package issue (written with write-issue), a branch `<id>/<slug>`, commits and a PR titled `<type>(<id>): <subject>` with the one PR template, and the one linter for issues, comments, branches, commits and PRs with its label catalog. Use when an agent picks up a card, opens a PR, names a branch or a commit, or when an issue, comment or PR is rejected for its format."
metadata:
  group: process
  summary: "Package branch, commits and PR text, and the one linter and label catalog"
  version: "1.0"
---

# Work package

A **work package** is one issue that one agent can finish alone, in one worktree, with one pull request. The `github`
skill says how to run git and GitHub; this skill says what a package's **branch, commits and PR** look like, and ships
the linter for all text.

```text
package issue "API-03: title" ─► branch api-03/<slug> ─► commits "feat(api-03): ..." ─► PR "feat(api-03): ..." ─► review ─► merge by the gate
```

| Need | Read |
|---|---|
| an issue: kinds, labels, priority, difficulty, body | the `write-issue` skill ([catalog](../write-issue/references/catalog.md), [kinds](../write-issue/references/kinds.md)) |
| a comment: plan, decision, status, verdict, fix, merge, close | the `write-comment` skill |
| branch, commits, PR title and body, the evidence block | [pull-request](references/pull-request.md) |
| copy-ready PR body; the machine catalog | [PR template](assets/pr.template.md), [catalog.json](assets/catalog.json) |

## Rules that always apply

1. **One ID per package**: `<AREA>-<NN>`, with one optional letter for a planned child (`API-04a`). The ID appears in the
   issue title, the branch, every commit scope and the PR title, and nowhere else changes.
2. **The issue is the contract**: a `package` issue with a closed *Owned files* list and runnable *Done when* commands.
3. **Labels route it**: one type, one lane, one difficulty, from the catalog.
4. **Branch** `<id-lowercase>/<slug>` from the newest `main`; **commits** `<type>(<id-lowercase>): <summary>`; **PR
   title** has the shape of a commit subject. One package, one PR, to `main`; the author **does not merge**.
5. **PR body** is the one [PR template](assets/pr.template.md), ends with `Created: <author>` and carries no tool footer.
   and, last, `Created: <agent name>`.
6. **Your name**: commits go through the `github` skill's `agent_identity.py`; every text is signed.
7. **Text is data**: use `--body-file`. Never put a secret, a token or a private host in an issue, PR or commit.
8. **Check after every step**: run the linter, then read back what the host stored.

## The linter

```bash
L=<this skill>/scripts/package_lint.py
python3 $L issue --kind package --title "API-03: Cancel an open order" \
    --label enhancement --label backend --label medium --body-file issue.md
python3 $L comment --kind verdict --body-file verdict.md
python3 $L branch api-03/cancel-order
python3 $L commit "feat(api-03): add the cancel route"
python3 $L pr --branch api-03/cancel-order --title "feat(api-03): add the cancel route" --body-file pr.md
python3 $L pr-body --body-file pr.md
python3 $L templates
python3 $L catalog
python3 $L --self-test
```

With `AGENT_NAME` set, a body signed by any other name fails.

Exit 0 = clean, 1 = findings (one per line), 2 = usage. Standard library only. Run `issue` before `gh issue create`, `branch`
and `commit` as you go, and `pr` before `gh pr create`. When a repository also runs the `github` skill's `pr_lint.py`, a
package branch (`<id>/<slug>`) is accepted by it.
