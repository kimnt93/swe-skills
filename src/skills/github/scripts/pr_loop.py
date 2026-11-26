#!/usr/bin/env python3
"""The rules of a build playbook's review loop that must not depend on memory.

    pr_loop.py state --pr 54 --repo owner/repo
    pr_loop.py decide --pr 54 --repo owner/repo --body-file decision.md    (before posting a decision or verdict)
    pr_loop.py can-merge --pr 54 --repo owner/repo                        (before merging on someone's judgment)
    pr_loop.py can-remove --worktree <path> [--pr 54 --repo owner/repo] [--handover]
    pr_loop.py --self-test

A round is a 'Changes required ... Round K of 3.' decision (CTO/CEO) or a 'Verdict: FAIL at <sha>. Round K of 3.'
verdict (reviewer) on one head SHA. After the last round: pass it, or post 'Stopped by'. Only comments from the
repository's owners, members and collaborators count.

An approval ('Accepted by' or 'Verdict: PASS') must be signed by an agent that did not write the pull request, and
must name every commit its signer pushed to it, because nobody else checked those. `can-merge` allows a merge only
when the newest judgment is such an approval of the current head; it does not read checks or the issue
(`gh pr checks`, `issue_gate.py pr`). `can-remove` allows removal only when nothing would be lost: a clean tree,
every local commit on GitHub, and the PR merged or stopped (--handover: still open and fully pushed, another agent
takes the branch; without --pr: the current branch is pushed). Nothing here merges or removes anything.
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
sys.path.insert(0, str(_OWN.parent / _OWN.name.replace("github", "work-package") / "scripts"))
from package_lint import MAX_ROUNDS  # noqa: E402

TRUSTED = ("OWNER", "MEMBER", "COLLABORATOR")
DECISION_RE = re.compile(
    r"^(?:(?P<verb>Accepted|Changes required) by (?:CTO|CEO) \(.+?\)\.|(?P<stop>Stopped) by (?:CTO|CEO|reviewer) \(.+?\)\.)"
    r" PR #(?P<pr>\d+) at (?P<sha>[0-9a-f]{40})\.(?: Round (?P<round>\d+) of \d+\.)?\s*$"
)
VERDICT_RE = re.compile(r"^Verdict: (?P<verb>PASS|FAIL) at (?P<sha>[0-9a-f]{40})(?:\. Round (?P<round>\d+) of \d+\.)?\s*$")
CREATED_RE = re.compile(r"^Created: (.+?)\s*$")
APPROVALS = ("Accepted", "PASS")


def first_line(body: str) -> str:
    return body.lstrip().split("\n", 1)[0].rstrip("\r")


def signer(body: str) -> str:
    """The name on the last line's 'Created:', or ''."""
    lines = [x.rstrip("\r") for x in (body or "").splitlines() if x.strip()]
    match = CREATED_RE.match(lines[-1]) if lines else None
    return match.group(1) if match else ""


def parse(body: str, pr: int) -> dict | None:
    """The decision or verdict a comment on this PR makes, or None."""
    line = first_line(body)
    match = DECISION_RE.match(line)
    if match:
        if int(match["pr"]) != pr:
            return None
        return {"verb": match["verb"] or match["stop"], "sha": match["sha"], "round": match["round"], "body": body}
    match = VERDICT_RE.match(line)
    if match:
        return {"verb": match["verb"], "sha": match["sha"], "round": match["round"], "body": body}
    return None


def decisions(entries: list[dict], pr: int) -> list[dict]:
    """The trusted judgments on this PR, oldest first. entries: {body, authorAssociation, at}."""
    found = []
    for entry in sorted(entries, key=lambda e: e.get("at") or ""):
        item = parse(entry.get("body") or "", pr)
        if item and entry.get("authorAssociation") in TRUSTED:
            found.append(item)
    return found


def asks_change(item: dict) -> bool:
    """Whether it spends a round. A review-only FAIL has no round number and spends none."""
    return item["verb"] == "Changes required" or (item["verb"] == "FAIL" and bool(item["round"]))


