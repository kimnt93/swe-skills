#!/usr/bin/env python3
"""Check a submission before (and after) it is opened: the github skill's submit rules, enforced.

    pr_lint.py local --body pr.md [--allow 'internal/orders/**' ...] [--max-lines 400]
    pr_lint.py pr <number> [--repo owner/repo] [--allow ...] [--max-lines 400]
    pr_lint.py --self-test

Checks:
  * branch is <type>/<issue>-<slug> (types: feat fix refactor perf test docs chore ci build)
  * title is a Conventional Commit: <type>(<scope>): <subject>, subject <= 72 chars, no trailing period
  * the body follows the one PR template (work-package/assets/pr.template.md, read by package_lint.py): its sections,
    a 'Closes #N' / 'Refs #N' line, the signature and no "Generated with" footer
  * the diff is small: added + deleted lines <= --max-lines (label size:large lifts it on a PR)
  * every changed file matches an --allow glob (the card's "may write"), when globs are given
  * no changed file is generated or secret-looking (.env, *.pem, dist/, node_modules/)
  * the body's last line is 'Created: <agent name>' (equal to AGENT_NAME when set), and every commit of the branch
    is authored by that name (local mode also checks the committer); --also-author names another agent on the branch
Exit 0 = clean, 1 = findings, 2 = usage. Standard library only.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# the PR body rules live with the one linter; an installed copy may prefix every skill directory
_OWN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_OWN.parent / _OWN.name.replace("github", "work-package") / "scripts"))
import package_lint  # noqa: E402

TYPES = ("feat", "fix", "refactor", "perf", "test", "docs", "chore", "ci", "build")
BRANCH_RE = re.compile(rf"^(({'|'.join(TYPES)})/\d+-[a-z0-9]+(-[a-z0-9]+)*|[a-z][a-z0-9]{{1,7}}-\d{{2,4}}[a-z]?/[a-z0-9]+(-[a-z0-9]+)*)$")
TITLE_RE = re.compile(rf"^({'|'.join(TYPES)})(\([a-z0-9-]+\))?!?: (?P<subject>.+)$")
CREATED_RE = re.compile(r"^Created: ([^<\n]+?)\s*$")
FORBIDDEN = (".env", "*.pem", "*.key", "dist/*", "node_modules/*", ".next/*", "*.tsbuildinfo")


def lint(branch: str, title: str, body: str, files: list[str], changed: int, allow: list[str],
         max_lines: int, large_ok: bool = False) -> list[str]:
    problems = []
    if not BRANCH_RE.match(branch):
        problems.append(f"branch {branch!r} is not <type>/<issue>-<slug> (feat/42-cancel-order) or a work-package branch <id>/<slug> (api-03/cancel-order)")
    match = TITLE_RE.match(title)
    if not match:
        problems.append(f"title {title!r} is not a Conventional Commit: <type>(<scope>): <subject>")
    else:
        subject = match.group("subject")
        if len(subject) > 72:
            problems.append(f"title subject is {len(subject)} chars (max 72)")
        if subject.endswith("."):
            problems.append("title subject ends with a period")
    problems += package_lint.lint_pr_body(body)
    if changed > max_lines and not large_ok:
        problems.append(f"diff is {changed} changed lines (max {max_lines}): split it into smaller PRs")
    for path in files:
        base = Path(path).name
        if any(fnmatch.fnmatch(path, g) or fnmatch.fnmatch(base, g) for g in FORBIDDEN):
            problems.append(f"{path}: generated or secret-looking file must not be committed")
        if allow and not any(fnmatch.fnmatch(path, g) for g in allow):
            problems.append(f"{path}: outside the card's scope ({', '.join(allow)})")
    return problems


def lint_author(body: str, commits: list[tuple[str, list[str]]], also: list[str]) -> list[str]:
    """commits is [(short sha, names on that commit)]. Every name must be the signer or an --also-author."""
    lines = [x for x in body.splitlines() if x.strip()]
    signed = CREATED_RE.match(lines[-1]) if lines else None
    if not signed:
        return ["body's last line is not 'Created: <agent name>'"]
    name = signed.group(1)
    expected = os.environ.get("AGENT_NAME", "").strip()
    problems = []
    if expected and name != expected and expected not in also:
        problems.append(f"'Created: {name}' is not your agent name {expected!r} (AGENT_NAME)")
    for sha, names in commits:
        wrong = sorted({n for n in names if n not in [name, *also]})
        if wrong:
            problems.append(f"commit {sha} is not by the agent: {', '.join(wrong)} (commit with agent_identity.py git)")
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
    commits = []
    for line in git("log", "--format=%h%x1f%an%x1f%cn", f"{base}..HEAD").splitlines():
        sha, author, committer = line.split("\x1f")
        commits.append((sha, [author, committer]))
    return lint(branch, title, body, files, changed, args.allow, args.max_lines) + lint_author(body, commits, args.also_author)


def remote(args: argparse.Namespace) -> list[str]:
    cmd = ["gh", "pr", "view", str(args.number), "--json", "headRefName,title,body,files,additions,deletions,labels,commits"]
    if args.repo:
        cmd += ["--repo", args.repo]
    data = json.loads(subprocess.run(cmd, capture_output=True, text=True, check=True).stdout)
    files = [f["path"] for f in data.get("files", [])]
    labels = {label["name"] for label in data.get("labels", [])}
    # the host lists the authors of a commit (the first is its author; co-authors follow), not its committer
    commits = [(c["oid"][:8], [c["authors"][0].get("name", "")]) for c in data.get("commits", []) if c.get("authors")]
    body = data.get("body") or ""
    return lint(data["headRefName"], data["title"], body, files, data.get("additions", 0) + data.get("deletions", 0),
                args.allow, args.max_lines, "size:large" in labels) + lint_author(body, commits, args.also_author)


def self_test() -> int:
    os.environ.pop("AGENT_NAME", None)
    with tempfile.TemporaryDirectory() as folder:
        Path(folder, "pr.template.md").write_text(package_lint.FIXTURES["pr"], encoding="utf-8")
        os.environ["AGENT_TEMPLATES"] = folder
        return run_cases()


def run_cases() -> int:
    signed = "Builder (Developer)"
    assert lint_author("x\n\nCreated: Builder (Developer)\n", [("a1", [signed, signed])], []) == []
    assert "last line" in lint_author("x\n", [], [])[0]
    assert "not by the agent: Human" in lint_author("Created: Builder (Developer)", [("a1", ["Human", signed])], [])[0]
    assert lint_author("Created: Builder (Developer)", [("a1", ["Reviewer Bot"])], ["Reviewer Bot"]) == []
    good_body = "Closes #42\n\n## Why\nOrders could not be cancelled.\n\n## What changed\n- add DELETE /v1/orders/{id}\n\n## Scope\nCancel only.\n\n## Blast radius\nOpen orders.\n\n## Verification\n- `make verify`: ok\n\nCreated: Builder (Developer)\n"
    ok = lint("feat/42-cancel-order", "feat(orders): cancel an open order", good_body,
              ["internal/orders/cancel.go"], 120, ["internal/orders/**"], 400)
    assert ok == [], ok
    assert lint("api-03/cancel-order", "feat(api-03): cancel an open order", good_body, [], 120, [], 400) == [], "same body on a package branch"
    bad = lint("my-branch", "Added cancel.", "did stuff", ["internal/risk/limits.go", ".env"], 900, ["internal/orders/**"], 400)
    joined = "\n".join(bad)
    for want in ("branch", "Conventional Commit", "## Why", "no closing line", "900 changed lines",
                 "outside the card's scope", "secret-looking"):
        assert want in joined, (want, joined)
    assert lint("fix/7-x", "fix: " + "a" * 80, good_body, [], 1, [], 400)[0].startswith("title subject is"), "subject length"
    assert not lint("feat/42-cancel-order", "feat(orders): cancel", good_body, [], 900, [], 400, large_ok=True), "size:large"
    with tempfile.TemporaryDirectory() as tmp:
        run = lambda *a: subprocess.run(["git", *a], cwd=tmp, check=True, capture_output=True)
        run("init", "-q", "-b", "main"); run("config", "user.email", "t@t"); run("config", "user.name", signed)
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
    print("self-test passed: branch, title, body sections, issue link, size, scope, secrets; local git mode, agent author")
    return 0


def main() -> int:
    if "--self-test" in sys.argv[1:]:
        return self_test()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="mode", required=True)
    for name in ("local", "pr"):
        p = sub.add_parser(name)
        p.add_argument("--also-author", action="append", default=[], help="another agent who committed on this branch")
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
