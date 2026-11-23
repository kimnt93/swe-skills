#!/usr/bin/env python3
"""Check the text and names of a work package: the work-package skill's format, enforced.

    package_lint.py issue --title "API-03: Cancel an open order" --label backend --label medium --label orders --body-file issue.md
    package_lint.py branch api-03/cancel-order
    package_lint.py commit "feat(api-03): add the cancel route"
    package_lint.py pr --branch api-03/cancel-order --title "feat(api-03): add the cancel route" --body-file pr.md
    package_lint.py --self-test

Exit 0 = clean, 1 = findings (one per line), 2 = usage. Standard library only.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

TYPES = ("feat", "fix", "refactor", "perf", "test", "docs", "chore", "ci", "build")
LANES = ("backend", "frontend", "data", "ops", "docs", "test", "research")
DIFFICULTIES = ("simple", "medium", "hard")
TITLE_RE = re.compile(r"^(?P<id>[A-Z][A-Z0-9]{1,7}-\d{2,4}): (?P<text>\S.*)$")
BRANCH_RE = re.compile(r"^(?P<id>[a-z][a-z0-9]{1,7}-\d{2,4})/[a-z0-9]+(-[a-z0-9]+){0,5}$")
COMMIT_RE = re.compile(rf"^({'|'.join(TYPES)})\((?P<id>[a-z][a-z0-9]{{1,7}}-\d{{2,4}})\)!?: (?P<subject>\S.*)$")
HEADER_RE = {
    "Lane": re.compile(r"^Lane: (\S+)\s*$", re.M),
    "Wave": re.compile(r"^Wave: (\d+)\s*$", re.M),
    "Difficulty": re.compile(r"^Difficulty: (simple|medium|hard)\b", re.M),
}
ORDER = ["Goal", "Status", "Read first", "Owned files", "Forbidden", "Depends on", "Notes", "Done when", "Branch and PR"]
REQUIRED = ("Goal", "Read first", "Owned files", "Forbidden", "Done when", "Branch and PR")
PR_SECTIONS = ("Summary", "Files changed", "Done-when evidence")
CLOSE_RE = re.compile(r"^(Closes|Refs) #\d+\s*$", re.M)
SECRET_RE = re.compile(
    r"(?i)(ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|(?:token|password|secret)\s*[:=]\s*\S{8,})"
)


def section_names(body: str) -> list[str]:
    return [m.group(1).split(" (")[0].strip() for m in re.finditer(r"^## (.+)$", body, re.M)]


def section_text(body: str, name: str) -> str | None:
    found = re.search(rf"^## {re.escape(name)}\b.*?(?=^## |\Z)", body, re.M | re.S)
    return found.group(0) if found else None


def lint_issue(title: str, labels: list[str], body: str) -> list[str]:
    problems: list[str] = []
    match = TITLE_RE.match(title)
    if not match:
        problems.append(f"title {title!r} is not 'ID: title' with an ID like API-03 (area in capitals, hyphen, 2+ digits)")
    else:
        text = match.group("text")
        if not 4 <= len(text) <= 90:
            problems.append(f"title text is {len(text)} chars (4 to 90)")
        if text.endswith("."):
            problems.append("title ends with a period")
        if re.match(rf"^({'|'.join(TYPES)})(\(|:)", text):
            problems.append("title carries a commit type prefix; an issue title is 'ID: outcome'")
    lanes = [x for x in labels if x in LANES]
    diffs = [x for x in labels if x in DIFFICULTIES]
    areas = [x for x in labels if x not in LANES and x not in DIFFICULTIES]
    if len(lanes) != 1:
        problems.append(f"labels need exactly one lane of {', '.join(LANES)} (got {lanes or 'none'})")
    if len(diffs) != 1:
        problems.append(f"labels need exactly one difficulty of {', '.join(DIFFICULTIES)} (got {diffs or 'none'})")
    if not areas:
        problems.append("labels need at least one area label")
    for key, pattern in HEADER_RE.items():
        found = pattern.search(body)
        if not found:
            problems.append(f"body has no '{key}: ...' header line")
        elif key == "Lane" and lanes and found.group(1) != lanes[0]:
            problems.append(f"body Lane is {found.group(1)!r} but the lane label is {lanes[0]!r}")
        elif key == "Difficulty" and diffs and found.group(1) != diffs[0]:
            problems.append(f"body Difficulty is {found.group(1)!r} but the difficulty label is {diffs[0]!r}")
    names = section_names(body)
    for required in REQUIRED:
        if required not in names:
            problems.append(f"body has no '## {required}' section")
    ranks = [ORDER.index(n) for n in names if n in ORDER]
    if ranks != sorted(ranks):
        problems.append("body sections are out of order (" + ", ".join(ORDER) + ")")
    done = section_text(body, "Done when")
    if done is not None and "`" not in done:
        problems.append("'Done when' has no command in backticks: it must be runnable")
    owned = section_text(body, "Owned files")
    if owned is not None and "- `" not in owned:
        problems.append("'Owned files' lists no file as - `path`")
    if SECRET_RE.search(body):
        problems.append("body looks like it contains a secret")
    return problems


def lint_branch(branch: str) -> list[str]:
    if BRANCH_RE.match(branch):
        return []
    return [f"branch {branch!r} is not <id>/<slug>, e.g. api-03/cancel-order (id lowercase, slug of 1 to 6 words)"]


def lint_commit(line: str) -> list[str]:
    match = COMMIT_RE.match(line)
    if not match:
        return [f"{line!r} is not '<type>(<id>): <summary>', e.g. feat(api-03): add the cancel route"]
    problems: list[str] = []
    subject = match.group("subject")
    if len(subject) > 72:
        problems.append(f"summary is {len(subject)} chars (max 72)")
    if subject.endswith("."):
        problems.append("summary ends with a period")
    return problems


def lint_pr(branch: str, title: str, body: str) -> list[str]:
    problems = lint_branch(branch) + lint_commit(title)
    branch_id = BRANCH_RE.match(branch)
    title_id = COMMIT_RE.match(title)
    if branch_id and title_id and branch_id.group("id") != title_id.group("id"):
        problems.append(f"branch id {branch_id.group('id')!r} differs from the title scope {title_id.group('id')!r}")
    names = section_names(body)
    for required in PR_SECTIONS:
        if required not in names:
            problems.append(f"body has no '## {required}' section")
    if not CLOSE_RE.search(body):
        problems.append("body has no closing line 'Closes #N' (or 'Refs #N' for partial work)")
    evidence = section_text(body, "Done-when evidence")
    if evidence is not None and ("```" not in evidence or not re.search(r"\b[0-9a-f]{7,40}\b", evidence)):
        problems.append("'Done-when evidence' needs the commit sha and fenced output tails")
    if SECRET_RE.search(body):
        problems.append("body looks like it contains a secret")
    return problems


GOOD_ISSUE = """Lane: backend
Wave: 1
Difficulty: medium (a route with storage)