def rounds_used(past: list[dict]) -> list[str]:
    """The head SHAs that got a change request, in order. Two requests on one SHA are one round."""
    return list(dict.fromkeys(d["sha"] for d in past if asks_change(d)))


def stopped(past: list[dict]) -> bool:
    return any(d["verb"] == "Stopped" for d in past)


def authors(pr: dict) -> list[tuple[str, str]]:
    """(sha, author name) of each commit, oldest first."""
    return [(c["oid"], c["authors"][0].get("name", "")) for c in pr.get("commits", []) if c.get("authors")]


def residual(body: str) -> str:
    """The text under '## Residual'. The headline names the head, so a commit counts as disclosed only here."""
    part = re.split(r"(?m)^## Residual\s*$", body or "")
    return re.split(r"(?m)^## ", part[1])[0] if len(part) > 1 else ""


def approval_problems(body: str, pr: dict) -> list[str]:
    """Why this approval does not count: unsigned, by the PR's writer, or hiding commits only its signer saw."""
    name = signer(body)
    if not name:
        return ["the approval's last line is not 'Created: <agent name>'"]
    commits = authors(pr)
    writers = {signer(pr.get("body") or "").lower()} | {n.lower() for _, n in commits[:1]}
    if name.lower() in writers - {""}:
        return [f"{name!r} wrote this pull request: another agent judges it"]
    hidden = [sha[:7] for sha, who in commits if who.lower() == name.lower() and sha[:7] not in residual(body)]
    if hidden:
        return [f"{name!r} pushed {', '.join(hidden)} and nobody else checked them: name them under Residual"]
    return []


def check_decision(past: list[dict], body: str, number: int, pr: dict) -> list[str]:
    """Why this decision or verdict may not be posted. Empty: post it."""
    if pr["state"] != "OPEN":
        return [f"PR #{number} is {pr['state']}: no further decision on it"]
    item = parse(body, number)
    if not item:
        return [f"first line is neither a verdict nor a decision on PR #{number}: 'Verdict: PASS|FAIL at <40-character "
                f"sha>' or '<Accepted|Changes required|Stopped> by <role> (<name>). PR #{number} at <sha>.' (a change "
                f"request or a FAIL in a loop adds '. Round K of {MAX_ROUNDS}.')"]
    if stopped(past):
        return ["this PR is stopped: no further decision; restarting it is the human's call"]
    problems = []
    head = pr["headRefOid"]
    if item["sha"] != head:
        problems.append(f"it names {item['sha'][:8]} but the head is {head[:8]}: check the head")
    used = rounds_used(past)
    if item["verb"] in ("Changes required", "FAIL"):
        count = used.index(item["sha"]) + 1 if item["sha"] in used else len(used) + 1
        if count > MAX_ROUNDS:
            problems.append(f"{MAX_ROUNDS} rounds are used: pass it, or post 'Stopped by'")
        elif item["round"] != str(count):
            problems.append(f"this is round {count} of {MAX_ROUNDS}, not {item['round'] or 'unnumbered'}")
    if item["verb"] in APPROVALS:
        problems += approval_problems(body, pr)
    return problems


def merge_problems(past: list[dict], pr: dict) -> list[str]:
    """Why the review does not allow a merge. Empty: the newest judgment approves the current head."""
    if pr["state"] != "OPEN":
        return [f"the PR is {pr['state']}"]
    if stopped(past):
        return ["this PR is stopped"]
    problems = []
    if any(x["name"] == "risk:money-path" for x in pr.get("labels", [])):
        problems.append("the PR or a linked issue is labelled risk:money-path: never auto-merged, a person merges it")
    if not past:
        return problems + ["nobody has judged it"]
    last = past[-1]
    if last["sha"] != pr["headRefOid"]:
        return problems + [f"the newest judgment is on {last['sha'][:8]}, not on the head {pr['headRefOid'][:8]}"]
    if last["verb"] not in APPROVALS:
        return problems + [f"the newest judgment on the head is '{last['verb']}'"]
    return problems + approval_problems(last["body"], pr)


