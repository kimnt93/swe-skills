#!/usr/bin/env python3
"""May this issue be implemented, and may this pull request be merged?

    issue_gate.py issue <number> --repo owner/repo     (before any work on the issue)
    issue_gate.py pr <number> --repo owner/repo        (right before a merge)
    issue_gate.py --self-test

A pull request may be merged only when (1) it links at least one issue of its repository and (2) every linked
issue passes. An issue passes when nothing refuses it and one approval holds.

  Refused, whatever else says yes: the issue is closed (done, not planned or duplicate), it carries a refusing
  label, or its board status is a refusing one.
  Approvals: the 'approvals' list in assets/merge-rules.json says which count, any one of them:
    owner_comment  the repository owner commented the acceptance (assets/owner-acceptance.template.md)
    owner_author   the owner created the issue
    board_status   its board status is an approving one
  Shipped: owner_comment only. Agents share the owner's account, so an issue the owner's account created and a board
  status an agent may have set are off. A missing, empty or unknown value refuses everything.
  The board: when GitHub answers that the gh login lacks the scope to read it (INSUFFICIENT_SCOPES), the check
  goes on without it and says so. No board status refuses or approves then, so a Done or Not planned on an issue
  that is still open is not seen. Any other failure to read the board refuses.

Agents often share the owner's account, so text that carries an agent's 'Created: <name>' line is never the
owner's. The status and label names are in assets/merge-rules.json too. For an organization's repository an owner is
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
from unittest import mock

ASSETS = Path(__file__).resolve().parents[1] / "assets"
REFS_RE = re.compile(r"^Refs #(\d+)\b", re.M)
CREATED_RE = re.compile(r"^Created: (.+?)\s*$", re.M)
APPROVALS = ("owner_comment", "owner_author", "board_status")
CLOSED_AS = {"COMPLETED": "done", "NOT_PLANNED": "not planned", "DUPLICATE": "duplicate"}
NO_SCOPE = "no scope"  # the board answer when GitHub says the login lacks the scope to read it
NOT_READ = "the board was not read: the gh login lacks the scope, so no board status was checked"
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


def approval_setting(config: dict) -> tuple[list[str], str]:
    """The approvals merge-rules.json switches on, and what is wrong with the setting ('' when nothing)."""
    value = config.get("approvals")
    if "approvals" not in config:
        problem = "has no 'approvals'"
    elif not isinstance(value, list):
        problem = f"'approvals' is not a list: {json.dumps(value)}"
    elif not value:
        problem = "'approvals' is empty"
    else:
        unknown = [x for x in value if x not in APPROVALS]
        if not unknown:
            return value, ""
        problem = "'approvals' has the unknown value " + ", ".join(json.dumps(x) for x in unknown)
    return [], (f"merge-rules.json {problem}, so nothing approves it. List one or more of "
                f"{', '.join(APPROVALS)}; the shipped setting is [\"owner_comment\"]")


def refusals(issue: dict, board: list[str] | None, config: dict) -> list[str]:
    """Why this issue must not be implemented or merged. board is None when reading it failed."""
    if issue["state"] != "OPEN":
        reason = CLOSED_AS.get(issue.get("stateReason") or "", "closed")
        return [f"it is closed ({reason})"]
    found = []
    banned = {x.lower() for x in config["refuse_labels"]}
    found += [f"it has the label '{x['name']}'" for x in issue.get("labels", []) if x["name"].lower() in banned]
    if board is None:
        found.append("its board status cannot be read, so it may be done or not planned; run the check again")
    else:
        refused = {key(x) for x in config["refuse_statuses"]}
        found += [f"its board status is '{x}'" for x in board if key(x) in refused]
    return found


def approvals(issue: dict, board: list[str] | None, config: dict, phrase: str,
              is_owner: Callable[[str], bool]) -> list[str]:
    on = approval_setting(config)[0]
    found = []
    for comment in issue.get("comments", []) if "owner_comment" in on else []:
        login = (comment.get("author") or {}).get("login", "")
        body = (comment.get("body") or "").lstrip()
        if (body.startswith(phrase) and not comment.get("isMinimized") and login and is_owner(login)
                and not by_agent(body, login)):
            found.append(f"the owner accepted it: {comment.get('url', '')}".rstrip(": "))
    author = (issue.get("author") or {}).get("login", "")
    if "owner_author" in on and author and is_owner(author) and not by_agent(issue.get("body") or "", author):
        found.append("the owner created it")
    approved = {key(x) for x in config["approve_statuses"]} if "board_status" in on else set()
    found += [f"its board status is '{x}'" for x in board or [] if key(x) in approved]
    return found


def not_approved(number: int, config: dict, phrase: str, unread: bool) -> str:
    """What the owner can do, and which approvals merge-rules.json has switched off."""
    on = approval_setting(config)[0]
    statuses = " or ".join(config["approve_statuses"])
    ways = {"owner_comment": f"the repository owner comments '{phrase}' on it (assets/owner-acceptance.template.md)",
            "owner_author": "the repository owner creates it",
            "board_status": "" if unread else f"the owner sets its board status to {statuses}"}
    offered = [ways[x] for x in APPROVALS if x in on and ways[x]]
    off = {"owner_comment": f"the owner's comment '{phrase}'", "owner_author": "an issue the owner created",
           "board_status": f"a board status of {statuses}"}
    text = f"#{number} is not approved. "
    if set(on) == {"owner_comment"}:
        text += f"Only the repository owner's comment '{phrase}' approves it (assets/owner-acceptance.template.md). "
    elif offered:
        text += "It needs one of: " + "; or ".join(offered) + ". "
    skipped = [off[x] for x in APPROVALS if x not in on]
    if skipped:
        joined = " and ".join(skipped)
        why = "switched off" if "owner_comment" not in on else "off while agents share the owner's account"
        text += f"{joined[0].upper()}{joined[1:]} approve{'' if len(skipped) > 1 else 's'} nothing: {why} "
        text += "(the 'approvals' list in assets/merge-rules.json). "
    return text + "An agent never approves for the owner"


def judge(issue: dict, board: list[str] | str | None, config: dict, phrase: str,
          is_owner: Callable[[str], bool]) -> tuple[bool, str]:
    number = issue["number"]
    if "/pull/" in issue.get("url", ""):
        return False, f"#{number} is a pull request, not an issue"
    unread = board == NO_SCOPE
    statuses = [] if unread else board
    note = f" ({NOT_READ})" if unread else ""
    setting = approval_setting(config)[1]
    stop = refusals(issue, statuses, config) + ([setting] if setting else [])
    if stop:
        return False, f"#{number} is refused: " + "; ".join(stop) + note
    yes = approvals(issue, statuses, config, phrase, is_owner)
    if yes:
        return True, f"#{number}: " + "; ".join(yes) + note
    return False, not_approved(number, config, phrase, unread) + note


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


def parse_board(returncode: int, output: str) -> list[str] | str | None:
    """GitHub's answer to BOARD_QUERY: the statuses; NO_SCOPE when every error is a missing scope; None for any
    other failure. gh exits non-zero on a GraphQL error and still prints the answer."""
    try:
        data = json.loads(output)
        errors = data.get("errors")
        if errors:
            return NO_SCOPE if all(x.get("type") == "INSUFFICIENT_SCOPES" for x in errors) else None
        if returncode:
            return None
        nodes = data["data"]["repository"]["issue"]["projectItems"]["nodes"]
        return [n["fieldValueByName"]["name"] for n in nodes if not n["isArchived"] and n.get("fieldValueByName")]
    except (ValueError, KeyError, TypeError, AttributeError):
        return None


def read_board(number: int, repo: str) -> list[str] | str | None:
    """The issue's Status on each project board (see parse_board). gh's own issue view returns an empty list
    without the scope, which looks like an issue on no board, so it cannot be used here."""
    owner, name = repo.split("/", 1)
    done = subprocess.run(["gh", "api", "graphql", "-f", f"query={BOARD_QUERY}", "-f", f"o={owner}",
                           "-f", f"r={name}", "-F", f"n={number}"], capture_output=True, text=True)
    return parse_board(done.returncode, done.stdout)


def check_issue(number: int, repo: str, is_owner: Callable[[str], bool], config: dict) -> tuple[bool, str]:
    issue = json.loads(gh("issue", "view", str(number), "--repo", repo, "--json",
                          "number,url,state,stateReason,author,body,labels,comments"))
    needs_board = issue["state"] == "OPEN" and "/pull/" not in issue["url"]
    board = read_board(number, repo) if needs_board else []
    return judge(issue, board, config, acceptance_phrase(), is_owner)


def self_test() -> int:
    shipped, phrase = rules(), acceptance_phrase()
    assert phrase == "Accepted by owner."
    assert shipped["approvals"] == ["owner_comment"], "shipped: only the owner's comment approves"
    every = {**shipped, "approvals": list(APPROVALS)}
    author_on = {**shipped, "approvals": ["owner_comment", "owner_author"]}
    board_on = {**shipped, "approvals": ["owner_comment", "board_status"]}
    boss = lambda login: login == "boss"

    def issue(**change) -> dict:
        base = {"number": 7, "url": "https://h/o/r/issues/7", "state": "OPEN", "stateReason": "",
                "author": {"login": "someone"}, "body": "text", "labels": [], "comments": []}
        return {**base, **change}

    def comment(body: str, login: str = "boss", **extra) -> dict:
        return {"author": {"login": login}, "body": body, "url": "u", **extra}

    def verdict(item: dict, board: list[str] | None = (), config: dict = shipped) -> tuple[bool, str]:
        return judge(item, None if board is None else list(board), config, phrase, boss)

    def ok(item: dict, board: list[str] | None = (), config: dict = shipped) -> bool:
        return verdict(item, board, config)[0]

    accepted = issue(comments=[comment("Accepted by owner.\n\nNotes: none")])
    owned = issue(author={"login": "boss"})
    signed = issue(author={"login": "boss"}, body="x\n\nCreated: boss")
    agent_made = issue(author={"login": "boss"}, body="x\n\nCreated: Bot (CTO)")

    # 1. the shipped rules: only the owner's acceptance comment approves, and its protections hold
    assert not ok(issue()), "nobody approved it"
    assert ok(accepted) and ok(accepted, ["Todo"])
    assert not ok(issue(comments=[comment("Accepted by owner.", login="someone")])), "not the owner"
    assert not ok(issue(comments=[comment("Accepted by owner.\n\nCreated: Bot (Developer)")])), "agent on the owner's account"
    assert not ok(issue(comments=[comment("Not yet.\nAccepted by owner.")])), "first line only"
    assert not ok(issue(comments=[comment("Accepted by owner.", isMinimized=True)])), "hidden comment"
    assert not ok(issue(comments=[comment("Accepted by CTO (Bot). Plan v1.")])), "a CTO decision is not the owner's"
    for item, board in ((owned, []), (signed, []), (issue(), ["Todo"]), (issue(), ["In Progress"]),
                        (issue(), ["in-progress"]), (owned, ["Todo"])):
        allowed, why = verdict(item, board)
        assert not allowed, ("off in the shipped rules", item["author"], board)
        assert "Only the repository owner's comment" in why and "off while agents share the owner's account" in why, why
        assert "board status to" not in why and "creates it" not in why, why

    # 2. the other two approvals, switched on, work as before; the comment counts only when listed
    assert ok(owned, config=author_on) and ok(signed, config=author_on), "the owner created it"
    assert not ok(agent_made, config=author_on), "an agent created it"
    assert not ok(issue(), ["Todo"], author_on), "board status still off"
    assert ok(issue(), ["Todo"], board_on) and ok(issue(), ["In Progress"], board_on)
    assert ok(issue(), ["in-progress"], board_on) and not ok(issue(), ["Backlog"], board_on)
    assert not ok(owned, config=board_on), "authorship still off"
    assert ok(owned, config=every) and ok(issue(), ["Todo"], every) and ok(accepted, config=every)
    assert not ok(accepted, config={**shipped, "approvals": ["owner_author"]}), "the comment is off when not listed"
    assert "creates it" in verdict(issue(), [], every)[1] and "board status to" in verdict(issue(), [], every)[1]
    assert "off while" not in verdict(issue(), [], every)[1]

    # 3. a missing, empty or unknown setting refuses everything
    missing = {k: v for k, v in shipped.items() if k != "approvals"}
    for bad in (missing, {**shipped, "approvals": []}, {**shipped, "approvals": ["owner_coment"]},
                {**shipped, "approvals": ["owner_comment", "anyone"]}, {**shipped, "approvals": "owner_comment"},
                {**shipped, "approvals": None}, {**shipped, "approvals": [1]}):
        for item in (accepted, owned, signed):
            allowed, why = verdict(item, ["Todo"], bad)
            assert not allowed and "merge-rules.json" in why and "'approvals'" in why, (bad, why)
            assert "owner_comment, owner_author, board_status" in why, why

    # 4. refusals win over every approval, whichever are on
    for config in (shipped, every):
        for status in ("Done", "Not planned", "Duplicate", "Canceled"):
            assert not ok(accepted, [status], config), status
            assert not ok(owned, [status], config) and not ok(issue(), ["Todo", status], config), status
        for reason, word in CLOSED_AS.items():
            allowed, why = verdict({**accepted, "state": "CLOSED", "stateReason": reason}, [], config)
            assert not allowed and word in why, why
        for name in ("wontfix", "Duplicate"):
            assert not ok({**accepted, "labels": [{"name": name}]}, config=config), name
        assert not ok(accepted, None, config), "an unreadable board refuses"
        assert not ok({**accepted, "url": "https://h/o/r/pull/7"}, config=config), "a pull request is not an issue"

    def asked(item: dict, code: int, answer: str, config: dict = shipped) -> tuple[bool, str]:
        """check_issue with gh stood in: the issue view returns item, the board query exits code with answer."""
        def run(command: list[str], **_) -> subprocess.CompletedProcess:
            view = command[1] == "issue"
            return subprocess.CompletedProcess(command, 0 if view else code, json.dumps(item) if view else answer, "")

        with mock.patch.object(subprocess, "run", run):
            return check_issue(item["number"], "o/r", boss, config)

    def board_of(*statuses: str, archived: bool = False) -> str:
        nodes = [{"isArchived": archived, "fieldValueByName": {"name": x}} for x in statuses]
        return json.dumps({"data": {"repository": {"issue": {"projectItems": {"nodes": nodes}}}}})

    def errors(*types: str) -> str:
        return json.dumps({"errors": [{"type": x, "message": "m"} for x in types]})

    # 5. the board is readable: its refusals always apply, its approvals only when switched on
    assert not asked(issue(), 0, board_of("Todo"))[0] and not asked(issue(), 0, board_of("In Progress"))[0]
    assert asked(issue(), 0, board_of("Todo"), every)[0] and asked(issue(), 0, board_of("In Progress"), every)[0]
    assert not asked(issue(), 0, board_of("Backlog"), every)[0] and not asked(issue(), 0, board_of(), every)[0]
    assert not asked(issue(), 0, board_of("Todo", archived=True), every)[0], "an archived item approves nothing"
    for config in (shipped, every):
        for status in ("Done", "Not planned", "Duplicate", "Canceled"):
            allowed, why = asked(accepted, 0, board_of(status), config)
            assert not allowed and f"its board status is '{status}'" in why, why
        assert "not read" not in asked(accepted, 0, board_of(), config)[1]

    # 6. the login lacks the scope: everything but the board works as before, and the output says so
    unscoped = errors("INSUFFICIENT_SCOPES", "INSUFFICIENT_SCOPES")
    for item, config in ((accepted, shipped), (accepted, every), (owned, every)):
        allowed, why = asked(item, 1, unscoped, config)
        assert allowed and "the board was not read" in why, why
    for item, config in ((owned, shipped), (issue(), every),
                         (issue(comments=[comment("Accepted by owner.", login="someone")]), every),
                         (issue(comments=[comment("Accepted by owner.\n\nCreated: Bot (Developer)")]), every),
                         (agent_made, every)):
        allowed, why = asked(item, 1, unscoped, config)
        assert not allowed and "not approved" in why and "the board was not read" in why, why
        assert "board status to" not in why, "a status that cannot be read is not offered as an approval"
    for name in ("wontfix", "duplicate"):
        allowed, why = asked({**accepted, "labels": [{"name": name}]}, 1, unscoped)
        assert not allowed and f"the label '{name}'" in why and "the board was not read" in why, why
    for reason, word in CLOSED_AS.items():
        allowed, why = asked({**accepted, "state": "CLOSED", "stateReason": reason}, 1, unscoped)
        assert not allowed and f"closed ({word})" in why, why

    # 7. any other failure to read the board refuses, whoever approved
    for code, answer in ((1, ""), (1, '{"message":"Bad credentials"}'), (1, "<html>502</html>"),
                         (1, errors("RATE_LIMITED")), (0, errors("FORBIDDEN")), (0, errors("NOT_FOUND")),
                         (1, errors("INSUFFICIENT_SCOPES", "RATE_LIMITED")), (1, board_of("Todo")),
                         (1, '{"errors":["INSUFFICIENT_SCOPES"]}'), (0, "null"),
                         (0, '{"data":{"repository":null}}')):
        for item, config in ((accepted, shipped), (accepted, every), (owned, every)):
            allowed, why = asked(item, code, answer, config)
            assert not allowed and "cannot be read" in why, (code, answer, why)

    here = {"number": 4, "repository": {"name": "r", "owner": {"login": "o"}}}
    away = {"number": 1, "repository": {"name": "r", "owner": {"login": "stranger"}}}
    assert linked_issues({"closingIssuesReferences": [here], "body": "Closes #4"}, "o/r") == ([4], [])
    assert linked_issues({"closingIssuesReferences": [], "body": "Refs #9\n"}, "o/r") == ([9], [])
    assert "links no issue" in linked_issues({"closingIssuesReferences": [], "body": "see #4"}, "o/r")[1][0]
    assert "another repository" in linked_issues({"closingIssuesReferences": [away], "body": ""}, "o/r")[1][0]
    print("self-test passed: a linked issue, only the owner's comment approves as shipped, the other two approvals "
          "when switched on, a bad setting refuses, refusals win, agents cannot approve, a board that is readable, "
          "out of scope or unreadable")
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
        config = rules()
        results += [check_issue(n, args.repo, is_owner, config) for n in numbers]
    for allowed, text in results:
        print("OK" if allowed else "REFUSED", text)
    passed = all(allowed for allowed, _ in results)
    what = "merge rules" if args.mode == "pr" else "implementation"
    print(f"{what}: {'allowed' if passed else 'NOT allowed'}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
