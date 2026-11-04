---
name: learn
description: "How this project learns: agents report durable facts in their run reports, and the manager folds them into PROJECT.md, which stays under 2000 words; detail that does not fit moves into a project skill under skills/. Use at the end of every run (manager) and when you finish a node (any agent)."
---

# Learn

This project improves itself. What an agent learns once should not be learned again.

# Where knowledge lives

- `PROJECT.md` (project directory): the short map every agent reads first. **At most 2000 words.**
- `skills/<topic>/SKILL.md` (project directory): detail that does not fit in `PROJECT.md`, one topic per skill
  (for example `skills/payments-api/SKILL.md`, `skills/release/SKILL.md`). Agents read the ones that match their task.
- Repo files (`ARCHITECTURE.md`, ADRs): decisions of one repo stay in that repo, not here.

# If you are an agent in a node

- End your report with a `## Learned` section: at most five bullets, each one durable fact: a command that
  works, a convention, a dependency and its version, a gotcha, a place a thing lives.
- Leave out task details, opinions and anything already in `PROJECT.md`. Nothing new: leave the section out.
- Do not edit `PROJECT.md` or `skills/` yourself; the manager does.

# If you are the manager

Run this after `swe-cli flow merge` and before `swe-cli flow clean`: the run report ends with `## Learned`.

1. Read `PROJECT.md` and the `## Learned` bullets of the run report.
2. Fold in each bullet that is true and durable under the right heading; merge duplicates; delete a line that
   the new fact makes wrong. Verify a doubtful fact with a command before you write it.
3. Run `swe-cli project notes`. Over 2000 words: move the most detailed section into
   `skills/<topic>/SKILL.md` (frontmatter `name` and `description`, a body with `#` sections), leave a one-line
   pointer in `PROJECT.md`, and run it again.
4. When the human states a rule ("always...", "never..."), write it under `# Conventions` right away.

# Writing rules

- Markdown with `#` headings and short bullets; commands in backticks.
- One fact per bullet, in the present tense, with the version or path that makes it checkable.
- No secrets, no tokens, no private URLs.