def describe(past: list[dict], head: str, pr_state: str = "OPEN") -> str:
    used = len(rounds_used(past))
    lines = [f"rounds used: {used} of {MAX_ROUNDS}"]
    at_head = past[-1] if past and past[-1]["sha"] == head else None
    if pr_state == "MERGED":
        lines.append("state: MERGED. Confirm the issue is closed; remove the worktrees that are left.")
    elif stopped(past):
        lines.append("state: STOPPED. Work on it ends and its worktree is removed; the PR and branch stay.")
    elif pr_state == "CLOSED":
        lines.append("state: CLOSED without a merge. Keep the branch and worktree; report it to the human.")
    elif at_head and at_head["verb"] in APPROVALS:
        word = "ACCEPTED" if at_head["verb"] == "Accepted" else "PASS"
        lines.append(f"state: {word} at the head. A playbook that merges runs can-merge next.")
    elif at_head:
        lines.append("state: changes required on the head. Whoever the playbook names fixes it.")
    elif used < MAX_ROUNDS:
        lines.append(f"state: head not judged. Pass it, or ask for changes as 'Round {used + 1} of {MAX_ROUNDS}'.")
    else:
        lines.append("state: head not judged. LAST CHECK: pass it, or post 'Stopped by'.")
    return "\n".join(lines)


def removal_problems(dirty: str, local_head: str, pr: dict | None, was_stopped: bool, remote_sha: str,
                     handover: bool = False) -> list[str]:
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
    if handover:
        if pr["state"] != "OPEN":
            problems.append(f"a handover is for an open PR; this one is {pr['state']}")
        if remote_sha != local_head:
            problems.append("origin's branch does not hold the local head: push before handing over")
        return problems
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
                          "state,headRefOid,headRefName,body,commits,labels,closingIssuesReferences,comments,reviews"))
    entries = [{**c, "at": c.get("createdAt")} for c in data["comments"]]
    entries += [{**r, "at": r.get("submittedAt")} for r in data["reviews"]]
    return data, decisions(entries, number)


def linked_labels(pr: dict, repo: str) -> list[dict]:
    """The labels of the issues the PR links: a money path is often marked only there."""
    numbers = [r["number"] for r in pr.get("closingIssuesReferences", [])]
    numbers += [int(x) for x in re.findall(r"(?m)^Refs #(\d+)\b", pr.get("body") or "")]
    found = []
    for number in dict.fromkeys(numbers):
        found += json.loads(run("gh", "issue", "view", str(number), "--repo", repo, "--json", "labels"))["labels"]
    return found


def worktree_facts(path: str, branch: str | None) -> tuple[str, str, str]:
    """(uncommitted files, local head, the head origin holds for the branch or '')."""
    dirty = run("git", "status", "--porcelain", "--untracked-files=all", cwd=path)
    head = run("git", "rev-parse", "HEAD", cwd=path).strip()
    branch = branch or run("git", "rev-parse", "--abbrev-ref", "HEAD", cwd=path).strip()
    remote = run("git", "ls-remote", "--heads", "origin", f"refs/heads/{branch}", cwd=path).split()
    return dirty, head, remote[0] if remote else ""


