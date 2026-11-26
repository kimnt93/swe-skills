#!/usr/bin/env python3
"""The rules of a build playbook's review loop that must not depend on memory.

    pr_loop.py state --pr 54 --repo owner/repo
    pr_loop.py decide --pr 54 --repo owner/repo --body-file decision.md    (before posting a decision or verdict)
    pr_loop.py can-merge --pr 54 --repo owner/repo                        (before merging on someone's judgment)
    pr_loop.py can-merge --pr 54 --repo owner/repo --unreviewed --head <sha>   (playbook-quick only: no judgment)
    pr_loop.py can-remove --worktree <path> [--pr 54 --repo owner/repo] [--handover]
    pr_loop.py --self-test

A round is a 'Changes required ... Round K of 3.' decision (CTO/CEO) or a 'Verdict: FAIL at <sha>. Round K of 3.'
verdict (reviewer) on one head SHA. After the last round: pass it, or post 'Stopped by'. A refusal (FAIL, Changes
required, Stopped) counts from a comment or review by the repository's owners, members and collaborators. A grant
(Verdict: PASS) counts only when, in addition, its author can push: gh api repos/<repo>/collaborators/<login>/permission
answers admin, maintain or write (issue_gate.read_write_access). A failed lookup drops the grant, never a refusal.
'Accepted by CTO|CEO (...). PR #n at <sha>.' is an old quick form: it is still read for the state, it approves no
merge, and decide refuses to post a new one. (An 'Accepted by' on a plan is an issue comment, not read here.)

An approval (Verdict: PASS) must be signed by an agent that did not write the pull request, and
must name every commit its signer pushed to it, because nobody else checked those. `can-merge` allows a merge only
when the newest judgment is such an approval of the current head; it does not read checks or the issue
(`gh pr checks`, `issue_gate.py pr`). `can-merge --unreviewed --head <sha>` is for playbook-quick, which has no
judgment: it refuses a PR that is not open, any judgment or stop on the PR by anyone on any head (a judged PR is a
build or ship PR), a PR that links no issue, or another repository's issue, or an issue without the 'Pipeline: quick' header
line only playbook-quick writes,
a risk:money-path label on the PR or a linked issue, and a head other than <sha>. It cannot know which head was
reported: the CTO/CEO takes <sha> from the builder's report. A quick PR goes back to its builder at most 3 times:
before each return the CTO/CEO posts 'Returned by CTO (...). PR #n at <head>. Return K of 3.', so the count is on the
PR for a resumed run, and decide refuses a fourth (then 'Stopped by CTO'). 'Rebase after #m.' instead of the count is
free once per other merged quick PR #m that merged after this PR's latest report or return (the newest of its last
return, its creation and its head commit); an older merge or a time that cannot be read counts. A return judges nothing.
A linked issue counts only from this repository: a closing reference to another one is refused in both can-merge forms,
and the quick line counts only in a header GitHub shows as written (every line before the first '## ' heading
blank or a plain template header line: package_lint.header_problem). `can-remove` allows removal only when nothing would be lost: a clean tree,
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
from datetime import datetime
from pathlib import Path
from typing import Callable

# the round limit lives with the one linter; an installed copy may prefix every skill directory
_OWN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_OWN.parent / _OWN.name.replace("github", "work-package") / "scripts"))
from package_lint import MAX_RETURNS, MAX_ROUNDS, QUICK_MARK, header_problem, quick_marked  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
from issue_gate import issue_refs, parse_time  # noqa: E402

TRUSTED = ("OWNER", "MEMBER", "COLLABORATOR")
DECISION_RE = re.compile(
    r"^(?:(?P<verb>Accepted|Changes required) by (?:CTO|CEO) \(.+?\)\.|(?P<stop>Stopped) by (?:CTO|CEO|reviewer) \(.+?\)\."
    r"|(?P<ret>Returned) by (?:CTO|CEO) \(.+?\)\.)"
    r" PR #(?P<pr>\d+) at (?P<sha>[0-9a-f]{40})\."
    r"(?: Round (?P<round>\d+) of \d+\.| Return (?P<back>\d+) of \d+\.| Rebase after #(?P<after>\d+)\.)?\s*$"
)
VERDICT_RE = re.compile(r"^Verdict: (?P<verb>PASS|FAIL) at (?P<sha>[0-9a-f]{40})(?:\. Round (?P<round>\d+) of \d+\.)?\s*$")
CREATED_RE = re.compile(r"^Created: (.+?)\s*$")
APPROVALS = ("PASS",)  # the only verdict that grants a merge; an old 'Accepted by' on a PR grants nothing


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
        return {"verb": match["verb"] or match["stop"] or match["ret"], "sha": match["sha"], "round": match["round"],
                "back": match["back"], "after": match["after"], "body": body}
    match = VERDICT_RE.match(line)
    if match:
        return {"verb": match["verb"], "sha": match["sha"], "round": match["round"], "back": None, "after": None,
                "body": body}
    return None


def decisions(entries: list[dict], pr: int, can_grant: Callable[[str], bool] | None = None) -> list[dict]:
    """The judgments on this PR that count, oldest first. entries: {body, authorAssociation, author: {login}, at}.
    A refusal counts from an owner, member or collaborator. A grant (PASS) counts only when can_grant(login) also
    says its author can push; without can_grant no grant counts."""
    found = []
    for entry in sorted(entries, key=lambda e: e.get("at") or ""):
        item = parse(entry.get("body") or "", pr)
        if not item or entry.get("authorAssociation") not in TRUSTED:
            continue
        if item["verb"] in APPROVALS:
            login = (entry.get("author") or {}).get("login") or ""
            if not (can_grant and login and can_grant(login) is True):
                continue
        found.append({**item, "at": entry.get("at")})
    return found


def asks_change(item: dict) -> bool:
    """Whether it spends a round. A review-only FAIL has no round number and spends none."""
    return item["verb"] == "Changes required" or (item["verb"] == "FAIL" and bool(item["round"]))


def rounds_used(past: list[dict]) -> list[str]:
    """The head SHAs that got a change request, in order. Two requests on one SHA are one round."""
    return list(dict.fromkeys(d["sha"] for d in past if asks_change(d)))


def judgments(past: list[dict]) -> list[dict]:
    """The verdicts and decisions; a 'Returned by' (quick sends a PR back on a mechanical condition) judges nothing."""
    return [d for d in past if d["verb"] != "Returned"]


def returns_used(past: list[dict]) -> int:
    """The counted returns of a quick PR ('Return K of 3.'); a 'Rebase after #m.' does not count."""
    return sum(1 for d in past if d["verb"] == "Returned" and d["back"])


def last_report(past: list[dict], pr: dict) -> datetime | None:
    """The newest time on the host that this PR's latest report or return cannot precede: its newest 'Returned by',
    its creation and its head commit. None when any of them cannot be read."""
    head = [c for c in pr.get("commits", []) if c.get("oid") == pr.get("headRefOid")]
    times = [parse_time(pr.get("createdAt")), parse_time(head[-1].get("committedDate")) if head else None]
    times += [parse_time(d.get("at")) for d in past if d["verb"] == "Returned"]
    return None if None in times else max(times)


def return_problems(past: list[dict], item: dict, number: int, merged: Callable[[int], datetime | None] | None,
                    pr: dict | None = None) -> list[str]:
    """Why this 'Returned by' may not be posted. merged(m): when PR #m merged, if it is a merged quick PR whose
    linked issues are all of this repository; None otherwise. A rebase is free only after a merge later than this
    PR's latest report or return; a time that cannot be read counts it."""
    if bool(item["back"]) == bool(item["after"]):
        return [f"a return ends its first line with 'Return K of {MAX_RETURNS}.' or, for a clean rebase after another "
                "quick PR merged, 'Rebase after #<m>.'"]
    if item["back"]:
        used = returns_used(past)
        if used >= MAX_RETURNS:
            return [f"{MAX_RETURNS} returns are used: post 'Stopped by CTO' with the mechanical reason and report to "
                    "the owner"]
        if item["back"] != str(used + 1):
            return [f"this is return {used + 1} of {MAX_RETURNS}, not {item['back']}"]
        return []
    after = int(item["after"])
    if after == number:
        return ["a rebase is free only after another PR merged, not this one"]
    if any(d["verb"] == "Returned" and d["after"] == item["after"] for d in past):
        return [f"the free rebase after #{after} was used already: count this one as 'Return K of {MAX_RETURNS}.'"]
    when = merged(after) if merged else None
    if not isinstance(when, datetime):
        return [f"#{after} is not a merged quick PR (or that could not be read): count this one as "
                f"'Return K of {MAX_RETURNS}.'"]
    since = last_report(past, pr or {})
    if since is None:
        return [f"the time of this PR's latest report or return cannot be read: count this one as "
                f"'Return K of {MAX_RETURNS}.'"]
    if when <= since:
        return [f"#{after} merged at {when:%Y-%m-%dT%H:%M:%SZ}, not after this PR's latest report or return "
                f"({since:%Y-%m-%dT%H:%M:%SZ}): count this one as 'Return K of {MAX_RETURNS}.'"]
    return []


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


