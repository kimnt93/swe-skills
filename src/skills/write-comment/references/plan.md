# The plan comment

The architect writes it on the issue **before** anyone codes. It is not a PR, not a branch and not code. A developer who
reads it can start every package without asking a design question.

## Analyse the code first

1. Read the issue, `ARCHITECTURE.md`, `STACK.md`, `AGENTS.md`, every file under `Read first`, their callers and their
   tests (the `how` and `why` skills).
2. Note what exists, what is reused, what is missing and what must stay unchanged, each with a file or symbol.
3. Compare at least two whole designs (the `architect` skill up to its checkpoint). Keep one.
4. Split by observable outcome, with disjoint files per wave (the `planner` skill's splitting rules; no plan file).

## Write it from the template

| On | Kind | Template | First line |
|---|---|---|---|
| a planning card | `plan` | [plan.template.md](../assets/plan.template.md) | ``## Architecture & Planning (`ID` — Priority: Low)``, the issue's priority |
| an epic | `epic-plan` | [epic-plan.template.md](../assets/epic-plan.template.md) | ``## Architecture & Planning (`<AREA>-00`)`` |

The template's sections and guidance are the format ([templates](../../write-issue/references/templates.md)). Beyond it:

- Package IDs use the card's ID with a letter (`API-04a`) or the next numbers of the area (`API-05`).
- In a wave table, a wave says what it waits for; `Issue` is `` `#N` (`ID`) ``, or the ID alone while the child issue
  does not exist.
- Each package holds its own unit tests and functional tests
  ([what a developer delivers](../../developer/SKILL.md#what-you-deliver)): no package is only another's tests, and none
  is for the tester unless the request [asks for testing](../../bot-orchestration/SKILL.md#the-tester-only-on-request).
- Shared files include ones that work outside this epic also touches.

## Decided or open

[The asking rule](../../principles/references/never-block-on-the-human.md) sorts every choice:

- **`Decisions`:** every other choice you made, as decided: the recommended option and its reason.
- **`Open Questions`:** only what the rule lists under *Still ask* (or another named stop), each with your
  recommendation and the packages that wait for it. None: leave the section out.

## Revising

A revision is a new comment whose first line ends `— Plan v2)`; the old one stays.

## Not ready

If, after looking in the code, docs, issues and past decisions, the card has no observable outcome, or you lack access,
or it contradicts itself, post a `status` comment (`Status: blocked`) naming what is needed, all at once. Do not guess a
requirement.
