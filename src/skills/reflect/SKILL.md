---
name: reflect
description: "Mine the current conversation for durable lessons with three parallel reviewers and a synthesizer, then turn each accepted lesson into a skill edit in this plugin's source, a new check, or a backlog item, after the human approves. Use when the human says reflect, or after a long task whose recipe should not be lost."
metadata:
  group: process
  summary: "Turn a long task's lessons into approved skill edits or new checks"
---

# Reflect

Skip it when the task was trivial or a skill was followed correctly. One-offs are not lessons.

1. **Find this conversation's transcript** (the router's `harness` reference; this workspace only),
   or write a tight digest of the session.
2. **Three reviewers in parallel**, each with its prompt verbatim and the transcript path:

   | Lens | Tier | Prompt |
   |---|---|---|
   | judgment: decisions, missed rules, corrections | `top` | [judgment-reviewer](references/judgment-reviewer.md) |
   | tooling: context the human had to paste that a command or skill could have fetched | `low` | [tooling-reviewer](references/tooling-reviewer.md) |
   | divergent: what another approach would have done better | `top`, another family | [divergent-reviewer](references/divergent-reviewer.md) |

3. **Synthesize** at tier `top` with [synthesizer](references/synthesizer.md) and the three outputs:
   an Accepted / Rejected / Backlog list.
4. **Structure before prose:** an accepted lesson that a lint, a validator check or a test would
   enforce better becomes a backlog item "build this check" (the **encode-lessons-in-structure** principle).
5. **Apply after approval only**, in this plugin's source repository (`src/skills/`, `src/agents/`,
   `fleet/skills/`), never in `dist/` or an installed copy. A substantive edit runs the router's eval
   playbook first. Then `make validate`, `make test`, and reinstall.

**Reply:** edits applied, checks to build, findings dropped and why.
