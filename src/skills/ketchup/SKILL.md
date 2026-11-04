---
name: ketchup
description: "Catch the human up on what changed since their last message, in plain words, and list every decision waiting on them with what they need to decide it from the reply alone. Use for 'catch me up', after a long unattended run, or at the start of a session that resumes work."
metadata:
  group: process
  summary: "Plain-words catch-up on what changed and what waits on you"
---

# Ketchup

Read-only. Assume the human remembers their last message and nothing after it.

1. **Gather:** your work since then, subagent and delegated-session reports, and the live state of every PR,
   card and CI run this work touched (`gh pr view`, `gh pr checks`, `swe-cli delegate status <project>`). Check every
   number against its source.
2. **Open with one sentence** naming what waits on the human, or that nothing does.
3. **What happened:** under 100 words. One plain line per thing they asked for: what came of it and
   whether it is done, running, failed or not checked. "The orders API now rejects over-limit orders",
   not "PR 42: done". Name bugs found and fixed on the way.
4. **Decisions waiting on them:** for each, the call (merge, approve, choose), your pick, what it
   changes for users, the evidence, and the risk (always say it, even "low: only the docs change").
   For a choice between options, each option's gain and cost.
5. **Pictures only when they help:** a screenshot of a changed page, a Mermaid diagram of a PR stack
   or a data flow (at most six boxes). Never a picture of something you didn't capture.

Leave out hashes, paths and commands unless the human needs one to act.
