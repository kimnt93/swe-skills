#!/usr/bin/env python3
"""Make every commit and every published text carry the agent's own name.

    agent_identity.py name  [--author NAME]
    agent_identity.py git   [--author NAME] -- commit -m "feat(api-03): ..."     (also: rebase, merge, cherry-pick, revert)
    agent_identity.py stamp [--author NAME] note.md                              (sets the last line 'Created: NAME')
    agent_identity.py check [--author NAME] [--also-author NAME] [--base origin/main]
    agent_identity.py --self-test

NAME is the agent's own name, exactly as its instructions give it, e.g. "Release Bot (Developer)". It comes from
--author, else the AGENT_NAME environment variable. There is no fallback to the git configuration: that is the human.
The email is AGENT_EMAIL, else <slug of the name>@agents.invalid (a reserved domain, so no account is claimed by it).
`git` sets the author and the committer through the environment and never edits the git configuration.
Exit 0 = ok, 1 = findings, 2 = usage or no name. Standard library only.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ALLOWED_GIT = ("commit", "rebase", "merge", "cherry-pick", "revert")
CREATED_RE = re.compile(r"^Created: .*$\n?", re.M)


class IdentityError(Exception):
    pass


def configured_user(cwd: str | None = None) -> str:
    """The git user.name of this checkout: the human. GIT_* variables do not change it."""
    run = subprocess.run(["git", "config", "--get", "user.name"], capture_output=True, text=True, cwd=cwd)
    return run.stdout.strip()


def resolve_name(author: str | None, cwd: str | None = None) -> str:
    name = (author or os.environ.get("AGENT_NAME", "")).strip()
    if not name:
        raise IdentityError("no agent name: pass --author \"<your agent name>\" or set AGENT_NAME")
    if any(c in name for c in "<>\n\r"):
        raise IdentityError(f"agent name {name!r} is a placeholder or has characters git does not allow")
    human = configured_user(cwd)
    if human and name.casefold() == human.casefold():
        raise IdentityError(f"{name!r} is the git user of this machine, not an agent name")
    return name


def email_for(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "agent"
    return os.environ.get("AGENT_EMAIL", "").strip() or f"{slug}@agents.invalid"


def identity_env(name: str) -> dict[str, str]:
    email = email_for(name)
    return {**os.environ, "GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email,
            "GIT_COMMITTER_NAME": name, "GIT_COMMITTER_EMAIL": email}


def run_git(name: str, args: list[str], cwd: str | None = None) -> int:
    if not args or args[0] not in ALLOWED_GIT:
        raise IdentityError(f"`git` takes one of {', '.join(ALLOWED_GIT)}")
    if any(a == "--author" or a.startswith("--author=") for a in args):
        raise IdentityError("do not pass --author to git: the agent name is set for you")
    return subprocess.run(["git", *args], env=identity_env(name), cwd=cwd).returncode


def stamp(name: str, text: str) -> str:
    """Return the text with exactly one 'Created: name' as its last line. Another agent's signature is refused."""
    others = [x for x in re.findall(r"^Created: (.*?)\s*$", text, re.M) if x != name and "<" not in x]
    if others:
        raise IdentityError(f"the text is already signed by {others[0]!r}: write your own, do not re-sign another's")
    return CREATED_RE.sub("", text).rstrip() + f"\n\nCreated: {name}\n"


def check_commits(names: list[str], base: str, cwd: str | None = None) -> list[str]:
    log = subprocess.run(["git", "log", "--format=%h%x1f%an%x1f%cn%x1f%s", f"{base}..HEAD"],
                         capture_output=True, text=True, check=True, cwd=cwd).stdout
    problems = []
    for line in log.splitlines():
        sha, author, committer, subject = line.split("\x1f", 3)
        for role, who in (("author", author), ("committer", committer)):
            if who not in names:
                problems.append(f"{sha} {subject!r}: {role} is {who!r}, not {' or '.join(repr(n) for n in names)}")
    return problems


