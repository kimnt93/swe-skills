# {project}

What this project is, in two lines. Keep this file under 2000 words (`swe-cli project notes` counts them);
detail goes into `skills/<topic>/SKILL.md`. The manager maintains it; see `skills/learn/SKILL.md`.

# Map

The repository map: every repo of the project, what depends on what, and what lies outside. The manager and the
planner read this block to give each repo its own card, to order merges (a repo merges after the repos it
depends on) and to write the interface between two repos once. Keep it true; the manager updates it in the same
run that changes a dependency. One YAML block, nothing else is parsed.

```yaml
repos:
  # <repo key from project.yaml>:
  #   role: what it is, in a few words
  #   provides: [the interfaces other repos use: an HTTP API, a library, a topic, a table]
  #   docs: docs/README.md   # the summary other repos read first; references live in docs/references/
  #   depends_on: [other repo keys; the repo that provides what this one uses]
  #   verify: make verify
external:
  # <name>:
  #   kind: database | queue | api | service
  #   used_by: [repo keys]
  #   note: version or owner that matters
merge_order: []   # repo keys, providers first; derived from depends_on, written down so it can be checked
```

# Repos

<!-- one bullet per repo: folder, what it is, language, how to verify (the make target) -->

# Dependencies

<!-- services, databases, queues, external APIs, and which repo depends on which; versions that matter -->

# Commands

<!-- build, test, verify, run, deploy: the exact commands, per repo -->

# Conventions

<!-- naming, branching, review rules, things the human told the agents to always or never do -->

# Gotchas

<!-- surprises that cost time before: flaky tests, ordering of deploys, generated files -->

# Decisions

<!-- date, decision, reason: one line each; longer ones are ADRs in the repo -->
