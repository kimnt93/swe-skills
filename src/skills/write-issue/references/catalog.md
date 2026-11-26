# Catalog: what an agent may create and write

The only list. The machine copy is `catalog.json` in the `work-package` skill, which the linter reads
(`package_lint.py catalog` prints it); a test keeps this page equal to it. A value that is not here is not used. A new
value is a change to the catalog, approved by the owner of the skills.

## Issue kinds

| Kind | What it is | ID and title |
|---|---|---|
| `epic` | the parent of several issues | `<AREA>-00: Epic — <outcome>` |
| `planning` | a child or backlog item that needs a design | `<AREA>-<NN>: <outcome>`, optionally `[Low Priority] <outcome>` |
| `package` | one pull request, ready to build | `<AREA>-<NN>: <outcome>` |

A package promoted from a plan keeps the plan's ID, which may end in one letter (`API-04a`).

## Task type (exactly one label)

| Label | Use it for | Commit type |
|---|---|---|
| `enhancement` | a new or improved behaviour | `feat` |
| `bug` | something is wrong | `fix` |
| `refactor` | structure only, same behaviour | `refactor` |
| `performance` | faster or smaller | `perf` |
| `testing` | tests only | `test` |
| `documentation` | documents only | `docs` |
| `chore` | tooling, CI, build and upkeep | `chore`, `ci`, `build` |

## Lane (exactly one label, and the `Lane:` line)

| Label | Who does the work |
|---|---|
| `backend` | server, services, libraries, CLI |
| `frontend` | web, desktop and mobile UI |
| `data` | pipelines, schemas, datasets |
| `ops` | deployment, CI, infrastructure |
| `docs` | documentation work |
| `test` | test and verification work |
| `research` | an investigation with a written answer |

## Difficulty (exactly one label, and the `Difficulty:` line)

| Label | The issue is |
|---|---|
| `simple` | clear and small, no design choice: a column and its test, a docs fix |
| `medium` | several files across layers with a complete rule list: the usual feature or fix |
| `hard` | open design choices, concurrency, money paths, security, a cross-repository contract |

An agent that finds the work harder than labelled comments the evidence and asks for a new label.

## Priority (the `Priority:` line, never a label)

| Value | Meaning |
|---|---|
| `low` | backlog: after the current work |
| `medium` | planned: the normal queue |
| `high` | next: before medium work |
| `urgent` | now: something is broken or blocking |

## The quick line (`Pipeline: quick`, only from playbook-quick)

A `package` or `epic` issue that the CTO/CEO creates **because the owner asked for `playbook-quick`** carries one more
header line after `Priority:`: exactly `Pipeline: quick`. quick's unreviewed form of `pr_loop.py can-merge` merges a pull request
without a review only when every issue it links has that line **in its header**: the lines before the first `## `
heading, and only when each of them is blank or a plain header line the templates write (`Lane`, `Wave`,
`Difficulty`, `Priority`, `Pipeline`, then `: ` and plain text with no `<`, `>`, `&`, backquote or backslash), so the
owner sees on GitHub exactly what counts. Any other line there (HTML such as `<details>`, a comment opener or closer, a
fence, a quote, an indented or unknown line) means the issue has no header and is never quick, and the same text below
a heading is not the line either; the linter says why. No other line value exists, a planning card never has it, and `playbook-build`, `playbook-ship` and
`playbook-plan` never write it; the linter refuses any other `Pipeline:` line, and a `Pipeline:` line outside the
header (indent or quote an example of it).

## Area (zero or more labels)

The part of the product (`bots`, `mobile`, `ci`, ...). Each project has its own; use only the ones `gh label list` shows.

## Flags (optional labels)

| Label | Meaning |
|---|---|
| `risk:low` | nobody notices if it is wrong for a day |
| `risk:standard` | normal review |
| `risk:money-path` | orders, fills, positions, balances, risk, P&L: never auto-merged |
| `size:large` | over the PR size limit, with a reason in the PR |
| `blocked` | waiting on something outside the card |

## Comment kinds

| Kind | Written by | First line |
|---|---|---|
| `plan` | architect, on a planning card | ``## Architecture & Planning (`ID` — Priority: Low)`` |
| `epic-plan` | architect, on an epic | ``## Architecture & Planning (`ID`)`` |
| `decision` | CTO/CEO, on a plan or a PR | `Accepted by CTO (<name>).`, `Changes required by CTO (<name>)`, or on a PR `Stopped by CTO (<name>).` and, in quick, `Returned by CTO (<name>).`; a reviewer posts only `Stopped by reviewer (<name>).` |
| `status` | whoever holds the work | `Status: started\|blocked\|done` |
| `verdict` | reviewer, on the PR, with its `## Security` section | `Verdict: PASS\|FAIL at <40-character sha>`; a FAIL in a fix loop adds `. Round K of 3.` |
| `fix` | author, on the PR | `Fixed in <sha>:` |
| `merge` | whoever the playbook names to merge, on the PR | `Merged by <who> at <sha> after PASS.`, `after checks.` (quick) or `after acceptance.` |
| `close` | the owner of the issue | `Closed: <outcome>` or `Replaced by #N` |
| `reply` | anyone answering a question | the answer |

## What an agent creates

Issues (the three kinds), comments (the nine kinds), branches, commits and pull requests (the `work-package` skill).
Every issue, comment and PR body ends with `Created: <agent name>`; every commit is authored by that name.

**Not an agent's:** the owner's acceptance comment (`Accepted by owner.`). Only the repository owner writes it
([merge rules](../../github/references/pull-requests.md#merge-rules)), and only for an issue the gate refuses as not
approved, such as an outsider's. As shipped, an issue an account with write access opens is approved without it.
