---
name: verify-maintain
description: "Keep a project's verify skill and feature map true to the app: check every feature against the source, drive every feature live once, and ship at most one PR of proven corrections. Use periodically, after features change, or when a verify run fails for reasons that look like drift."
metadata:
  group: process
  summary: "Keep the verify skill and its feature map true as the app changes"
---

# Verify maintain

A feature map rots when the app changes. This is the upkeep pass.

**Outcome**, one of: **clean** (no change needed), **changed** (one PR of proven corrections),
**blocked** (say exactly why).

**Edit only** the verify skill's directory (its `SKILL.md`, `features/`, its helper scripts) and
`verify.mk`. Never product code: a feature the app no longer does is either doc drift (fix the map)
or a regression (report it).

1. **Find the target:** `.agents/skills/verify-*/` (or `.claude/skills/verify-*/`). None: use the
   **verify-create** skill instead.
2. **Index:** fix missing, extra or dead entries in `features/README.md`.
3. **Source pass:** one read-only subagent per feature file (the `verifier` or `developer` agent), in parallel. Each
   checks the feature against the code (routes in the Fiber router, the OpenAPI file, Next.js `app/`
   routes or React Router routes, topic names, model entry points) and returns drift with `file:line`
   and one drive recipe.
4. **Live pass:** you drive every feature once, serially, on one healthy instance: run Doctor before
   the first drive and after any surprise; keep the evidence; stop what you started.
5. **Triage:** a wrong description is drift (fix it); working behaviour the harness can't drive is a
   harness gap (fix it, then re-drive); broken behaviour is a product bug (report it, keep it out of the PR).
6. **Ship or stop:** one PR for `changed`; a report for `clean` or `blocked`.