def self_test() -> int:
    a, b, c, d = ("a" * 40, "b" * 40, "c" * 40, "d" * 40)
    boss, rev = "Boss (CTO)", "Check (Reviewer)"

    def line(verb: str, sha: str, number: int | None = None) -> str:
        tail = f" Round {number} of {MAX_ROUNDS}." if number else ""
        if verb in ("PASS", "FAIL"):
            return f"Verdict: {verb} at {sha}" + (f".{tail}" if tail else "")
        who = "reviewer" if verb == "Stopped" else "CTO"
        return f"{verb} by {who} (X ({who})). PR #54 at {sha}.{tail}"

    def text(verb: str, sha: str, number: int | None = None, by: str = rev, more: str = "") -> str:
        return f"{line(verb, sha, number)}\n\ntext\n\n## Residual\n- {more or 'none'}\n\nCreated: {by}\n"

    def say(verb: str, sha: str, number: int | None = None, who: str = "OWNER", at: str = "", **extra) -> dict:
        return {"body": text(verb, sha, number, **extra), "authorAssociation": who, "at": at or sha}

    def pull(head: str, state: str = "OPEN", more: tuple = (), labels: tuple = ()) -> dict:
        commits = [(a, "Builder (Developer)"), *more]
        return {"state": state, "headRefOid": head, "body": "x\n\nCreated: Builder (Developer)\n",
                "commits": [{"oid": o, "authors": [{"name": n}]} for o, n in commits],
                "labels": [{"name": x} for x in labels]}

    assert MAX_ROUNDS == 3
    assert decisions([say("Changes required", a, 1, who="NONE")], 54) == [], "an outsider cannot spend a round"
    assert decisions([say("Changes required", a, 1)], 55) == [], "another PR's decision"
    for verb in ("Changes required", "FAIL"):
        assert check_decision([], text(verb, a, 1), 54, pull(a)) == [], verb
        assert "round 1 of 3" in check_decision([], text(verb, a, 2), 54, pull(a))[0]
        assert "unnumbered" in check_decision([], text(verb, a), 54, pull(a))[0]
    assert "head is" in check_decision([], text("PASS", a), 54, pull(b))[0], "stale SHA"
    assert rounds_used(decisions([say("FAIL", a)], 54)) == [], "a review-only FAIL spends no round"
    two = decisions([say("FAIL", b, 2), say("Changes required", a, 1)], 54)
    assert rounds_used(two) == [a, b], "one count for decisions and verdicts, ordered by time"
    again = decisions([say("FAIL", a, 1), say("FAIL", a, 1, at="z")], 54)
    assert rounds_used(again) == [a], "two requests on one head are one round"
    three = decisions([say("FAIL", a, 1), say("FAIL", b, 2), say("FAIL", c, 3)], 54)
    assert "3 rounds are used" in check_decision(three, text("FAIL", d, 3), 54, pull(d))[0], "no fourth round"
    assert check_decision(three, text("Stopped", d), 54, pull(d)) == []
    assert check_decision(three, text("PASS", d), 54, pull(d)) == []
    assert "LAST CHECK" in describe(three, d) and "changes required" in describe(three, c)
    done = three + decisions([say("Stopped", d)], 54)
    assert "this PR is stopped" in check_decision(done, text("PASS", d), 54, pull(d))[0]
    assert "STOPPED" in describe(done, d) and "STOPPED" in describe(done, d, "CLOSED")
    assert "neither a verdict" in check_decision([], "Looks good", 54, pull(a))[0]

    # approvals: never by the writer, never hiding the signer's own commits
    for verb in ("PASS", "Accepted"):
        assert "wrote this pull request" in check_decision([], text(verb, a, by="Builder (Developer)"), 54, pull(a))[0]
    fixed = pull(b, more=((b, rev),))
    assert "name them under Residual" in check_decision([], text("PASS", b), 54, fixed)[0]
    assert check_decision([], text("PASS", b, more=f"fixed by the reviewer: {b[:7]}"), 54, fixed) == []
    assert "Created" in approval_problems("Verdict: PASS at x", pull(a))[0]

    passed = decisions([say("PASS", a)], 54)
    assert merge_problems(passed, pull(a)) == []
    assert merge_problems(decisions([say("Accepted", a, by=boss)], 54), pull(a)) == []
    assert "nobody has judged" in merge_problems([], pull(a))[0]
    assert "not on the head" in merge_problems(passed, pull(b))[0], "a push after the PASS"
    later = decisions([say("PASS", a, at="1"), say("FAIL", a, at="2")], 54)
    assert "'FAIL'" in merge_problems(later, pull(a))[0], "a later FAIL wins"
    assert "money-path" in merge_problems(passed, pull(a, labels=("risk:money-path",)))[0]
    assert "stopped" in merge_problems(done, pull(d))[0]
    assert "PASS at the head" in describe(passed, a)
    assert "MERGED" in describe(passed, a, "MERGED") and "can-merge" not in describe(passed, a, "MERGED")
    assert "CLOSED" in describe(passed, a, "CLOSED")
    for state in ("MERGED", "CLOSED"):
        assert "no further decision" in check_decision([], text("FAIL", a, 1), 54, pull(a, state))[0], state
        assert state in merge_problems(passed, pull(a, state))[0]

    merged, opened = {"state": "MERGED", "headRefOid": a}, {"state": "OPEN", "headRefOid": a}
    assert removal_problems("", a, merged, False, "") == [], "merged, remote branch already deleted"
    assert removal_problems("", a, opened, True, a) == [], "stopped, branch on origin"
    assert "neither merged nor stopped" in removal_problems("", a, opened, False, a)[0]
    assert "uncommitted" in removal_problems("?? x\n", a, merged, False, "")[0]
    assert "not the PR's head" in removal_problems("", b, merged, False, "")[0], "a commit made after the merge"
    assert "keep the branch" in removal_problems("", a, opened, True, "")[0], "stopped but branch gone"
    assert "not fully pushed" in removal_problems("", a, None, False, b)[0]
    assert removal_problems("", a, opened, False, a, handover=True) == [], "pushed, another agent takes it"
    assert "push before handing over" in removal_problems("", a, opened, False, b, handover=True)[0]
    assert "not the PR's head" in removal_problems("", b, opened, False, a, handover=True)[0]
    assert "uncommitted" in removal_problems("?? x\n", a, opened, False, a, handover=True)[0]
    assert "open PR" in removal_problems("", a, merged, False, a, handover=True)[0]

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
    print("self-test passed: three rounds then pass or stop; only another agent approves; removal loses nothing")
    return 0


