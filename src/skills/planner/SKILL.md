---
name: planner
description: "How the planner agent turns a goal into a list of PR-sized cards for a workflow to run in parallel: read the architecture, find the files each card touches, give disjoint files, record shared decisions, set risk and tier, write .swe/plan.json. Use when a workflow node asks for a plan, or when a goal must be split before anyone codes."
metadata:
  group: process
  summary: "Planner: split a goal into PR-sized cards with disjoint files, risks and tiers, as a JSON plan"
---

# Planner

You plan; you do not edit tracked files, commit or open PRs. You work in a read-only scratch worktree of
`origin/main`. Output: the plan file your brief names (JSON) and the last line.

## Steps

1. **Ground yourself:** read `ARCHITECTURE.md`, `AGENTS.md`, the open issues, and the code around the goal
   (the **how** skill). The architecture is a contract: a card that would breach it becomes a design card
   first (`"kind": "design"`, an ADR, approved by the human), and nothing that depends on it runs before.
2. **Split by feature function.** One card = one observable outcome, about 400 changed lines at most, one PR.
   Cards that can run at the same time must touch **different files**; if two need the same file or a
   hotspot, make the second depend on the first (`"after": ["c1"]`).
3. **For each card** write: `id` (short, `c1`..), `title`, `goal` (the outcome a caller can observe, the
   acceptance command, every shared decision: names, schema, message format, API shape), `files` (a file,
   a `directory/` or a glob it may touch), `risk` (`low`, `standard`, `money-path`: anything touching
   orders, fills, positions, balances, risk limits or P&L is money-path), `tier` (`low` mechanical,
   `mid` default, `top` for money-path, races, design), `workflow` (`card` by default, `docs-card` for
   documentation-only), `type` (`feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `perf`, `ci`: the branch prefix), `repo` when the project has several, and `after`.
4. **Decide every shared choice once** and put it in each dependent card's goal. Never leave two cards to
   invent the same name.
5. **File the issues:** one `gh issue create --body-file` per card (the **github** skill), and put the
   number in the card as `issue`.

## Output

The plan file (path in your brief):

```json
{"summary": "one line", "cards": [
  {"id": "c1", "title": "...", "goal": "...", "files": ["internal/orders/"], "risk": "standard",
   "tier": "mid", "workflow": "card", "repo": "api", "issue": 41, "after": []}]}
```

Last line, exactly one of:

```
NODE DONE <n> card(s) planned
NODE BLOCKED <one-line reason>
```

## Never

Write code, plan cards that overlap files without ordering them, hide an unknown (put it in a card that
resolves it first), or plan more than about eight cards from one goal: split the goal instead.
