#!/usr/bin/env python3
"""Check a submission before (and after) it is opened: the github skill's submit rules, enforced.

    pr_lint.py local --body pr.md [--allow 'internal/orders/**' ...] [--max-lines 400]
    pr_lint.py pr <number> [--repo owner/repo] [--allow ...] [--max-lines 400]
    pr_lint.py --self-test

Checks:
  * branch is <type>/<issue>-<slug> (types: feat fix refactor perf test docs chore ci build)
  * title is a Conventional Commit: <type>(<scope>): <subject>, subject <= 72 chars, no trailing period
  * body has the sections ## Why, ## What changed, ## Verification, and links an issue (Closes #N / Refs #N)
  * the diff is small: added + deleted lines <= --max-lines (label size:large lifts it on a PR)
  * every changed file matches an --allow glob (the card's "may write"), when globs are given
  * no changed file is generated or secret-looking (.env, *.pem, dist/, node_modules/)
Exit 0 = clean, 1 = findings, 2 = usage. Standard library only.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

TYPES = ("feat", "fix", "refactor", "perf", "test", "docs", "chore", "ci", "build")
BRANCH_RE = re.compile(rf"^({'|'.join(TYPES)})/\d+-[a-z0-9]+(-[a-z0-9]+)*$")
TITLE_RE = re.compile(rf"^({'|'.join(TYPES)})(\([a-z0-9-]+\))?!?: (?P<subject>.+)$")
SECTIONS = ("## Why", "## What changed", "## Verification")
ISSUE_RE = re.compile(r"\b(Closes|Fixes|Resolves|Refs) #\d+\b")
FORBIDDEN = (".env", "*.pem", "*.key", "dist/*", "node_modules/*", ".next/*", "*.tsbuildinfo")


def lint(branch: str, title: str, body: str, files: list[str], changed: int, allow: list[str],
         max_lines: int, large_ok: bool = False) -> list[str]:
    problems = []
    if not BRANCH_RE.match(branch):
        problems.append(f"branch {branch!r} is not <type>/<issue>-<slug>, e.g. feat/42-cancel-order")
    match = TITLE_RE.match(title)
    if not match:
        problems.append(f"title {title!r} is not a Conventional Commit: <type>(<scope>): <subject>")
    else:
        subject = match.group("subject")
        if len(subject) > 72:
            problems.append(f"title subject is {len(subject)} chars (max 72)")
        if subject.endswith("."):
            problems.append("title subject ends with a period")
    for section in SECTIONS:
        if section not in body:
            problems.append(f"body has no {section!r} section")
    if not ISSUE_RE.search(body):
        problems.append("body links no issue: add 'Closes #N' (or 'Refs #N' for partial work)")
    if changed > max_lines and not large_ok:
        problems.append(f"diff is {changed} changed lines (max {max_lines}): split it into smaller PRs")
    for path in files:
        base = Path(path).name
        if any(fnmatch.fnmatch(path, g) or fnmatch.fnmatch(base, g) for g in FORBIDDEN):
            problems.append(f"{path}: generated or secret-looking file must not be committed")
        if allow and not any(fnmatch.fnmatch(path, g) for g in allow):
            problems.append(f"{path}: outside the card's scope ({', '.join(allow)})")
    return problems


def git(*args: str, cwd: str | None = None) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True, cwd=cwd).stdout


def local(args: argparse.Namespace) -> list[str]:
    base = args.base
    branch = git("rev-parse", "--abbrev-ref", "HEAD").strip()
    title = git("log", "-1", "--format=%s").strip() if not args.title else args.title
    files = [f for f in git("diff", "--name-only", f"{base}...HEAD").splitlines() if f]
    changed = 0
    for line in git("diff", "--numstat", f"{base}...HEAD").splitlines():
        added, deleted, _ = line.split("\t", 2)
        changed += int(added) + int(deleted) if added != "-" else 0
    body = Path(args.body).read_text(encoding="utf-8") if args.body else ""
    return lint(branch, title, body, files, changed, args.allow, args.max_lines)


def remote(args: argparse.Namespace) -> list[str]:
    cmd = ["gh", "pr", "view", str(args.number), "--json", "headRefName,title,body,files,additions,deletions,labels"]
    if args.repo:
        cmd += ["--repo", args.repo]
    data = json.loads(subprocess.run(cmd, capture_output=True, text=True, check=True).stdout)
    files = [f["path"] for f in data.get("files", [])]
    labels = {label["name"] for label in data.get("labels", [])}
    return lint(data["headRefName"], data["title"], data.get("body") or "", files,
                data.get("additions", 0) + data.get("deletions", 0), args.allow, args.max_lines, "size:large" in labels)


def self_test() -> int:
    good_body = "## Why\nOrders could not be cancelled.\n\n## What changed\n- add DELETE /v1/orders/{id}\n\n## Verification\nmake verify: ok\n\nCloses #42\n"
    ok = lint("feat/42-cancel-order", "feat(orders): cancel an open order", good_body,
              ["internal/orders/cancel.go"], 120, ["internal/orders/**"], 400)
    assert ok == [], ok
    bad = lint("my-branch", "Added cancel.", "did stuff", ["internal/risk/limits.go", ".env"], 900, ["internal/orders/**"], 400)
    joined = "\n".join(bad)
    for want in ("branch", "Conventional Commit", "## Why", "links no issue", "900 changed lines",
                 "outside the card's scope", "secret-looking"):
        assert want in joined, (want, joined)
    assert lint("fix/7-x", "fix: " + "a" * 80, good_body, [], 1, [], 400)[0].startswith("title subject is"), "subject length"
    assert not lint("feat/42-cancel-order", "feat(orders): cancel", good_body, [], 900, [], 400, large_ok=True), "size:large"
    with tempfile.TemporaryDirectory() as tmp:
        run = lambda *a: subprocess.run(["git", *a], cwd=tmp, check=True, capture_output=True)
        run("init", "-q", "-b", "main"); run("config", "user.email", "t@t"); run("config", "user.name", "t")
        Path(tmp, "a.txt").write_text("a\n"); run("add", "."); run("commit", "-qm", "chore: init")
        run("switch", "-qc", "feat/42-cancel-order")
        Path(tmp, "internal").mkdir(); Path(tmp, "internal", "x.go").write_text("package x\n" * 3)
        run("add", "."); run("commit", "-qm", "feat(orders): cancel an open order")
        body = Path(tmp, "body.md"); body.write_text(good_body)
        result = subprocess.run([sys.executable, __file__, "local", "--base", "main", "--body", str(body), "--allow", "internal/**"],
                                cwd=tmp, capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
        result = subprocess.run([sys.executable, __file__, "local", "--base", "main", "--body", str(body), "--allow", "web/**"],
                                cwd=tmp, capture_output=True, text=True)
        assert result.returncode == 1 and "outside the card's scope" in result.stdout, result.stdout
    print("self-test passed: branch, title, body sections, issue link, size, scope, secrets; local git mode")
    return 0


def main() -> int:
    if "--self-test" in sys.argv[1:]:
        return self_test()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="mode", required=True)
    for name in ("local", "pr"):
        p = sub.add_parser(name)
        p.add_argument("--allow", action="append", default=[], help="glob a changed file must match (repeatable)")
        p.add_argument("--max-lines", type=int, default=400)
        if name == "local":
            p.add_argument("--body", help="the PR body file")
            p.add_argument("--title", help="the PR title (default: the last commit subject)")
            p.add_argument("--base", default="origin/main")
        else:
            p.add_argument("number")
            p.add_argument("--repo")
    args = parser.parse_args()
    problems = local(args) if args.mode == "local" else remote(args)
    for problem in problems:
        print("PROBLEM", problem)
    print(f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