def _facts_for_no_pr(path: str):
    dirty, head, remote = worktree_facts(path, None)
    return dirty, head, None, False, remote


def main(argv: list[str]) -> int:
    if "--self-test" in argv[:1]:
        return self_test()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="mode", required=True)
    for mode in ("state", "decide", "can-merge", "can-remove"):
        p = sub.add_parser(mode)
        p.add_argument("--pr", type=int, required=mode != "can-remove")
        p.add_argument("--repo", required=mode != "can-remove")
        if mode == "decide":
            p.add_argument("--body-file", required=True)
        if mode == "can-remove":
            p.add_argument("--worktree", required=True)
            p.add_argument("--handover", action="store_true", help="the PR stays open; another agent takes the branch")
    args = parser.parse_args(argv)
    if args.mode == "can-remove":
        if args.pr is not None and not args.repo:
            parser.error("--pr needs --repo")
        if args.handover and args.pr is None:
            parser.error("--handover needs --pr")
        pr, past = read_pr(args.pr, args.repo) if args.pr is not None else (None, [])
        dirty, head, remote = worktree_facts(args.worktree, pr["headRefName"] if pr else None)
        problems = removal_problems(dirty, head, pr, stopped(past), remote, args.handover)
        ok = "safe to remove"
    else:
        pr, past = read_pr(args.pr, args.repo)
        if args.mode == "state":
            print(describe(past, pr["headRefOid"], pr["state"]))
            return 0
        if args.mode == "decide":
            body = Path(args.body_file).read_text(encoding="utf-8")
            problems = check_decision(past, body, args.pr, pr)
            ok = "decision allowed"
        else:
            pr = {**pr, "labels": pr.get("labels", []) + linked_labels(pr, args.repo)}
            problems = merge_problems(past, pr)
            ok = "the review allows the merge"
            if not problems:
                own = [sha[:7] for sha, who in authors(pr) if who.lower() == signer(past[-1]["body"]).lower()]
                if own:
                    ok += f"; pushed by the approver and checked by nobody else: {', '.join(own)}"
    for problem in problems:
        print("REFUSED", problem)
    if not problems:
        print(ok)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