def check_decision(past: list[dict], body: str, number: int, pr: dict,
                   merged: Callable[[int], datetime | None] | None = None) -> list[str]:
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
    if item["verb"] == "Returned":
        head = pr["headRefOid"]
        found = [] if item["sha"] == head else [f"it names {item['sha'][:8]} but the head is {head[:8]}: check the head"]
        return found + return_problems(past, item, number, merged, pr)
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
    if item["verb"] == "Accepted":
        problems.append("'Accepted by' on a pull request no longer approves a merge: the reviewer posts the PASS "
                        "(playbook-build, playbook-ship); playbook-quick has no judgment")
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
    past = judgments(past)
    if not past:
        return problems + ["nobody has judged it"]
    last = past[-1]
    if last["sha"] != pr["headRefOid"]:
        return problems + [f"the newest judgment is on {last['sha'][:8]}, not on the head {pr['headRefOid'][:8]}"]
    if last["verb"] == "Accepted":
        return problems + ["the newest judgment on the head is an old 'Accepted by': it approves no merge; the "
                           "reviewer's PASS does"]
    if last["verb"] not in APPROVALS:
        return problems + [f"the newest judgment on the head is '{last['verb']}'"]
    return problems + approval_problems(last["body"], pr)


def unreviewed_problems(seen: list[dict], pr: dict, head: str, issues: list[dict],
                        refs: list[str] | tuple = ()) -> list[str]:
    """Why a pull request may not be merged without a judgment (playbook-quick only). Empty: the PR is open, nobody
    judged or stopped it on any head, it links issues of its repository only and every one carries the
    'Pipeline: quick' header line, it is no money path, and its head is the given one. seen: every judgment on the
    PR from anyone (not only the trusted). issues: the linked issues, {number, body, labels}; refs: what is wrong
    with the links (another repository's issue). The script cannot know which head the builder reported: the CTO/CEO
    passes the sha from the builder's report as head."""
    if not re.fullmatch(r"[0-9a-f]{40}", head or ""):
        return [f"--head is the reported head as a 40-character sha, not {head!r}"]
    if pr["state"] != "OPEN":
        return [f"the PR is {pr['state']}"]
    if stopped(seen):
        return ["this PR is stopped"]
    problems = list(refs)
    judged = [d for d in judgments(seen) if d["verb"] != "Stopped"]
    if judged:
        first = judged[0]
        problems.append(f"this PR carries a judgment ('{first['verb']}' at {first['sha'][:8]}): a judged PR is not a "
                        "quick PR; merge it with plain can-merge after a PASS, never --unreviewed")
    if not issues:
        problems.append("it links no issue: an unreviewed merge needs linked issues that carry 'Pipeline: quick'")
    for issue in issues:
        if not quick_marked(issue.get("body") or ""):
            unseen = header_problem(issue.get("body") or "")
            why = f"the header is not recognised: {unseen}" if unseen else "its header has no such line"
            problems.append(f"#{issue.get('number')} has no '{QUICK_MARK}' line in its header ({why}): only an issue "
                            "playbook-quick created is merged without a review")
    labels = pr.get("labels", []) + [x for issue in issues for x in issue.get("labels", [])]
    if any(x["name"] == "risk:money-path" for x in labels):
        problems.append("the PR or a linked issue is labelled risk:money-path: never auto-merged, a person merges it")
    if pr["headRefOid"] != head:
        problems.append(f"the head is {pr['headRefOid'][:8]}, not the reported head {head[:8]}: get a new report")
    return problems


