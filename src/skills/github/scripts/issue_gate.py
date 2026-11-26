#!/usr/bin/env python3
"""May this issue be implemented, and may this pull request be merged?

    issue_gate.py issue <number> --repo owner/repo     (before any work on the issue)
    issue_gate.py pr <number> --repo owner/repo        (right before a merge)
    issue_gate.py --self-test

A pull request may be merged only when (1) it links at least one issue of its repository and (2) every linked
issue passes. An issue passes when nothing refuses it and one approval holds.

  Refused, whatever else says yes: the issue is closed (done, not planned or duplicate), it carries a refusing
  label, or its board status is a refusing one. A board that cannot be read also refuses: it may say any of those.
  Approvals, any one: the repository owner commented the acceptance (assets/owner-acceptance.template.md); the
  owner created the issue; or its board status is an approving one.

Agents often share the owner's account, so text that carries an agent's 'Created: <name>' line is never the
owner's. The status and label names are in assets/merge-rules.json. For an organization's repository an owner is
a user with the admin role. Exit 0 = allowed, 1 = refused (reasons printed), 2 = usage. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

ASSETS = Path(__file__).resolve().parents[1] / "assets"
REFS_RE = re.compile(r"^Refs #(\d+)\b", re.M)
CREATED_RE = re.compile(r"^Created: (.+?)\s*$", re.M)
CLOSED_AS = {"COMPLETED": "done", "NOT_PLANNED": "not planned", "DUPLICATE": "duplicate"}
SCOPE_FIX = "gh auth refresh -h github.com -s read:project"
BOARD_QUERY = (
    "query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){issue(number:$n){projectItems(first:50){"
    'nodes{isArchived fieldValueByName(name:"Status"){... on ProjectV2ItemFieldSingleSelectValue{name}}}}}}}'
)


def rules() -> dict:
    return json.loads((ASSETS / "merge-rules.json").read_text(encoding="utf-8"))


def acceptance_phrase() -> str:
    """The first line of the template: what the owner's comment must start with."""
    return (ASSETS / "owner-acceptance.template.md").read_text(encoding="utf-8").strip().splitlines()[0]


def key(status: str) -> str:
    return re.sub(r"[^a-z]", "", status.lower())


def by_agent(text: str, login: str) -> bool:
    return any(name.lower() != login.lower() for name in CREATED_RE.findall(text or ""))


def refusals(issue: dict, board: list[str] | None, config: dict) -> list[str]:
    """Why this issue must not be implemented or merged. board is None when it could not be read."""
    if issue["state"] != "OPEN":
        reason = CLOSED_AS.get(issue.get("stateReason") or "", "closed")
        return [f"it is closed ({reason})"]
    found = []
    banned = {x.lower() for x in config["refuse_labels"]}
    found += [f"it has the label '{x['name']}'" for x in issue.get("labels", []) if x["name"].lower() in banned]
    if board is None:
        found.append(f"its board status cannot be read, so it may be done or not planned; the owner runs: {SCOPE_FIX}")
    else:
        refused = {key(x) for x in config["refuse_statuses"]}
        found += [f"its board status is '{x}'" for x in board if key(x) in refused]
    return found


def approvals(issue: dict, board: list[str] | None, config: dict, phrase: str,
              is_owner: Callable[[str], bool]) -> list[str]:
    found = []
    for comment in issue.get("comments", []):
        login = (comment.get("author") or {}).get("login", "")
        body = (comment.get("body") or "").lstrip()
        if (body.startswith(phrase) and not comment.get("isMinimized") and login and is_owner(login)
                and not by_agent(body, login)):
            found.append(f"the owner accepted it: {comment.get('url', '')}".rstrip(": "))
    author = (issue.get("author") or {}).get("login", "")
    if author and is_owner(author) and not by_agent(issue.get("body") or "", author):
        found.append("the owner created it")
    approved = {key(x) for x in config["approve_statuses"]}
    found += [f"its board status is '{x}'" for x in board or [] if key(x) in approved]
    return found


