---
name: formal-verify
description: "Formally check the code where a bug costs the most and tests reach the least: an order or position state machine, retries around a commit, concurrent balance updates, a parser, Rust unsafe code. Picks the tool (TLA+, property-based tests, Kani), proves the property can fail, and keeps the check true to the code as it changes. Use for money-path state machines and races, or after merges that touched verified code."
metadata:
  group: process
  summary: "Check state machines, races and retries across every case in a bounded scope"
---

# Formal verify

A test checks the cases someone wrote. A formal check covers every case in a stated scope.

| You want to | Read |
|---|---|
| check a property for the first time and leave a project-local skill that rechecks it | [create](references/create.md) |
| bring an existing check back in line after the code changed | [maintain](references/maintain.md) |

| The question | Tool |
|---|---|
| can events happen in a bad order (order lifecycle, retries, consumer + offset commits) | TLA+ (TLC) on a small model of the design |
| does the real code hold an invariant for every input up to a size | property-based tests on the real code: Go `testing/quick` or `pgregory.net/rapid`, Python Hypothesis, Rust `proptest` |
| Rust `unsafe`, overflow, panics | Kani |

Rules: show each property **failing** on a broken variant before trusting a pass; a failure on the
current code is a finding, never a reason to weaken the property; state the bounds and assumptions;
edit only the verification, not product code, unless asked.