## Goal
Cancel an open order.

## Read first
- `AGENTS.md`

## Owned files (create or change only these)
- `src/orders/cancel.py` (new)

## Forbidden
- every file not listed above

## Depends on
- nothing; start now

## Done when (run from the repository root)
- `pytest -q tests/test_cancel.py`

## Branch and PR
- Branch `api-03/cancel-order` from `main`; do not merge it.
"""
GOOD_PR = """## Summary

Adds the cancel route.

## Files changed

- `src/orders/cancel.py` (new)

## Done-when evidence

All commands ran on commit `a1b2c3d4`.

### `pytest -q tests/test_cancel.py`

```
1 passed
```

Closes #12
"""
TITLE = "feat(api-03): add the cancel route"
BRANCH = "api-03/cancel-order"
ISSUE_TITLE = "API-03: Cancel an open order"


def self_test() -> int:
    failures: list[str] = []

    def expect(name: str, got: list[str], needle: str = "") -> None:
        if not needle and got:
            failures.append(f"{name}: expected clean, got {got}")
        if needle and not any(needle in g for g in got):
            failures.append(f"{name}: expected a finding with {needle!r}, got {got}")

    labels = ["backend", "medium", "orders"]
    expect("good issue", lint_issue(ISSUE_TITLE, labels, GOOD_ISSUE))
    expect("bad id", lint_issue("api3: Cancel", labels, GOOD_ISSUE), "not 'ID: title'")
    expect("type prefix", lint_issue("API-03: feat: cancel it", labels, GOOD_ISSUE), "commit type prefix")
    expect("no lane", lint_issue(ISSUE_TITLE, ["medium", "orders"], GOOD_ISSUE), "exactly one lane")
    expect("two difficulties", lint_issue(ISSUE_TITLE, labels + ["hard"], GOOD_ISSUE), "exactly one difficulty")
    expect("no area", lint_issue(ISSUE_TITLE, ["backend", "medium"], GOOD_ISSUE), "at least one area")
    expect("lane mismatch", lint_issue(ISSUE_TITLE, ["frontend", "medium", "ui"], GOOD_ISSUE), "Lane is")
    missing = GOOD_ISSUE.replace("## Forbidden\n- every file not listed above\n\n", "")
    expect("missing section", lint_issue(ISSUE_TITLE, labels, missing), "no '## Forbidden'")
    unrunnable = GOOD_ISSUE.replace("`pytest -q tests/test_cancel.py`", "it works")
    expect("unrunnable done", lint_issue(ISSUE_TITLE, labels, unrunnable), "runnable")
    shuffled = GOOD_ISSUE.replace("## Goal\nCancel an open order.\n\n", "") + "\n## Goal\nlate\n"
    expect("order", lint_issue(ISSUE_TITLE, labels, shuffled), "out of order")
    expect("secret", lint_issue(ISSUE_TITLE, labels, GOOD_ISSUE + "\ntoken = abcdefgh12345678\n"), "secret")
    expect("good branch", lint_branch(BRANCH))
    expect("type branch", lint_branch("feat/cancel-order"), "not <id>/<slug>")
    expect("upper branch", lint_branch("API-03/cancel-order"), "not <id>/<slug>")
    expect("good commit", lint_commit(TITLE))
    expect("commit no scope", lint_commit("feat: add the cancel route"), "not '<type>(<id>)")
    expect("commit period", lint_commit(TITLE + "."), "period")
    expect("good pr", lint_pr(BRANCH, TITLE, GOOD_PR))
    expect("pr id mismatch", lint_pr("api-04/cancel-order", TITLE, GOOD_PR), "differs")
    expect("pr no close", lint_pr(BRANCH, TITLE, GOOD_PR.replace("Closes #12\n", "")), "closing line")
    expect("pr no evidence", lint_pr(BRANCH, TITLE, GOOD_PR.replace("```\n1 passed\n```\n", "")), "fenced output")
    expect("pr no summary", lint_pr(BRANCH, TITLE, GOOD_PR.replace("## Summary", "## Why")), "no '## Summary'")
    if failures:
        print("\n".join(failures))
        return 1
    print("package_lint self-test: ok")
    return 0


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--self-test":
        return self_test()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    issue = sub.add_parser("issue")
    issue.add_argument("--title", required=True)
    issue.add_argument("--label", action="append", default=[])
    issue.add_argument("--body-file", required=True)
    branch = sub.add_parser("branch")
    branch.add_argument("name")
    commit = sub.add_parser("commit")
    commit.add_argument("line")
    pr = sub.add_parser("pr")
    pr.add_argument("--branch", required=True)
    pr.add_argument("--title", required=True)
    pr.add_argument("--body-file", required=True)
    try:
        args = parser.parse_args(argv)
    except SystemExit as stop:
        return 2 if stop.code else 0
    if args.cmd == "issue":
        problems = lint_issue(args.title, args.label, Path(args.body_file).read_text(encoding="utf-8"))
    elif args.cmd == "branch":
        problems = lint_branch(args.name)
    elif args.cmd == "commit":
        problems = lint_commit(args.line)
    else:
        problems = lint_pr(args.branch, args.title, Path(args.body_file).read_text(encoding="utf-8"))
    for problem in problems:
        print(problem)
    if not problems:
        print("package_lint: clean")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