def describe(past: list[dict], head: str, pr_state: str = "OPEN") -> str:
    used = len(rounds_used(past))
    lines = [f"rounds used: {used} of {MAX_ROUNDS}", f"returns used: {returns_used(past)} of {MAX_RETURNS} (quick)"]
    judged = judgments(past)
    at_head = judged[-1] if judged and judged[-1]["sha"] == head else None
    if pr_state == "MERGED":
        lines.append("state: MERGED. Confirm the issue is closed; remove the worktrees that are left.")
    elif stopped(past):
        lines.append("state: STOPPED. Work on it ends and its worktree is removed; the PR and branch stay.")
    elif pr_state == "CLOSED":
        lines.append("state: CLOSED without a merge. Keep the branch and worktree; report it to the human.")
    elif at_head and at_head["verb"] in APPROVALS:
        lines.append("state: PASS at the head. A playbook that merges runs can-merge next.")
    elif at_head and at_head["verb"] == "Accepted":
        lines.append("state: an old 'Accepted by' on the head; it approves no merge. A reviewer judges the head.")
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


def writer_check(repo: str) -> Callable[[str], bool]:
    """Whether a login can push to the repository, asked once per login; any failure is a no."""
    from issue_gate import read_write_access  # same folder; standard library only
    seen: dict[str, bool] = {}

    def can_grant(login: str) -> bool:
        if login not in seen:
            seen[login] = read_write_access(repo, login)[0] is True
        return seen[login]

    return can_grant