def judge(issue: dict, board: list[str] | None, config: dict, phrase: str,
          is_owner: Callable[[str], bool]) -> tuple[bool, str]:
    number = issue["number"]
    if "/pull/" in issue.get("url", ""):
        return False, f"#{number} is a pull request, not an issue"
    stop = refusals(issue, board, config)
    if stop:
        return False, f"#{number} is refused: " + "; ".join(stop)
    yes = approvals(issue, board, config, phrase, is_owner)
    if yes:
        return True, f"#{number}: " + "; ".join(yes)
    statuses = " or ".join(config["approve_statuses"])
    return False, (f"#{number} is not approved. The repository owner comments '{phrase}' on it "
                   f"(assets/owner-acceptance.template.md), or sets its board status to {statuses}. "
                   "An agent does neither of these for the owner")


def linked_issues(pr: dict, repo: str) -> tuple[list[int], list[str]]:
    """The issue numbers a pull request links in its own repository, and what is wrong with the links."""
    numbers, problems = [], []
    for ref in pr.get("closingIssuesReferences", []):
        home = f"{ref['repository']['owner']['login']}/{ref['repository']['name']}"
        if home.lower() == repo.lower():
            numbers.append(ref["number"])
        else:
            problems.append(f"{home}#{ref['number']} is in another repository: link an issue of {repo}")
    numbers += [int(x) for x in REFS_RE.findall(pr.get("body") or "")]
    numbers = list(dict.fromkeys(numbers))
    if not numbers and not problems:
        problems.append("it links no issue: add 'Closes #N' (or 'Refs #N' for partial work) to its body")
    return numbers, problems


def gh(*args: str) -> str:
    done = subprocess.run(["gh", *args], capture_output=True, text=True)
    if done.returncode:
        raise SystemExit(f"REFUSED gh failed, so nothing is approved: {done.stderr.strip()}")
    return done.stdout


def owner_check(repo: str) -> Callable[[str], bool]:
    info = json.loads(gh("api", f"repos/{repo}"))["owner"]
    seen: dict[str, bool] = {}

    def is_owner(login: str) -> bool:
        if info["type"] != "Organization":
            return login.lower() == info["login"].lower()
        if login not in seen:
            done = subprocess.run(["gh", "api", f"repos/{repo}/collaborators/{login}/permission"],
                                  capture_output=True, text=True)
            seen[login] = not done.returncode and json.loads(done.stdout).get("role_name") == "admin"
        return seen[login]

    return is_owner


def read_board(number: int, repo: str) -> list[str] | None:
    """The issue's Status on each project board; None when GitHub will not show it. gh's own issue view
    returns an empty list without the read:project scope, so it cannot be used here."""
    owner, name = repo.split("/", 1)
    done = subprocess.run(["gh", "api", "graphql", "-f", f"query={BOARD_QUERY}", "-f", f"o={owner}",
                           "-f", f"r={name}", "-F", f"n={number}"], capture_output=True, text=True)
    if done.returncode:
        return None
    data = json.loads(done.stdout)
    if data.get("errors"):
        return None
    nodes = data["data"]["repository"]["issue"]["projectItems"]["nodes"]
    return [n["fieldValueByName"]["name"] for n in nodes if not n["isArchived"] and n.get("fieldValueByName")]


def check_issue(number: int, repo: str, is_owner: Callable[[str], bool]) -> tuple[bool, str]:
    issue = json.loads(gh("issue", "view", str(number), "--repo", repo, "--json",
                          "number,url,state,stateReason,author,body,labels,comments"))
    needs_board = issue["state"] == "OPEN" and "/pull/" not in issue["url"]
    board = read_board(number, repo) if needs_board else []
    return judge(issue, board, rules(), acceptance_phrase(), is_owner)


