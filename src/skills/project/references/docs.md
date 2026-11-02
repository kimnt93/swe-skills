# Project documents

| File | What it holds | Who changes it |
|---|---|---|
| `README.md` | what the project does, how to run it locally, `make verify` | any PR that changes how to run it |
| `ARCHITECTURE.md` | **the contract:** components, layers and what may import what, data each component owns (tables, topics, buckets), external interfaces (APIs, topics), the language per component, invariants | only a PR that also passes the **architect** skill's review; agents read it before structural changes |
| `docs/adr/NNNN-<title>.md` | one decision each: context, decision, alternatives rejected, consequences | a PR that makes the decision |
| `CHANGELOG.md` | user-visible changes per release | the release PR |
| `RUNBOOK.md` | how to deploy, roll back, read the dashboards, handle the usual alerts | after any incident or deploy change |
| `AGENTS.md` | repo rules for agents, and the rule → enforcer table (the **correct** skill) | when a rule or enforcer changes |

`ARCHITECTURE.md` starts from `assets/ARCHITECTURE.md`; an ADR from `assets/adr.md`.

**Breaching the contract** (a new dependency between components, a component writing data it does not
own, a new public interface) is a design change: an ADR plus the `ARCHITECTURE.md` edit in the same PR,
reviewed by the other model family and approved by the human.