def entries_of(data: dict) -> list[dict]:
    return [{**c, "at": c.get("createdAt")} for c in data.get("comments", [])] + \
        [{**r, "at": r.get("submittedAt")} for r in data.get("reviews", [])]


def anyone(entries: list[dict], pr: int) -> list[dict]:
    """Every judgment on this PR, whoever posted it: for a refusal that must not depend on who is trusted."""
    found = [(parse(e.get("body") or "", pr), e) for e in sorted(entries, key=lambda e: e.get("at") or "")]
    return [{**x, "at": e.get("at")} for x, e in found if x]


def read_pr(number: int, repo: str) -> tuple[dict, list[dict]]:
    data = json.loads(run("gh", "pr", "view", str(number), "--repo", repo, "--json",
                          "state,createdAt,headRefOid,headRefName,body,commits,labels,closingIssuesReferences,"
                          "comments,reviews"))
    return data, decisions(entries_of(data), number, writer_check(repo))


def linked_issues(pr: dict, repo: str) -> tuple[list[dict], list[str]]:
    """The issues the PR links in its own repository ({number, labels, body}), and what is wrong with the links: a
    money path is often marked only on the issue, and a quick issue carries its 'Pipeline: quick' line there. A
    closing reference to another repository is refused, never read as the same number here (issue_gate.issue_refs)."""
    numbers, problems = issue_refs(pr, repo)
    found = []
    for number in numbers:
        issue = json.loads(run("gh", "issue", "view", str(number), "--repo", repo, "--json", "number,labels,body"))
        found.append({"number": issue.get("number", number), "labels": issue.get("labels", []),
                      "body": issue.get("body") or ""})
    return found, problems


