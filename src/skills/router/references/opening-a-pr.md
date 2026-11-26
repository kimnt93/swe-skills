### Opening a PR

1. **Branch and worktree** off `main`, named `<type>/<issue>-<slug>` (the `github` skill). Each subagent
   on its own worktree.
2. **Commits:** small, ordered, each one green; Conventional Commits `type(scope): subject`
   (`fix(orders): commit offsets after the fill upsert`).
3. **Before you commit,** run the formatter and linter of each language touched (`golangci-lint fmt`
   and `run`, `ruff format` and `check`, `cargo fmt` and `clippy -D warnings`, `eslint` and `tsc`),
   then the **deslop** skill over the diff.
4. **Verify:** `make verify` on the committed head. `docs/` already describes the change (the **docs-sync** skill); the body says
   "docs: updated" or "docs: no change".
5. **Body** (a one-minute briefing, under about 40 lines): copy the one
   [PR template](../../work-package/assets/pr.template.md) and follow its sections. Use the **blast-radius** skill for a
   risky change; for performance, give one number `before → after`. No "Generated with" footer.
6. **Lint, then open it ready (not draft):** `pr_lint.py local --body pr.md --allow '<scope>'` with
   0 problems, then `gh pr create --base main --title ... --body-file pr.md` and `pr_lint.py pr <n>`
   (the `github` skill's pull-requests reference). The body ends with `Created: <author>`.
   Prefer five narrow PRs to one large one (the `github` skill's submit rules).
7. Post the URL and keep building. Don't babysit each PR; see [babysit](babysit.md) when asked.

**Reply:** the PR URL and its verification line.