def self_test() -> int:
    for key in ("AGENT_NAME", "AGENT_EMAIL"):
        os.environ.pop(key, None)
    name = "Release Bot (Developer)"

    def refused(call) -> bool:
        try:
            call()
        except IdentityError:
            return True
        return False

    with tempfile.TemporaryDirectory() as tmp:
        git = lambda *a: subprocess.run(["git", *a], cwd=tmp, check=True, capture_output=True, text=True).stdout
        git("init", "-q", "-b", "main")
        git("config", "user.name", "Human Owner")
        git("config", "user.email", "owner@example.com")
        Path(tmp, "a").write_text("a\n"); git("add", "."); git("commit", "-qm", "chore: base")
        git("switch", "-qc", "work")
        assert refused(lambda: resolve_name(None, tmp)), "no name"
        assert refused(lambda: resolve_name("human owner", tmp)), "the human's name"
        assert refused(lambda: resolve_name("<your name>", tmp)), "placeholder"
        assert refused(lambda: run_git(name, ["push"], tmp)), "only history-writing commands"
        assert refused(lambda: run_git(name, ["commit", "--author=x <y@z>"], tmp)), "no --author"
        Path(tmp, "b").write_text("b\n"); git("add", ".")
        assert run_git(name, ["commit", "-qm", "feat: b"], tmp) == 0
        who = git("log", "-1", "--format=%an|%ae|%cn|%ce").strip()
        assert who == f"{name}|release-bot-developer@agents.invalid|{name}|release-bot-developer@agents.invalid", who
        assert check_commits([name], "main", tmp) == []
        assert git("config", "user.name").strip() == "Human Owner", "the configuration is untouched"
        Path(tmp, "c").write_text("c\n"); git("add", "."); git("commit", "-qm", "feat: c")
        found = check_commits([name], "main", tmp)
        assert len(found) == 2 and "Human Owner" in found[0], found
        assert check_commits([name, "Human Owner"], "main", tmp) == []
    assert stamp(name, "text\n") == f"text\n\nCreated: {name}\n"
    assert stamp(name, stamp(name, "text")) == stamp(name, "text"), "stamping twice is the same"
    assert stamp(name, "text\n\nCreated: <your name>\n") == stamp(name, "text"), "a template placeholder is filled"
    assert refused(lambda: stamp(name, "text\nCreated: Other Bot\n")), "never re-sign another agent's text"
    os.environ["AGENT_EMAIL"] = "bot@example.com"
    assert email_for(name) == "bot@example.com"
    os.environ.pop("AGENT_EMAIL")
    print("self-test passed: name required, never the human's, author and committer set, commit check, signature")
    return 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv[:1]:
        return self_test()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="mode", required=True)
    for mode in ("name", "git", "stamp", "check"):
        p = sub.add_parser(mode)
        p.add_argument("--author")
        if mode == "git":
            p.add_argument("args", nargs=argparse.REMAINDER)
        if mode == "stamp":
            p.add_argument("file")
        if mode == "check":
            p.add_argument("--also-author", action="append", default=[], help="another agent who committed on this branch")
            p.add_argument("--base", default="origin/main")
    args = parser.parse_args(argv)
    try:
        name = resolve_name(args.author)
        if args.mode == "name":
            print(name)
        elif args.mode == "git":
            return run_git(name, args.args[1:] if args.args[:1] == ["--"] else args.args)
        elif args.mode == "stamp":
            path = Path(args.file)
            path.write_text(stamp(name, path.read_text(encoding="utf-8")), encoding="utf-8")
            print(f"signed: Created: {name}")
        else:
            problems = check_commits([name, *args.also_author], args.base)
            for problem in problems:
                print("PROBLEM", problem)
            print(f"{len(problems)} problem(s)")
            return 1 if problems else 0
    except IdentityError as error:
        print(f"agent_identity: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