def merged_quick(repo: str) -> Callable[[int], datetime | None]:
    """When PR #m merged, if it is merged and links only issues of this repository carrying the quick line: the
    only merge after which a quick PR may get a free rebase. Any failure or odd answer is None."""
    def merged(number: int) -> datetime | None:
        try:
            other = json.loads(run("gh", "pr", "view", str(number), "--repo", repo, "--json",
                                   "state,mergedAt,body,closingIssuesReferences"))
            issues, problems = linked_issues(other, repo)
        except (subprocess.CalledProcessError, ValueError, KeyError, TypeError, AttributeError):
            return None
        if other.get("state") != "MERGED" or problems or not issues or not all(quick_marked(x["body"]) for x in issues):
            return None
        return parse_time(other.get("mergedAt"))

    return merged


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

    def say(verb: str, sha: str, number: int | None = None, who: str = "OWNER", at: str = "", login: str = "rev",
            **extra) -> dict:
        return {"body": text(verb, sha, number, **extra), "authorAssociation": who, "author": {"login": login},
                "at": at or sha}

    writers = {"rev", "boss"}
    grant = lambda login: login in writers  # noqa: E731

    def judged(entries: list[dict], pr: int = 54) -> list[dict]:
        return decisions(entries, pr, grant)

    def pull(head: str, state: str = "OPEN", more: tuple = (), labels: tuple = ()) -> dict:
        commits = [(a, "Builder (Developer)"), *more]
        commits += [] if head in dict(commits) else [(head, "Builder (Developer)")]
        return {"state": state, "headRefOid": head, "body": "x\n\nCreated: Builder (Developer)\n",
                "createdAt": "2026-01-01T00:00:00Z",
                "commits": [{"oid": o, "authors": [{"name": n}], "committedDate": "2026-01-01T00:00:00Z"}
                            for o, n in commits],
                "labels": [{"name": x} for x in labels]}

    assert MAX_ROUNDS == 3
    assert judged([say("Changes required", a, 1, who="NONE")], 54) == [], "an outsider cannot spend a round"
    assert judged([say("Changes required", a, 1)], 55) == [], "another PR's decision"
    for verb in ("Changes required", "FAIL"):
        assert check_decision([], text(verb, a, 1), 54, pull(a)) == [], verb
        assert "round 1 of 3" in check_decision([], text(verb, a, 2), 54, pull(a))[0]
        assert "unnumbered" in check_decision([], text(verb, a), 54, pull(a))[0]
    assert "head is" in check_decision([], text("PASS", a), 54, pull(b))[0], "stale SHA"
    assert rounds_used(judged([say("FAIL", a)], 54)) == [], "a review-only FAIL spends no round"
    two = judged([say("FAIL", b, 2), say("Changes required", a, 1)], 54)
    assert rounds_used(two) == [a, b], "one count for decisions and verdicts, ordered by time"
    again = judged([say("FAIL", a, 1), say("FAIL", a, 1, at="z")], 54)
    assert rounds_used(again) == [a], "two requests on one head are one round"
    three = judged([say("FAIL", a, 1), say("FAIL", b, 2), say("FAIL", c, 3)], 54)
    assert "3 rounds are used" in check_decision(three, text("FAIL", d, 3), 54, pull(d))[0], "no fourth round"
    assert check_decision(three, text("Stopped", d), 54, pull(d)) == []
    assert check_decision(three, text("PASS", d), 54, pull(d)) == []
    assert "LAST CHECK" in describe(three, d) and "changes required" in describe(three, c)
    done = three + judged([say("Stopped", d)], 54)
    assert "this PR is stopped" in check_decision(done, text("PASS", d), 54, pull(d))[0]
    assert "STOPPED" in describe(done, d) and "STOPPED" in describe(done, d, "CLOSED")
    assert "neither a verdict" in check_decision([], "Looks good", 54, pull(a))[0]

    # approvals: never by the writer, never hiding the signer's own commits
    assert "wrote this pull request" in check_decision([], text("PASS", a, by="Builder (Developer)"), 54, pull(a))[0]
    fixed = pull(b, more=((b, rev),))
    assert "name them under Residual" in check_decision([], text("PASS", b), 54, fixed)[0]
    assert check_decision([], text("PASS", b, more=f"fixed by the reviewer: {b[:7]}"), 54, fixed) == []
    assert "Created" in approval_problems("Verdict: PASS at x", pull(a))[0]
    own = {"state": "OPEN", "headRefOid": a, "body": "x\n\nCreated: Boss (CTO) / developer\n",
           "commits": [{"oid": a, "authors": [{"name": "Boss (CTO) / developer"}]}]}
    assert approval_problems(text("PASS", a, by=boss), own) == [], "an agent judges the PR of another's agent"

    passed = judged([say("PASS", a)], 54)
    assert merge_problems(passed, pull(a)) == []
    # an old 'Accepted by CTO' on a PR is read for the state, approves no merge, and cannot be posted any more
    old = judged([say("Accepted", a, by=boss, login="boss")], 54)
    assert old and "approves no merge" in merge_problems(old, pull(a))[0]
    assert "no longer approves" in " ".join(check_decision([], text("Accepted", a, by=boss), 54, pull(a)))
    assert "old 'Accepted by'" in describe(old, a)
    assert "'FAIL'" in merge_problems(judged([say("PASS", a, at="1"), say("Accepted", a, at="2", by=boss)], 54) +
                                      judged([say("FAIL", a, at="3")], 54), pull(a))[0]

    # a grant counts only from an account that can push; a refusal counts whatever the lookup says
    for login in ("reader", "triager", ""):
        for who in ("MEMBER", "COLLABORATOR", "OWNER"):
            assert judged([say("PASS", a, who=who, login=login)], 54) == [], (login, who)
            assert "nobody has judged" in merge_problems(judged([say("PASS", a, who=who, login=login)], 54), pull(a))[0]
    assert decisions([say("PASS", a)], 54) == [], "no permission check: no grant"
    assert decisions([say("PASS", a)], 54, lambda login: "yes") == [], "an odd answer is a no"
    assert judged([say("PASS", a, who="NONE")], 54) == [], "a writer's grant still needs the association"
    failed = judged([say("FAIL", a, 1, at="1", login="reader")], 54) + judged([say("PASS", a, at="2", login="reader")], 54)
    assert "'FAIL'" in merge_problems(failed, pull(a))[0], "a dropped PASS never hides a FAIL"
    assert judged([say("FAIL", a, 1, login="reader")], 54), "a refusal counts without the permission lookup"
    assert judged([say("Stopped", a, login="")], 54), "a stop counts without the permission lookup"
    assert "nobody has judged" in merge_problems([], pull(a))[0]
    assert "not on the head" in merge_problems(passed, pull(b))[0], "a push after the PASS"
    later = judged([say("PASS", a, at="1"), say("FAIL", a, at="2")], 54)
    assert "'FAIL'" in merge_problems(later, pull(a))[0], "a later FAIL wins"
    assert "money-path" in merge_problems(passed, pull(a, labels=("risk:money-path",)))[0]
    assert "stopped" in merge_problems(done, pull(d))[0]
    assert "PASS at the head" in describe(passed, a)
    assert "MERGED" in describe(passed, a, "MERGED") and "can-merge" not in describe(passed, a, "MERGED")
    assert "CLOSED" in describe(passed, a, "CLOSED")
    for state in ("MERGED", "CLOSED"):
        assert "no further decision" in check_decision([], text("FAIL", a, 1), 54, pull(a, state))[0], state
        assert state in merge_problems(passed, pull(a, state))[0]

    # can-merge --unreviewed (quick): only an open PR nobody judged or stopped, whose linked issues all carry the
    # quick line, that is no money path, at the head the builder reported
    quick = [{"number": 7, "labels": [], "body": "Lane: backend\nPipeline: quick\n\n## Goal\nx\n\nCreated: Boss (CTO)"}]
    seen = lambda *entries: anyone(list(entries), 54)  # noqa: E731
    assert unreviewed_problems([], pull(a), a, quick) == [], "nobody judged it: quick merges it"
    assert "not the reported head" in unreviewed_problems([], pull(b), a, quick)[0], "a push after the report"
    assert "40-character" in unreviewed_problems([], pull(a), "abc", quick)[0]
    for state in ("MERGED", "CLOSED"):
        assert state in unreviewed_problems([], pull(a, state), a, quick)[0], state
    assert "stopped" in unreviewed_problems(seen(say("Stopped", d)), pull(d), d, quick)[0]
    assert "money-path" in " ".join(unreviewed_problems([], pull(a, labels=("risk:money-path",)), a, quick))
    marked_money = [{**quick[0], "labels": [{"name": "risk:money-path"}]}]
    assert "money-path" in " ".join(unreviewed_problems([], pull(a), a, marked_money)), "a money path on the issue"
    # s1: a build PR the reviewer failed, then a push nobody judged; s2: a build PR never reviewed (no quick line)
    s1 = seen(say("FAIL", a, 1))
    assert "carries a judgment" in " ".join(unreviewed_problems(s1, pull(b), b, quick)), "s1"
    build_issue = [{"number": 7, "labels": [], "body": "Lane: backend\nRefs #60\n\nCreated: Boss (CTO)"}]
    assert "no 'Pipeline: quick' line" in " ".join(unreviewed_problems([], pull(b), b, build_issue)), "s2"
    assert "links no issue" in " ".join(unreviewed_problems([], pull(a), a, [])), "no linked issue"
    assert "no 'Pipeline: quick'" in " ".join(unreviewed_problems([], pull(a), a, quick + build_issue)), "every issue"
    for mark in ("Pipeline: build", "pipeline: quick", "Notes: Pipeline: quick", "Pipeline: quickly", "> Pipeline: quick",
                 "  Pipeline: quick", "## Goal\nPipeline: quick", "```text\nPipeline: quick\n```", "~~~\nPipeline: quick"):
        other = [{"number": 7, "labels": [], "body": f"Lane: x\n{mark}\n\n## Goal\nx\n"}]
        assert "line in its header" in " ".join(unreviewed_problems([], pull(a), a, other)), mark
    fenced = [{"number": 7, "labels": [], "body": "Lane: x\n\n## Goal\nx\n\n## Notes\n```text\nPriority: medium\n"
               "Pipeline: quick\n```\n"}]
    assert "line in its header" in " ".join(unreviewed_problems([], pull(a), a, fenced)), "N1: a fenced example"
    assert "line in its header" in " ".join(unreviewed_problems([], pull(a), a, [{**quick[0], "body": "Pipeline: quick\n"}]))
    for body in ("Priority: medium\n<!--\nPipeline: quick\n-->\n## Goal\nx",
                 "Priority: medium\n<details>\n\nPipeline: quick\n\n</details>\n## Goal\nx",
                 "Priority: medium\n<!--\nPipeline: quick\n## Goal\nx", "Lane: x\n<!--\nPipeline: quick\n\n## Goal\n-->\n",
                 "<p hidden>\nPipeline: quick\n</p>\n\n## Goal\nx", "Notes: x\nPipeline: quick\n\n## Goal\nx"):
        hidden = unreviewed_problems([], pull(a), a, [{"number": 7, "labels": [], "body": body}])
        assert "line in its header" in " ".join(hidden) and "not recognised" in " ".join(hidden), ("N4", body)
    away = "stranger/other#7 is in another repository: link an issue of o/r"
    assert away in unreviewed_problems([], pull(a), a, quick, [away]), "N3: another repository's issue"
    for verb, number in (("FAIL", 1), ("Changes required", 1), ("FAIL", None), ("PASS", None), ("Accepted", None)):
        assert "carries a judgment" in " ".join(unreviewed_problems(seen(say(verb, b, number)), pull(a), a, quick)), verb
    outsider = seen(say("FAIL", a, who="NONE", login="stranger"))
    assert "carries a judgment" in " ".join(unreviewed_problems(outsider, pull(a), a, quick)), "anyone's judgment"

    # quick returns: at most 3 counted, numbered in order, read from the PR; a rebase after another merged quick PR
    # is free once per such PR; a return judges nothing
    def back(k: int | None = None, sha: str = a, after: int | None = None) -> str:
        tail = f" Return {k} of {MAX_RETURNS}." if k else f" Rebase after #{after}." if after else ""
        return f"Returned by CTO (Boss (CTO)). PR #54 at {sha}.{tail}\n\n## Blocking\n- x\n\nCreated: {boss}\n"

    def said(*bodies: str) -> list[dict]:
        return judged([{"body": x, "authorAssociation": "OWNER", "author": {"login": "boss"},
                        "at": f"2026-01-0{k + 2}T00:00:00Z"} for k, x in enumerate(bodies)])

    others = {53: parse_time("2026-02-01T00:00:00Z"), 52: parse_time("2026-02-01T00:00:00Z")}.get
    assert MAX_RETURNS == 3
    assert check_decision([], back(1), 54, pull(a)) == []
    assert "return 1 of 3, not 2" in check_decision([], back(2), 54, pull(a))[0]
    two = said(back(1, a), back(2, b))
    assert check_decision(two, back(3, c), 54, pull(c)) == []
    full = said(back(1, a), back(2, b), back(3, c))
    assert returns_used(full) == 3 and "returns used: 3 of 3" in describe(full, d)
    assert "3 returns are used" in check_decision(full, back(4, d), 54, pull(d))[0], "no fourth return"
    assert "3 returns are used" in check_decision(full, back(3, d), 54, pull(d))[0]
    assert check_decision(full, text("Stopped", d), 54, pull(d)) == [], "then the stop"
    assert "head is" in check_decision([], back(1, b), 54, pull(a))[0], "a return names the head"
    assert "'Return K of 3.'" in check_decision([], back(), 54, pull(a))[0], "a return carries its count"
    assert check_decision(full, back(sha=d, after=53), 54, pull(d), others) == [], "a free rebase after #53"
    assert "used already" in check_decision(said(back(sha=c, after=53)), back(sha=d, after=53), 54, pull(d), others)[0]
    assert "not a merged quick PR" in check_decision([], back(after=60), 54, pull(a), others)[0]
    assert "not a merged quick PR" in check_decision([], back(after=53), 54, pull(a))[0], "no lookup: counted"
    assert "not a merged quick PR" in check_decision([], back(after=53), 54, pull(a), {53: True}.get)[0], "no time"
    # N2: free only when #m merged after this PR's latest report or return; a time that cannot be read counts it
    early = {53: parse_time("2026-01-03T00:00:00Z")}.get
    assert "not after this PR's latest" in check_decision(said(back(1), back(2)), back(sha=a, after=53), 54, pull(a),
                                                          early)[0], "merged before the latest return"
    assert check_decision(said(back(1)), back(sha=a, after=53), 54, pull(a), early) == [], "merged after it"
    assert "not after" in check_decision([], back(after=53), 54, {**pull(a), "createdAt": "2026-01-04T00:00:00Z"},
                                         early)[0], "merged before the PR was opened"
    pushed = {**pull(a), "commits": [{"oid": a, "authors": [{"name": "x"}], "committedDate": "2026-01-05T00:00:00Z"}]}
    assert "not after" in check_decision([], back(after=53), 54, pushed, early)[0], "merged before the head was made"
    assert "not after" in check_decision([], back(after=53), 54, pull(a), {53: parse_time("2026-01-01T00:00:00Z")}.get)[0]
    for broken in ({**pull(a), "createdAt": None}, {**pull(a), "createdAt": "soon"}, {**pull(a), "commits": []},
                   {**pull(a), "commits": [{"oid": a, "authors": [{"name": "x"}]}]}):
        assert "cannot be read" in check_decision([], back(after=53), 54, broken, others)[0], broken
    undated = judged([{"body": back(1), "authorAssociation": "OWNER", "author": {"login": "boss"}, "at": None}])
    assert "cannot be read" in check_decision(undated, back(sha=a, after=53), 54, pull(a), others)[0], "a return's time"
    old = said(*[back(k) for k in (1, 2, 3)], *[back(sha=a, after=m) for m in (10, 11, 12)])
    assert "not after" in check_decision(old, back(sha=a, after=13), 54, pull(a), {13: parse_time("2026-01-05T00:00:00Z")}.get)[0], \
        "the reviewer's seventh return through old merged quick PRs"
    assert "not this one" in check_decision([], back(after=54), 54, pull(a), others)[0]
    assert returns_used(said(back(1), back(sha=b, after=53))) == 1, "a rebase does not count"
    assert len(said(back(1))) == 1 and judgments(said(back(1))) == [], "a return is read, and judges nothing"
    assert "nobody has judged" in merge_problems(said(back(1)), pull(a))[0]
    assert unreviewed_problems(anyone([{"body": back(1), "at": "0"}], 54), pull(a), a, quick) == []
    assert "stopped" in unreviewed_problems(anyone([{"body": back(1), "at": "0"}, {"body": text("Stopped", a), "at": "1"}],
                                                   54), pull(a), a, quick)[0]

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
    print("self-test passed: three rounds then pass or stop; only another agent that can push grants a PASS, an old "
          "'Accepted by' approves nothing, a failed lookup never hides a refusal; at most 3 counted returns of a quick "
          "PR, a rebase free only after a later merge; an unreviewed merge only of an unjudged PR whose issues, all of "
          "this repository, say 'Pipeline: quick' in their header, at the given head, never a money path; removal "
          "loses nothing")
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
        if mode == "can-merge":
            p.add_argument("--unreviewed", action="store_true", help="playbook-quick: merge with no judgment")
            p.add_argument("--head", help="with --unreviewed: the head sha the builder reported")
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
        if args.mode == "can-merge" and bool(args.unreviewed) != bool(args.head):
            parser.error("--unreviewed and --head go together")
        pr, past = read_pr(args.pr, args.repo)
        if args.mode == "state":
            print(describe(past, pr["headRefOid"], pr["state"]))
            return 0
        if args.mode == "decide":
            body = Path(args.body_file).read_text(encoding="utf-8")
            problems = check_decision(past, body, args.pr, pr, merged_quick(args.repo))
            ok = "decision allowed"
        elif args.unreviewed:
            issues, refs = linked_issues(pr, args.repo)
            problems = unreviewed_problems(anyone(entries_of(pr), args.pr), pr, args.head, issues, refs)
            ok = "the unreviewed merge is allowed (playbook-quick): nobody judged this head"
        else:
            issues, refs = linked_issues(pr, args.repo)
            labels = [x for issue in issues for x in issue["labels"]]
            pr = {**pr, "labels": pr.get("labels", []) + labels}
            problems = refs + merge_problems(past, pr)
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