def self_test() -> int:
    config, phrase = rules(), acceptance_phrase()
    assert phrase == "Accepted by owner."
    boss = lambda login: login == "boss"

    def issue(**change) -> dict:
        base = {"number": 7, "url": "https://h/o/r/issues/7", "state": "OPEN", "stateReason": "",
                "author": {"login": "someone"}, "body": "text", "labels": [], "comments": []}
        return {**base, **change}

    def comment(body: str, login: str = "boss", **extra) -> dict:
        return {"author": {"login": login}, "body": body, "url": "u", **extra}

    def ok(item: dict, board: list[str] | None = ()) -> bool:
        return judge(item, None if board is None else list(board), config, phrase, boss)[0]

    assert not ok(issue()), "nobody approved it"
    accepted = issue(comments=[comment("Accepted by owner.\n\nNotes: none")])
    assert ok(accepted)
    assert not ok(issue(comments=[comment("Accepted by owner.", login="someone")])), "not the owner"
    assert not ok(issue(comments=[comment("Accepted by owner.\n\nCreated: Bot (Developer)")])), "agent on the owner's account"
    assert not ok(issue(comments=[comment("Not yet.\nAccepted by owner.")])), "first line only"
    assert not ok(issue(comments=[comment("Accepted by owner.", isMinimized=True)])), "hidden comment"
    assert not ok(issue(comments=[comment("Accepted by CTO (Bot). Plan v1.")])), "a CTO decision is not the owner's"
    assert ok(issue(author={"login": "boss"})), "the owner created it"
    assert ok(issue(author={"login": "boss"}, body="x\n\nCreated: boss")), "signed with the owner's login"
    assert not ok(issue(author={"login": "boss"}, body="x\n\nCreated: Bot (CTO)")), "an agent created it"
    assert ok(issue(), ["Todo"]) and ok(issue(), ["In Progress"]) and ok(issue(), ["in-progress"])
    assert not ok(issue(), ["Backlog"])
    for status in ("Done", "Not planned", "Duplicate", "Canceled"):
        assert not ok(accepted, [status]), status
        assert not ok(issue(), ["Todo", status]), f"{status} wins over Todo"
    for reason, word in CLOSED_AS.items():
        allowed, why = judge({**accepted, "state": "CLOSED", "stateReason": reason}, [], config, phrase, boss)
        assert not allowed and word in why, why
    assert not ok({**accepted, "labels": [{"name": "wontfix"}]}) and not ok({**accepted, "labels": [{"name": "Duplicate"}]})
    assert not ok(accepted, None), "an unreadable board refuses"
    assert SCOPE_FIX in judge(accepted, None, config, phrase, boss)[1]
    assert not ok({**accepted, "url": "https://h/o/r/pull/7"}), "a pull request is not an issue"

    here = {"number": 4, "repository": {"name": "r", "owner": {"login": "o"}}}
    away = {"number": 1, "repository": {"name": "r", "owner": {"login": "stranger"}}}
    assert linked_issues({"closingIssuesReferences": [here], "body": "Closes #4"}, "o/r") == ([4], [])
    assert linked_issues({"closingIssuesReferences": [], "body": "Refs #9\n"}, "o/r") == ([9], [])
    assert "links no issue" in linked_issues({"closingIssuesReferences": [], "body": "see #4"}, "o/r")[1][0]
    assert "another repository" in linked_issues({"closingIssuesReferences": [away], "body": ""}, "o/r")[1][0]
    print("self-test passed: a linked issue, the three approvals, refusals win, agents cannot approve")
    return 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv[:1]:
        return self_test()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=("issue", "pr"))
    parser.add_argument("number", type=int)
    parser.add_argument("--repo", required=True)
    args = parser.parse_args(argv)
    results: list[tuple[bool, str]] = []
    if args.mode == "pr":
        pr = json.loads(gh("pr", "view", str(args.number), "--repo", args.repo, "--json",
                           "state,body,closingIssuesReferences"))
        if pr["state"] != "OPEN":
            results.append((False, f"PR #{args.number} is {pr['state']}"))
        numbers, problems = linked_issues(pr, args.repo)
        results += [(False, f"PR #{args.number}: {x}") for x in problems]
    else:
        numbers = [args.number]
    if numbers:
        is_owner = owner_check(args.repo)
        results += [check_issue(n, args.repo, is_owner) for n in numbers]
    for allowed, text in results:
        print("OK" if allowed else "REFUSED", text)
    passed = all(allowed for allowed, _ in results)
    what = "merge rules" if args.mode == "pr" else "implementation"
    print(f"{what}: {'allowed' if passed else 'NOT allowed'}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
