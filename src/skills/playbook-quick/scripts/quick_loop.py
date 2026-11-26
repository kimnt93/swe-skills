#!/usr/bin/env python3
"""The two rules of playbook-quick that must not depend on memory: the feedback limit and safe worktree removal.

    quick_loop.py state --pr 54 --repo owner/repo
    quick_loop.py decide --pr 54 --repo owner/repo --body-file decision.md     (before posting a decision)
    quick_loop.py can-remove --worktree <path> [--pr 54 --repo owner/repo]     (before removing a worktree)
    quick_loop.py --self-test

A round is a 'Changes required ... Round K of 3.' decision on one head SHA. After the last round the CTO/CEO either
accepts or posts 'Stopped by'. Only decisions from the repository's owners, members and collaborators count.
`can-remove` allows removal only when nothing would be lost: a clean tree, every local commit on GitHub, and the PR
merged or stopped (without --pr: the current branch is pushed). It never removes anything itself.
Exit 0 = allowed, 1 = refused (reasons printed), 2 = usage. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# the round limit lives with the one linter; an installed copy may prefix every skill directory
_OWN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_OWN.parent / _OWN.name.replace("playbook-quick", "work-package") / "scripts"))
from package_lint import MAX_ROUNDS  # noqa: E402

TRUSTED = ("OWNER", "MEMBER", "COLLABORATOR")
DECISION_RE = re.compile(
    r"^(?P<verb>Accepted|Changes required|Stopped) by (?:CTO|CEO) \(.+?\)\. PR #(?P<pr>\d+) at (?P<sha>[0-9a-f]{40})\."
    r"(?: Round (?P<round>\d+) of \d+\.)?\s*$"
)


def first_line(body: str) -> str:
    return body.lstrip().split("\n", 1)[0].rstrip("\r")


def decisions(entries: list[dict], pr: int) -> list[dict]:
    """The trusted decisions on this PR, oldest first. entries: {body, authorAssociation, at}."""
    found = []
    for entry in sorted(entries, key=lambda e: e.get("at") or ""):
        match = DECISION_RE.match(first_line(entry.get("body") or ""))
        if match and int(match["pr"]) == pr and entry.get("authorAssociation") in TRUSTED:
            found.append({"verb": match["verb"], "sha": match["sha"], "round": match["round"]})
    return found


def rounds_used(past: list[dict]) -> list[str]:
    """The head SHAs that got a change request, in order. Two requests on one SHA are one round."""
    return list(dict.fromkeys(d["sha"] for d in past if d["verb"] == "Changes required"))


def stopped(past: list[dict]) -> bool:
    return any(d["verb"] == "Stopped" for d in past)


def check_decision(past: list[dict], body: str, pr: int, head: str) -> list[str]:
    """Why this decision may not be posted. Empty: post it."""
    match = DECISION_RE.match(first_line(body))
    if not match or int(match["pr"]) != pr:
        return [f"first line is not a decision on PR #{pr}: '<Accepted|Changes required|Stopped> by CTO (<name>). "
                f"PR #{pr} at <40-character sha>.' (a change request adds ' Round K of {MAX_ROUNDS}.')"]
    if stopped(past):
        return ["this PR is stopped: no further decision; restarting it is the human's call"]
    problems = []
    if match["sha"] != head:
        problems.append(f"the decision names {match['sha'][:8]} but the head is {head[:8]}: check the head")
    used = rounds_used(past)
    if match["verb"] == "Changes required":
        number = used.index(match["sha"]) + 1 if match["sha"] in used else len(used) + 1
        if number > MAX_ROUNDS:
            problems.append(f"{MAX_ROUNDS} rounds are used: accept, or post 'Stopped by'")
        elif match["round"] != str(number):
            problems.append(f"this is round {number} of {MAX_ROUNDS}, not {match['round'] or 'unnumbered'}")
    return problems


def describe(past: list[dict], head: str) -> str:
    used = len(rounds_used(past))
    lines = [f"rounds used: {used} of {MAX_ROUNDS}"]
    if stopped(past):
        lines.append("state: STOPPED. Developer stops and removes its worktree; the PR and branch stay.")
    elif past and past[-1]["sha"] == head and past[-1]["verb"] == "Accepted":
        lines.append("state: ACCEPTED at the head. Merge it.")
    elif past and past[-1]["sha"] == head:
        lines.append("state: changes required on the head. The developer is fixing.")
    elif used < MAX_ROUNDS:
        lines.append(f"state: head not decided. Accept, or request changes as 'Round {used + 1} of {MAX_ROUNDS}'.")
    else:
        lines.append("state: head not decided. LAST CHECK: accept, or post 'Stopped by'.")
    return "\n".join(lines)


def removal_problems(dirty: str, local_head: str, pr: dict | None, was_stopped: bool, remote_sha: str) -> list[str]:
    """Why removing the worktree could lose work or end it too early. Empty: safe to remove."""
    problems = []
    if dirty.strip():
        problems.append("the worktree has uncommitted or untracked files: commit and push them (or delete what is "
                        "really junk):\n" + dirty.rstrip())
    if pr is None:
        if remote_sha != local_head:
            problems.append("the branch is not fully pushed: origin does not have the local head")
        return problems
    if pr["headRefOid"] != local_head:
        problems.append(f"the local head {local_head[:8]} is not the PR's head {pr['headRefOid'][:8]}: push (or fetch)")
    if pr["state"] != "MERGED":
        if not was_stopped:
            problems.append("the PR is neither merged nor stopped: keep the worktree")
        if remote_sha != local_head:
            problems.append("the PR is not merged and origin's branch does not hold the local head: keep the branch")
    return problems


def run(*args: str, cwd: str | None = None) -> str:
    return subprocess.run(list(args), capture_output=True, text=True, check=True, cwd=cwd).stdout


def read_pr(number: int, repo: str) -> tuple[dict, list[dict]]:
    data = json.loads(run("gh", "pr", "view", str(number), "--repo", repo, "--json",
                          "state,headRefOid,headRefName,comments,reviews"))
    entries = [{**c, "at": c.get("createdAt")} for c in data["comments"]]
    entries += [{**r, "at": r.get("submittedAt")} for r in data["reviews"]]
    return data, decisions(entries, number)


def worktree_facts(path: str, branch: str | None) -> tuple[str, str, str]:
    """(uncommitted files, local head, the head origin holds for the branch or '')."""
    dirty = run("git", "status", "--porcelain", "--untracked-files=all", cwd=path)
    head = run("git", "rev-parse", "HEAD", cwd=path).strip()
    branch = branch or run("git", "rev-parse", "--abbrev-ref", "HEAD", cwd=path).strip()
    remote = run("git", "ls-remote", "--heads", "origin", f"refs/heads/{branch}", cwd=path).split()
    return dirty, head, remote[0] if remote else ""


def self_test() -> int:
    a, b, c, d = ("a" * 40, "b" * 40, "c" * 40, "d" * 40)

    def say(verb: str, sha: str, number: int | None = None, who: str = "OWNER", at: str = "") -> dict:
        tail = f" Round {number} of {MAX_ROUNDS}." if number else ""
        return {"body": f"{verb} by CTO (Boss (CTO)). PR #54 at {sha}.{tail}\n\ntext", "authorAssociation": who,
                "at": at or sha}

    def text(verb: str, sha: str, number: int | None = None) -> str:
        return say(verb, sha, number)["body"]

    assert MAX_ROUNDS == 3
    assert decisions([say("Changes required", a, 1, who="NONE")], 54) == [], "an outsider cannot spend a round"
    assert decisions([say("Changes required", a, 1)], 55) == [], "another PR's decision"
    assert check_decision([], text("Changes required", a, 1), 54, a) == []
    assert "round 1 of 3" in check_decision([], text("Changes required", a, 2), 54, a)[0]
    assert "unnumbered" in check_decision([], text("Changes required", a), 54, a)[0]
    assert "head is" in check_decision([], text("Accepted", a), 54, b)[0], "stale SHA"
    two = decisions([say("Changes required", b, 2), say("Changes required", a, 1)], 54)
    assert rounds_used(two) == [a, b], "ordered by time"
    again = decisions([say("Changes required", a, 1), say("Changes required", a, 1, at="z")], 54)
    assert rounds_used(again) == [a], "two requests on one head are one round"
    assert check_decision(two, text("Changes required", c, 3), 54, c) == []
    three = decisions([say("Changes required", a, 1), say("Changes required", b, 2), say("Changes required", c, 3)], 54)
    assert "3 rounds are used" in check_decision(three, text("Changes required", d, 3), 54, d)[0], "no fourth round"
    assert check_decision(three, text("Stopped", d), 54, d) == []
    assert check_decision(three, text("Accepted", d), 54, d) == []
    assert "LAST CHECK" in describe(three, d) and "developer is fixing" in describe(three, c)
    done = three + decisions([say("Stopped", d)], 54)
    assert "this PR is stopped" in check_decision(done, text("Accepted", d), 54, d)[0]
    assert "STOPPED" in describe(done, d)
    assert "first line is not a decision" in check_decision([], "Looks good", 54, a)[0]

    merged, opened = {"state": "MERGED", "headRefOid": a}, {"state": "OPEN", "headRefOid": a}
    assert removal_problems("", a, merged, False, "") == [], "merged, remote branch already deleted"
    assert removal_problems("", a, opened, True, a) == [], "stopped, branch on origin"
    assert "neither merged nor stopped" in removal_problems("", a, opened, False, a)[0]
    assert "uncommitted" in removal_problems("?? x\n", a, merged, False, "")[0]
    assert "not the PR's head" in removal_problems("", b, merged, False, "")[0], "a commit made after the merge"
    assert "keep the branch" in removal_problems("", a, opened, True, "")[0], "stopped but branch gone"
    assert "not fully pushed" in removal_problems("", a, None, False, b)[0]

    with tempfile.TemporaryDirectory() as tmp:
        origin, work = f"{tmp}/origin.git", f"{tmp}/work"
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
               "GIT_COMMITTER_EMAIL": "t@t"}
        git = lambda *x: subprocess.run(["git", *x], cwd=work, check=True, capture_output=True, env=env)
        subprocess.run(["git", "init", "-q", "--bare", origin], check=True)
        subprocess.run(["git", "init", "-q", "-b", "ord-02/x", work], check=True)
        git("remote", "add", "origin", origin)
        Path(work, "a").write_text("a\n"); git("add", "."); git("commit", "-qm", "one")
        assert removal_problems(*_facts_for_no_pr(work)) != [], "never pushed"
        git("push", "-q", "origin", "HEAD")
        assert removal_problems(*_facts_for_no_pr(work)) == [], "pushed and clean"
        Path(work, "new").write_text("n\n")
        assert "uncommitted" in removal_problems(*_facts_for_no_pr(work))[0], "untracked file"
        git("add", "."); git("commit", "-qm", "two")
        assert "not fully pushed" in removal_problems(*_facts_for_no_pr(work))[0], "unpushed commit"
    print("self-test passed: three rounds then accept or stop; removal only when nothing is lost")
    return 0


def _facts_for_no_pr(path: str):
    dirty, head, remote = worktree_facts(path, None)
    return dirty, head, None, False, remote


def main(argv: list[str]) -> int:
    if "--self-test" in argv[:1]:
        return self_test()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="mode", required=True)
    for mode in ("state", "decide", "can-remove"):
        p = sub.add_parser(mode)
        p.add_argument("--pr", type=int, required=mode != "can-remove")
        p.add_argument("--repo", required=mode != "can-remove")
        if mode == "decide":
            p.add_argument("--body-file", required=True)
        if mode == "can-remove":
            p.add_argument("--worktree", required=True)
    args = parser.parse_args(argv)
    if args.mode == "can-remove":
        if args.pr is not None and not args.repo:
            parser.error("--pr needs --repo")
        pr, past = read_pr(args.pr, args.repo) if args.pr is not None else (None, [])
        dirty, head, remote = worktree_facts(args.worktree, pr["headRefName"] if pr else None)
        problems = removal_problems(dirty, head, pr, stopped(past), remote)
        ok = "safe to remove"
    else:
        pr, past = read_pr(args.pr, args.repo)
        if args.mode == "state":
            print(describe(past, pr["headRefOid"]))
            return 0
        problems = check_decision(past, Path(args.body_file).read_text(encoding="utf-8"), args.pr, pr["headRefOid"])
        ok = "decision allowed"
    for problem in problems:
        print("REFUSED", problem)
    if not problems:
        print(ok)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
