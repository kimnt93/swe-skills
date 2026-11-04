---
name: verifier
description: "How a scheduled agent proves a project still works like a user would and sweeps it for problems without changing anything: run make verify and the project's verify skill against the real app, replay the feature map, record regressions as issues, log anti-patterns and drift to a findings document, and leave a short review list. Use for the nightly or weekly check of a repo, after a burst of merges, or before turning autopilot up."
metadata:
  group: process
  summary: "Verifier: run the real app against the feature map, file regressions, list findings; edits nothing"
---

# Verifier

You find problems; you do not fix them. A workflow node starts you in a read-only scratch worktree of
`origin/main`, so the central clone is untouched.

## Steps

1. **Baseline:** `make verify` on the head of `main`. Red: file an issue `type:bug risk:standard` with the failing
   output and stop; there is nothing to sweep on a broken base.
2. **Drive the app like a user** (the project's verify skill and its feature map; the `verify-maintain`
   skill's checks): every feature once, live. Record for each: command run, output, pass or fail.
3. **Regressions:** one issue per distinct failure (`gh issue create`, body from a file), with the exact
   command, the output and the first bad commit if you can find it (`git bisect run` on the failing command).
   Search open issues first; add to an existing one instead of duplicating.
4. **Sweep** (read-only): repeated mistakes the `correct` skill would turn into a check, a feature map
   that no longer matches the source, dead code, a doc that contradicts the code. List each in
   your report as `<path>:<line> <one-sentence finding> <evidence command>`.
5. **Review list:** put it in your report (the path in your brief): regressions filed (links), findings worth a card,
   and what you could not check and why. Last line, exactly one of:

```
NODE DONE <n> regression(s) filed, <m> finding(s) logged
NODE BLOCKED <one-line reason>
```

## Never

- Edit tracked files, open a PR, merge, or change the feature map (that is a `verify-maintain` card).
- Report a number or a pass without the command that produced it.
- Fix a regression you found: file it, so the manager scopes it as a card.
