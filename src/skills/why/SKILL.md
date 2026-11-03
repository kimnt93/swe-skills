---
name: why
description: "Find out why code is shaped the way it is: the commits, PRs, issues, incidents and errors behind it, separating what the evidence shows from what is inferred. Use for 'why is it like this', before removing a guard, retry, flag or odd special case, or before redesigning existing code."
metadata:
  group: process
  summary: "Find the history and reasons behind code before changing or removing it"
---

# Why

Be a careful investigator: say what you know, what you infer, and what you couldn't find.

1. **Anchor the target:** files and line ranges, the key symbols, and their history:
   - `git blame -L <start>,<end> <file>` for the last touch of each line;
   - `git log --follow -p -- <file>` through renames; `git log -S '<symbol>'` for when it appeared;
   - PR numbers from merge commits, then `gh pr view <n> --comments` for the discussion;
   - linked issues: `gh issue view <n>`.
2. **Search each source of evidence**, and record the ones that returned nothing:
   - source control (always): commits, PRs, review comments, tests added with the code;
   - issues and tickets;
   - incidents and errors: Sentry/GlitchTip for the exception a guard or retry was added for;
   - metrics and logs: Grafana and Loki around the commit date, for timeouts, limits and retries;
   - docs: the repo's `docs/`, ADRs, READMEs.
   Defensive code (a NULL check, a retry, a timeout, a feature flag) usually has an incident behind it: look for it.
3. **Write it:** the question; the code in question; **what we found** (each with its source); **what
   we can reasonably infer** (labelled); competing explanations; **what we don't know**; the sources
   consulted, one line each, including the empty ones.
4. If the question precedes a change, end with **Preserve / Change / Avoid / Risk** for the change.
