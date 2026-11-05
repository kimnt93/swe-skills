---
name: planner
description: "How the planner agent turns a goal into a list of PR-sized cards for a workflow to run in parallel: read the architecture, find the files each card touches, give disjoint files, record shared decisions, set risk and agent, write .swe/plan.json. Use when a workflow node asks for a plan, or when a goal must be split before anyone codes."
metadata:
  group: process
  summary: "Planner: split a goal into PR-sized cards with disjoint files, risks and agents, as a JSON plan"
---

# Planner

You plan; you do not edit tracked files, commit or open PRs. You work in a read-only scratch worktree of
`origin/main`. Output: the plan file your brief names (JSON) and the last line.

## Steps

1. **Ground yourself:** read the `# Map` block of the project's `PROJECT.md` (the repos, who depends on whom,
   what is external), `ARCHITECTURE.md`, `AGENTS.md`, the open issues, and the code around the goal
   (the **how** skill). The architecture is a contract: a card that would breach it becomes a design card
   first (`"kind": "design"`, an ADR, approved by the human), and nothing that depends on it runs before.
2. **Split by feature function.** One card = one observable outcome, about 400 changed lines at most, one PR.
   Cards that can run at the same time must touch **different files**; if two need the same file or a
   hotspot, make the second depend on the first (`"after": ["c1"]`).
3. **For each card** write: `id` (short, `c1`..), `title`, `goal` (the outcome a caller can observe, the
   acceptance command, every shared decision: names, schema, message format, API shape), `files` (a file,
   a `directory/` or a glob it may touch), `risk` (`low`, `standard`, `money-path`: anything touching
   orders, fills, positions, balances, risk limits or P&L is money-path), `agent` (`documenter` mechanical,
   `developer-junior` for a clear description, `developer-senior` for medium or complex work, money-path, races, design; the names are in `config.yaml`), `reviewer` (`reviewer-junior` by default; `reviewer-senior` for complex or money-path cards or code the human did not write), `workflow` (`card` by default; `lane` under `delivery`), `type` (`feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `perf`, `ci`: the branch prefix), `repo` when the project has several, and `after`.
4. **Decide every shared choice once** and put it in each dependent card's goal. Never leave two cards to
   invent the same name.
5. **File the issues:** one `gh issue create --body-file` per card (the **github** skill), and put the
   number in the card as `issue`.

## Output

The plan file (path in your brief):

```json
{"summary": "one line", "cards": [
  {"id": "c1", "title": "...", "goal": "...", "files": ["internal/orders/"], "risk": "standard",
   "agent": "developer", "workflow": "card", "repo": "api", "issue": 41, "after": [], "waits_for": []}]}
```

For a goal that touches several repos, plan one card per repo from the Map: give each card its `repo`, write the
interface between a provider and its consumers once and paste it into both goals, and set the consumer's
`waits_for` to the provider's card (the Map's `depends_on`). Do not ask the human anything: an unknown becomes
a stated assumption in the goal.

`after` holds a card back until the other card is finished (built, checked, reviewed). `waits_for` is for the
`delivery` workflow, where a card in one repo needs a card in another repo **merged to main**: both cards start at
once, the dependent builds against the interface written in its goal, then waits for the merge, pulls it, and is
checked and merged in turn. Put the provider's interface (names, types, API shape, schema) in both goals, and
list the provider's id in the consumer's `waits_for`. Never make two cards wait for each other.

Do not plan documentation as a card of its own for a code change: the workflow has a docs step after every
implementation that updates `docs/` from the diff. A docs-only goal is the `docs` workflow, which has no planner.

Last line, exactly one of:

```
NODE DONE <n> card(s) planned
NODE BLOCKED <one-line reason>
```

## Never

Write code, plan cards that overlap files without ordering them, hide an unknown (put it in a card that
resolves it first), or plan more than about eight cards from one goal: split the goal instead.
