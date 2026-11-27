---
name: security-review
description: "The security and outbound-data check every pull request gets besides the correctness review, for Go, Python, Rust, TypeScript, web, API, SQL, CI, container, money, wallet, agent and prompt code: scan the diff, list every path data leaves by, work through the topics the diff touches and prove each finding with a command. A pull request that adds or widens an outbound path its accepted issue does not ask for fails, and a proven finding blocks the merge. Use when reviewing, shipping, building or auditing code, before a PASS, and when asked about security, secrets, data leaks or telemetry."
metadata:
  group: process
  summary: "Security check of every PR: proven findings block, and no data leaves unless the issue asks"
---

# Security review

Every pull request gets this check **besides** the correctness review. A correct change can still leak. Three rules
decide:

1. **No unrequested data leaves.** A pull request that adds or widens an outbound path, or sends more on one, **fails**
   unless a linked accepted issue asks for that exact destination and data ([outbound data](references/outbound-data.md)).
2. **No new risk.** A proven security finding that the pull request adds, widens or makes reachable **blocks the
   merge**. It goes under `Blocking`, never under `Residual`, however small the change.
3. **Proof, not opinion.** A finding is kept when a command you ran shows it, or two quoted lines do.

**Proofs run on your machine only**: a test, a local instance, a disposable database, a local fake receiver. Never a
live system, a real account, real funds or someone else's host
([safety rules](../web-testing/references/safety.md)). Running a pull request's code needs the
[safe-to-run check](../reviewer/SKILL.md#before-you-run-anything-from-it) first.

## Steps

1. [Scan](#the-scan) the diff.
2. List **every** outbound path the diff touches, the ones the scan missed too, and apply rule 1.
3. Read the diff against each [topic](#topics) it touches. Also read what the diff removes.
4. Prove each suspicion. Unproven is not a finding. What you could not check goes under `Not checked`.
5. Write the `## Security` section of the verdict ([comment template](../write-comment/assets/pr-comment.template.md)).
   `playbook-solo` has no verdict: its author records the result in the PR body, as a self-check.

## The scan

```bash
python3 -I <security-review skill>/scripts/security_scan.py --base origin/main --head <sha>   # in a checkout
gh pr diff <n> --repo <owner>/<repo> | python3 -I <security-review skill>/scripts/security_scan.py --diff -
python3 -I <security-review skill>/scripts/security_scan.py --tree <sha>                      # every file, for an audit
```

**Run the installed copy, never one from the pull request's checkout.** It sends nothing, runs nothing from the diff
and prints no line of it, so it is safe on code that is not safe to run: pipe in `gh pr diff` then.

**It is an aid. A clean scan is never a pass.** It has line rules only: it does not know a library it has no rule for,
or a payload built in another file than the send call. With `--diff` it sees the hunks only, so a payload widened far
from its send call is listed with `--base` and `--head` alone. Resolve **every** item: safe because of what, asked for
by which issue, or a finding. Exit 1 means items to resolve, 0 none listed, and **2 nothing was scanned**: never read
2 as clean. An `UNREAD` item (a binary, a hidden or a very long line) must be inspected another way, else no PASS.

## Topics

| The diff touches | Read |
|---|---|
| anything that sends, logs out, installs or publishes | [outbound data](references/outbound-data.md) |
| keys, tokens, passwords, config, client bundles | [secrets](references/secrets.md) |
| anything read from outside: requests, files, messages | [input validation](references/input-validation.md) |
| SQL, queries, templates, headers, anything built from text | [injection](references/injection.md) |
| routes, handlers, jobs, who may do what | [authentication and authorization](references/access-control.md) |
| pages, cookies, sessions, CORS, redirects | [session and browser attacks](references/web-session.md) |
| login, costly or public endpoints, loops over input | [rate limits](references/rate-limits.md) |
| log calls and error responses | [sensitive data in logs and errors](references/logs-and-errors.md) |
| manifests, lock files, images, actions, install steps | [dependencies and supply chain](references/dependencies.md) |
| paths, uploads, archives, commands, URLs from input | [files, commands and URLs](references/files-commands-urls.md) |
| orders, balances, payments, wallets, chains | [money and chain code](references/money-and-chain.md) |
| workflows, Dockerfiles, Compose files | [CI and containers](references/ci-and-containers.md) |
| prompts, agent instructions, tools, model calls | [agent and prompt code](references/agent-code.md) |

## What blocks

| What you proved | Where it goes |
|---|---|
| the pull request adds it, widens it or makes it reachable | `Blocking`, with the smallest fix: **FAIL** |
| data leaves and the accepted issue does not ask | `Blocking`: **FAIL** |
| a destination you cannot trace to its value, or a part of the diff you cannot read | **no PASS** until it is traced or read |
| it was there before and the pull request leaves it as it is | `Residual`, and tell the CTO/CEO. On a public repository name the area only, with no way to exploit it |

A real secret you come across is **never repeated** in a comment, a report, a message or a commit: give the file, the
line and the kind, and say that it must be rotated.

## One good, one bad

- **Good:** "`export.go:41` posts `user.email` to `hooks.vendor.test`. `issue_gate.py asked 12` prints an issue that
  asks for order ids only. Local receiver captured `{"id":…,"email":…}`. FAIL: send the id only."
- **Bad:** "The scan listed nothing and the code looks fine: PASS." A clean scan is no check, and nobody looked at what
  the diff sends.
