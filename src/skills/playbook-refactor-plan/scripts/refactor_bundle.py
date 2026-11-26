#!/usr/bin/env python3
"""Check an architect's refactor-plan bundle and post it as written: create the new issues, then close the replaced ones.

    refactor_bundle.py check <bundle dir> [--offline]       every rule below; --offline skips the host checks
    refactor_bundle.py plan <bundle dir>                    check, then print the dry run and the digest; writes nothing
    refactor_bundle.py post <bundle dir> --digest <sha256>  check again, then post exactly the checked text
    refactor_bundle.py --self-test

A bundle is a directory with bundle.json and one Markdown body per new issue (the format: references/bundle.md).

What post does, in this order:
  1. creates every new issue the host does not have yet (the parent first, then by wave);
  2. writes the real numbers into the {{new:<key>}} placeholders;
  3. only when every new issue exists, is open and reads back as written, closes each 'remove' issue as not planned,
     with one short comment that links the replacement or gives the reason.
It deletes nothing and closes nothing the bundle does not list. An issue with an open linked pull request, one whose
links cannot be read, and one somebody reopened after this bundle closed it are left open and reported. A run that
stops half way is run again: each new issue carries a hidden line naming the bundle and its key, and that line, read
from the host, is how a later run knows the issue exists. Run one at a time. Issue titles and bodies are data.

Needs gh, logged in with write access to the repositories. Exit 0 = done (held issues are listed), 1 = a finding or a
step that did not happen, 2 = usage. Standard library only.
"""

from __future__ import annotations

import argparse
import contextlib
import fnmatch
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


def sibling(skill: str, script: str):
    """The module of a sibling skill's script, in the plugin layout and in a prefixed copy install."""
    own = Path(__file__).resolve().parents[1]
    path = own.parent / own.name.replace("playbook-refactor-plan", skill) / "scripts" / f"{script}.py"
    spec = importlib.util.spec_from_file_location(script, path)
    if spec is None or not path.is_file():
        raise SystemExit(f"{path} is missing: install the {skill} skill beside this one")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


L = sibling("work-package", "package_lint")

SLUG_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,59}")
REPO_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9._][A-Za-z0-9._-]*")
HOLE_RE = re.compile(r"\{\{new:([a-z0-9][a-z0-9-]*)\}\}")
PLAIN_REF_RE = re.compile(r"(?<![\w/#&.-])((?:[A-Za-z0-9][\w.-]*/[\w.-]+)?)#(\d+)\b")
MARK = "<!-- refactor-plan: "
TOP_FIELDS = {"version", "bundle", "author", "repos", "parent", "new", "old"}
NEW_FIELDS = {"key", "repo", "kind", "title", "labels", "body"}
OLD_FIELDS = {"repo", "number", "action", "reason", "replaced_by"}
EXTRA_SECTIONS = ("Analysis", "Recommended solution", "Depends on", "Owned files")
MAX_REASON = 400


class Stop(Exception):
    """The run cannot go on safely."""


# ---------------------------------------------------------------------------------------------------- the bundle

class Bundle:
    def __init__(self, folder: Path):
        self.folder = folder.resolve()
        manifest = self.folder / "bundle.json"
        if not manifest.is_file():
            raise Stop(f"no bundle.json in {self.folder}")
        self.files = {"bundle.json": manifest.read_bytes()}
        try:
            data = json.loads(self.files["bundle.json"])
        except ValueError as error:
            raise Stop(f"bundle.json is not JSON: {error}")
        self.shape(data)
        self.name, self.author, self.repos = data["bundle"], data["author"], data["repos"]
        self.parent, self.old = data["parent"], data["old"]
        self.new = {x["key"]: x for x in data["new"]}
        self.text = {key: self.read(item["body"]) for key, item in self.new.items()}

    @staticmethod
    def shape(data) -> None:
        def need(ok: bool, why: str) -> None:
            if not ok:
                raise Stop(f"bundle.json: {why}")

        def words(value) -> bool:
            return isinstance(value, str) and bool(value.strip()) and "\n" not in value

        need(isinstance(data, dict) and set(data) == TOP_FIELDS, f"needs exactly the fields {sorted(TOP_FIELDS)}")
        need(data["version"] == 1, "version is 1")
        need(isinstance(data["bundle"], str) and bool(SLUG_RE.fullmatch(data["bundle"])), "bundle is a lowercase slug")
        need(words(data["author"]) and "<" not in data["author"], "author is the architect's name on one line")
        repos = data["repos"]
        need(isinstance(repos, list) and bool(repos) and all(isinstance(x, str) and REPO_RE.fullmatch(x) for x in repos)
             and len({x.lower() for x in repos}) == len(repos), "repos lists each repository in scope once, as owner/name")
        need(isinstance(data["new"], list) and bool(data["new"]) and isinstance(data["old"], list), "new and old are lists")
        keys = []
        for item in data["new"]:
            need(isinstance(item, dict) and set(item) == NEW_FIELDS, f"each new issue has exactly {sorted(NEW_FIELDS)}")
            key = item["key"]
            need(isinstance(key, str) and bool(SLUG_RE.fullmatch(key)) and key != "close", f"unusable key {key!r}")
            need(item["repo"] in repos, f"{key}: repo {item['repo']!r} is not in repos")
            need(item["kind"] in ("epic", "package"), f"{key}: kind is epic (the parent) or package")
            need(words(item["title"]) and "{{" not in item["title"], f"{key}: title is one line without placeholders")
            need(isinstance(item["labels"], list) and all(words(x) for x in item["labels"]), f"{key}: labels is a list")
            need(words(item["body"]), f"{key}: body is the path of its Markdown file")
            keys.append(key)
        need(len(set(keys)) == len(keys), "two new issues have the same key")
        need(isinstance(data["parent"], str) and data["parent"] in keys, "parent is the key of the parent card")
        for item in data["old"]:
            need(isinstance(item, dict) and set(item) <= OLD_FIELDS and {"repo", "number", "action", "reason"} <= set(item),
                 "each old entry has repo, number, action, reason and, for a removal, replaced_by")
            need(item["repo"] in repos and type(item["number"]) is int and item["number"] > 0,
                 f"old entry {item.get('repo')}#{item.get('number')}: repo in repos and a positive number")
            where = f"{item['repo']}#{item['number']}"
            need(item["action"] in ("remove", "keep"), f"{where}: action is remove or keep")
            need(words(item["reason"]) and len(item["reason"]) <= MAX_REASON,
                 f"{where}: reason is one line of at most {MAX_REASON} characters")
            need("{{" not in item["reason"] and MARK.strip() not in item["reason"] and not item["reason"].startswith("Created:"),
                 f"{where}: reason is plain text")
            need(not L.SECRET_RE.search(item["reason"]), f"{where}: reason looks like it contains a secret")
            replaced = item.get("replaced_by", [])
            need(isinstance(replaced, list) and all(x in keys for x in replaced) and len(set(replaced)) == len(replaced),
                 f"{where}: replaced_by lists keys of new issues")
            need(item["action"] == "remove" or "replaced_by" not in item, f"{where}: only a removal has replaced_by")

    def read(self, relative: str) -> str:
        path = (self.folder / relative).resolve()
        if Path(relative).is_absolute() or not path.is_relative_to(self.folder) or not path.is_file():
            raise Stop(f"body {relative!r} is not a file inside the bundle directory")
        raw = path.read_bytes()
        self.files[relative] = raw
        try:
            return raw.decode("utf-8").replace("\r\n", "\n")
        except UnicodeDecodeError:
            raise Stop(f"body {relative!r} is not UTF-8")

    def digest(self) -> str:
        """Names the checked text: post refuses any other."""
        total = hashlib.sha256()
        for name in sorted(self.files):
            total.update(f"{name}\0{len(self.files[name])}\0".encode())
            total.update(self.files[name])
        return total.hexdigest()

    def marker(self, key: str) -> str:
        return f"{MARK}{self.name}/{key} -->"

    def template(self, key: str) -> str:
        """The body to post, placeholders still in it: the architect's text with the marker line above 'Created:'.
        The marker is below every heading, so the issue's header stays the template's."""
        lines = self.text[key].rstrip().splitlines()
        above = "\n".join(lines[:-1]).rstrip()
        return f"{above}\n\n{self.marker(key)}\n\n{lines[-1]}\n"

    def ref(self, key: str, number: int, seen_from: str) -> str:
        repo = self.new[key]["repo"]
        return f"#{number}" if repo == seen_from else f"{repo}#{number}"

    def render(self, key: str, numbers: dict[str, int]) -> str:
        home = self.new[key]["repo"]
        return HOLE_RE.sub(lambda m: self.ref(m.group(1), numbers[m.group(1)], home) if m.group(1) in numbers
                           else m.group(0), self.template(key))

    def matches(self, key: str, body: str, numbers: dict[str, int]) -> bool:
        """Whether a body on the host is this issue as written: each placeholder either still there or already the
        right number. Any other difference means somebody edited it."""
        home = self.new[key]["repo"]
        pieces = HOLE_RE.split(self.template(key).rstrip())
        pattern = re.escape(pieces[0])
        for other, rest in zip(pieces[1::2], pieces[2::2]):
            choices = [re.escape("{{new:%s}}" % other)]
            if other in numbers:
                choices.append(re.escape(self.ref(other, numbers[other], home)) + r"(?!\d)")
            pattern += f"(?:{'|'.join(choices)})" + re.escape(rest)
        return re.fullmatch(pattern, (body or "").replace("\r\n", "\n").rstrip()) is not None

    def wave(self, key: str) -> int:
        found = re.search(r"^Wave: (\d+)", self.text[key], re.M)
        return int(found.group(1)) if found else 0

    def order(self) -> list[str]:
        listed = list(self.new)
        return sorted(listed, key=lambda k: (k != self.parent, self.wave(k), listed.index(k)))

    def close_comment(self, item: dict, numbers: dict[str, int]) -> str:
        replaced = item.get("replaced_by", [])
        refs = [self.ref(k, numbers[k], item["repo"]) if k in numbers else "{{new:%s}}" % k for k in replaced]
        if not refs:
            first = f"Closed: not planned. {item['reason']}"
        elif all(self.new[k]["repo"] == item["repo"] for k in replaced):
            first = f"Replaced by {', '.join(refs)}\n\n{item['reason']}"
        else:
            first = f"Closed: replaced by {', '.join(refs)}.\n\n{item['reason']}"
        return f"{first}\n\n{self.marker('close')}\n\nCreated: {self.author}\n"


def sections(body: str) -> dict[str, str]:
    return {name: content for name, _, content in L.split_sections(body, 2)[1]}


def section(body: str, name: str) -> str:
    return next((text for found, text in sections(body).items() if found == name or found.startswith(name + " ")), "")


def owned_paths(body: str) -> list[str]:
    found = []
    for line in section(body, "Owned files").splitlines():
        if line.lstrip().startswith("- "):
            for token in re.findall(r"`([^`\s]+)`", line):
                token = re.sub(r"/\*\*?$", "", token.removeprefix("./")).rstrip("/")
                if token:
                    found.append(token)
    return found


def overlap(a: str, b: str) -> bool:
    return (a == b or a.startswith(b + "/") or b.startswith(a + "/") or fnmatch.fnmatch(a, b) or fnmatch.fnmatch(b, a))


@contextlib.contextmanager
def anybodys_text():
    """The linter compares 'Created:' with AGENT_NAME; whoever posts is not the author of the architect's text."""
    name = os.environ.pop("AGENT_NAME", None)
    try:
        yield
    finally:
        if name is not None:
            os.environ["AGENT_NAME"] = name


def check_offline(bundle: Bundle) -> list[str]:
    problems: list[str] = []
    epics = [k for k, x in bundle.new.items() if x["kind"] == "epic"]
    if epics != [bundle.parent]:
        problems.append(f"exactly one new issue is the epic and it is the parent card (epics: {epics or 'none'})")
    titles: dict = {}
    ids: dict = {}
    for key, item in bundle.new.items():
        titles.setdefault((item["repo"], item["title"].strip().lower()), []).append(key)
        ids.setdefault(item["title"].split(":")[0], []).append(key)
    problems += [f"{', '.join(v)}: the same title twice in {k[0]}" for k, v in titles.items() if len(v) > 1]
    problems += [f"{', '.join(v)}: the same ID {k!r} twice" for k, v in ids.items() if len(v) > 1]

    for key, item in bundle.new.items():
        text = bundle.text[key]
        if MARK.strip() in text:
            problems.append(f"{key}: do not write the marker line; the script adds it")
            continue
        holes = HOLE_RE.findall(text)
        if len(holes) != text.count("{{new"):
            problems.append(f"{key}: a placeholder is not exactly {{{{new:<key>}}}}")
        if "#{{new" in text:
            problems.append(f"{key}: write {{{{new:<key>}}}} without '#': the script writes the whole reference")
        problems += [f"{key}: {{{{new:{x}}}}} names no new issue" for x in sorted(set(holes)) if x not in bundle.new]
        lines = text.rstrip().splitlines()
        if not lines or lines[-1] != f"Created: {bundle.author}":
            problems.append(f"{key}: the last line is 'Created: {bundle.author}', the bundle's author")
            continue
        body = bundle.template(key)
        with anybodys_text():
            problems += [f"{key}: {x}" for x in L.lint_issue(item["kind"], item["title"], item["labels"], body)]
        if L.header_problem(body):
            problems.append(f"{key}: the header is not recognised: {L.header_problem(body)}")
        if any(x.startswith("Pipeline:") for x in L.header_lines(body) or []):
            problems.append(f"{key}: a refactor plan marks no issue for a pipeline")

    packages = [k for k, x in bundle.new.items() if x["kind"] == "package"]
    if not packages:
        problems.append("a plan needs at least one package issue under the parent")
    for key in packages:
        text = bundle.text[key]
        for name in EXTRA_SECTIONS:
            if not section(text, name):
                problems.append(f"{key}: needs a filled '## {name}' section")
        if "`" not in section(text, "Analysis"):
            problems.append(f"{key}: the analysis names the code it read, in backticks")
        if not owned_paths(text):
            problems.append(f"{key}: 'Owned files' lists each path as - `path`")
        if bundle.wave(key) < 1:
            problems.append(f"{key}: a package's wave is 1 or later")
        for other in HOLE_RE.findall(section(text, "Depends on")):
            if other == bundle.parent:
                problems.append(f"{key}: the parent card is not a dependency")
            elif other in bundle.new and bundle.wave(other) >= bundle.wave(key):
                problems.append(f"{key} (wave {bundle.wave(key)}) depends on {other} (wave {bundle.wave(other)}): "
                                "a dependency is in an earlier wave")
        if bundle.parent not in HOLE_RE.findall(text):
            problems.append(f"{key}: names its parent as {{{{new:{bundle.parent}}}}}")
        if bundle.parent in bundle.new and key not in HOLE_RE.findall(bundle.text[bundle.parent]):
            problems.append(f"the parent card does not list the child {{{{new:{key}}}}}")
    waves = sorted({bundle.wave(k) for k in packages if bundle.wave(k) > 0})
    if waves and waves != list(range(1, waves[-1] + 1)):
        problems.append(f"waves run 1, 2, 3 without a gap (got {waves})")
    for index, a in enumerate(packages):
        for b in packages[index + 1:]:
            if bundle.new[a]["repo"] != bundle.new[b]["repo"] or bundle.wave(a) != bundle.wave(b):
                continue
            shared = sorted({x for x in owned_paths(bundle.text[a]) for y in owned_paths(bundle.text[b]) if overlap(x, y)})
            if shared:
                problems.append(f"{a} and {b} are in wave {bundle.wave(a)} and both own {', '.join(shared)}: "
                                "one wave never shares a file")

    listed: set = set()
    for item in bundle.old:
        where = (item["repo"], item["number"])
        if where in listed:
            problems.append(f"{item['repo']}#{item['number']} is listed twice")
        listed.add(where)
        comment = bundle.close_comment(item, {k: 1 for k in bundle.new})
        if item["action"] == "remove":
            with anybodys_text():
                problems += [f"close comment of {item['repo']}#{item['number']}: {x}"
                             for x in L.lint_comment("close", comment)]
    return problems


# ---------------------------------------------------------------------------------------------------- the host

class State:
    """What the host says now: every issue and pull request of the repositories in scope, and the new issues of this
    bundle that exist already."""

    def __init__(self, bundle: Bundle, host):
        self.viewer = host.viewer()
        self.items = {repo: {x["number"]: x for x in host.issues(repo)} for repo in bundle.repos}
        self.labels = {repo: {x.lower() for x in host.labels(repo)} for repo in bundle.repos}
        self.numbers: dict[str, int] = {}
        self.problems: list[str] = []
        for repo, items in self.items.items():
            for number, issue in sorted(items.items()):
                if issue["is_pr"]:
                    continue
                key = marked_key(bundle, issue["body"])
                where = f"{repo}#{number}"
                if key is None:
                    if issue["user"] == self.viewer and f"{MARK}{bundle.name}/" in issue["body"]:
                        self.problems.append(f"{where} has this bundle's marker away from its last lines: somebody edited "
                                             "a new issue, and posting again could duplicate it")
                    continue
                if issue["user"] != self.viewer:
                    self.problems.append(f"{where} carries this bundle's marker but {issue['user']!r} opened it, not "
                                         f"{self.viewer!r}: look at it before anything is posted")
                elif key not in bundle.new or bundle.new[key]["repo"] != repo:
                    self.problems.append(f"{where} carries the marker of {key!r}, which this bundle does not post there: "
                                         "a changed plan needs a new bundle name")
                elif key in self.numbers:
                    self.problems.append(f"{where} and #{self.numbers[key]} are both the new issue {key!r}")
                else:
                    self.numbers[key] = number
        for key, number in self.numbers.items():
            issue = self.items[bundle.new[key]["repo"]][number]
            if issue["title"] != bundle.new[key]["title"] or not bundle.matches(key, issue["body"], self.numbers):
                self.problems.append(f"{bundle.new[key]['repo']}#{number} is the new issue {key!r} but its title or body "
                                     "was changed: it is not overwritten")

    def ours(self, bundle: Bundle, repo: str) -> set[int]:
        return {n for k, n in self.numbers.items() if bundle.new[k]["repo"] == repo}


def marked_key(bundle: Bundle, body: str) -> str | None:
    """The key in this bundle's marker, which counts only as the last line above the closing 'Created:' line."""
    lines = [x for x in (body or "").replace("\r\n", "\n").split("\n") if x.strip()]
    if len(lines) < 2 or not lines[-1].startswith("Created: "):
        return None
    found = re.fullmatch(re.escape(f"{MARK}{bundle.name}/") + r"([a-z0-9][a-z0-9-]*) -->", lines[-2].rstrip())
    return found.group(1) if found and found.group(1) != "close" else None


def outside_code(body: str) -> str:
    return re.sub(r"`[^`\n]*`", " ", re.sub(r"(?ms)^\s*(```|~~~).*?^\s*\1[^\n]*$", " ", body))


def check_online(bundle: Bundle, state: State) -> list[str]:
    problems = list(state.problems)
    for key, item in bundle.new.items():
        missing = [x for x in item["labels"] if x.lower() not in state.labels[item["repo"]]]
        if missing:
            problems.append(f"{key}: {item['repo']} has no label {', '.join(missing)}")
    listed = {(x["repo"], x["number"]): x for x in bundle.old}
    removed = {k for k, x in listed.items() if x["action"] == "remove"}
    for (repo, number), item in listed.items():
        issue = state.items[repo].get(number)
        if issue is None or issue["is_pr"]:
            problems.append(f"{repo}#{number} is {'a pull request' if issue else 'not there'}: old entries are issues")
        elif number in state.ours(bundle, repo):
            problems.append(f"{repo}#{number} is a new issue of this bundle, so it cannot also be an old one")
    for repo, items in state.items.items():
        for number, issue in sorted(items.items()):
            open_issue = issue["state"] == "open" and not issue["is_pr"] and number not in state.ours(bundle, repo)
            if open_issue and (repo, number) not in listed:
                problems.append(f"{repo}#{number} {issue['title'][:60]!r} is open and has no disposition (remove or keep)")
            if open_issue and (repo, number) not in removed:
                for key, item in bundle.new.items():
                    if item["repo"] == repo and item["title"].strip().lower() == issue["title"].strip().lower():
                        problems.append(f"{key}: {repo}#{number} is open with the same title and is not removed")
    for key, item in bundle.new.items():
        for part, text in (("body", bundle.text[key]), ("Depends on", section(bundle.text[key], "Depends on"))):
            for other, digits in PLAIN_REF_RE.findall(outside_code(text)):
                repo, number = other or item["repo"], int(digits)
                found = state.items.get(repo, {}).get(number)
                if found is None:
                    problem = f"{key}: {other}#{number} is not an issue or pull request of the repositories in scope"
                elif part == "Depends on" and (repo, number) in removed:
                    problem = f"{key}: depends on {repo}#{number}, which the bundle removes: name its replacement"
                elif part == "Depends on" and found["state"] != "open" and found["state_reason"] != "completed":
                    problem = f"{key}: depends on {repo}#{number}, which was closed without being completed"
                else:
                    continue
                if problem not in problems:
                    problems.append(problem)
    return problems


class GhHost:
    """The host through gh. Every call is an argument list and every body goes as JSON on stdin: no issue text ever
    reaches a shell. It has no call that deletes."""

    LINKS = """query($owner:String!,$name:String!,$number:Int!,$after:String){repository(owner:$owner,name:$name){
issue(number:$number){closedByPullRequestsReferences(first:100,includeClosedPrs:false){pageInfo{hasNextPage}
nodes{url state}}timelineItems(first:100,after:$after,itemTypes:[CROSS_REFERENCED_EVENT,CONNECTED_EVENT]){
pageInfo{hasNextPage endCursor}nodes{__typename ... on CrossReferencedEvent{source{__typename ... on PullRequest{
url state}}} ... on ConnectedEvent{subject{__typename ... on PullRequest{url state}}}}}}}}"""

    def __init__(self, read_only: bool, run=subprocess.run):
        self.read_only, self.run = read_only, run

    def gh(self, args: list[str], payload: dict | None = None) -> str:
        try:
            done = self.run(["gh", *args], input=None if payload is None else json.dumps(payload), capture_output=True,
                            text=True, timeout=120)
        except subprocess.TimeoutExpired:
            raise Stop(f"gh {' '.join(args[:4])} timed out; whether it happened is read from the host on the next run")
        if done.returncode:
            raise Stop(f"gh {' '.join(args[:4])} failed: {(done.stderr or done.stdout).strip()[:300]}")
        return done.stdout

    def pages(self, path: str) -> list:
        text, found, at = self.gh(["api", "--paginate", path]), [], 0
        decoder = json.JSONDecoder()
        while text[at:].strip():
            at += len(text[at:]) - len(text[at:].lstrip())
            page, at = decoder.raw_decode(text, at)
            if not isinstance(page, list):
                raise Stop(f"gh api {path}: not a list")
            found += page
        return found

    @staticmethod
    def shaped(raw: dict) -> dict:
        return {"number": raw["number"], "title": raw["title"], "body": raw.get("body") or "", "state": raw["state"],
                "state_reason": raw.get("state_reason") or "", "user": (raw.get("user") or {}).get("login", ""),
                "is_pr": "pull_request" in raw}

    def viewer(self) -> str:
        name = self.gh(["api", "user", "--jq", ".login"]).strip()
        if not name:
            raise Stop("gh does not say who is logged in")
        return name

    def issues(self, repo: str) -> list[dict]:
        return [self.shaped(x) for x in self.pages(f"repos/{repo}/issues?state=all&per_page=100")]

    def issue(self, repo: str, number: int) -> dict:
        return self.shaped(json.loads(self.gh(["api", f"repos/{repo}/issues/{number}"])))

    def labels(self, repo: str) -> list[str]:
        return [x["name"] for x in self.pages(f"repos/{repo}/labels?per_page=100")]

    def comments(self, repo: str, number: int) -> list[dict]:
        return [{"user": (x.get("user") or {}).get("login", ""), "body": x.get("body") or ""}
                for x in self.pages(f"repos/{repo}/issues/{number}/comments?per_page=100")]

    def linked_open_prs(self, repo: str, number: int) -> list[str] | None:
        """Open pull requests that close, are connected to or mention the issue. None: it cannot be told."""
        owner, name = repo.split("/")
        found: set[str] = set()
        after = None
        try:
            for _ in range(50):
                args = ["api", "graphql", "-f", f"query={self.LINKS}", "-f", f"owner={owner}", "-f", f"name={name}",
                        "-F", f"number={number}"] + (["-f", f"after={after}"] if after else [])
                answer = json.loads(self.gh(args))
                if answer.get("errors"):
                    return None
                issue = answer["data"]["repository"]["issue"]
                closing = issue["closedByPullRequestsReferences"]
                if closing["pageInfo"]["hasNextPage"]:
                    return None
                found |= {x["url"] for x in closing["nodes"] if x["state"] == "OPEN"}
                timeline = issue["timelineItems"]
                for event in timeline["nodes"]:
                    other = event.get("source") or event.get("subject") or {}
                    if other.get("__typename") == "PullRequest" and other["state"] == "OPEN":
                        found.add(other["url"])
                if not timeline["pageInfo"]["hasNextPage"]:
                    return sorted(found)
                after = timeline["pageInfo"]["endCursor"]
        except (Stop, ValueError, KeyError, TypeError, AttributeError):
            return None
        return None

    def write(self, method: str, path: str, payload: dict) -> dict:
        if self.read_only:
            raise Stop(f"refusing to {method} {path}: this command only reads")
        return json.loads(self.gh(["api", "-X", method, path, "--input", "-"], payload))

    def create(self, repo: str, title: str, body: str, labels: list[str]) -> int:
        return self.write("POST", f"repos/{repo}/issues", {"title": title, "body": body, "labels": labels})["number"]

    def edit_body(self, repo: str, number: int, body: str) -> None:
        self.write("PATCH", f"repos/{repo}/issues/{number}", {"body": body})

    def comment(self, repo: str, number: int, body: str) -> None:
        self.write("POST", f"repos/{repo}/issues/{number}/comments", {"body": body})

    def close_not_planned(self, repo: str, number: int) -> None:
        self.write("PATCH", f"repos/{repo}/issues/{number}", {"state": "closed", "state_reason": "not_planned"})


# ---------------------------------------------------------------------------------------------------- commands

def dry_run(bundle: Bundle, host, state: State) -> list[str]:
    out = [f"Bundle {bundle.name} by {bundle.author}", f"Repositories: {', '.join(bundle.repos)}", "",
           f"1. New issues ({len(bundle.new)}), created in this order:"]
    for key in bundle.order():
        item = bundle.new[key]
        have = f"exists as #{state.numbers[key]}" if key in state.numbers else "create"
        out.append(f"   {have}: {item['repo']} wave {bundle.wave(key)} '{item['title']}' [{', '.join(item['labels'])}] "
                   f"({{{{new:{key}}}}})")
    out += ["", "2. Fill the new numbers into every {{new:<key>}} placeholder.", ""]
    close, held, closed, keep = [], [], [], []
    for item in bundle.old:
        issue = state.items[item["repo"]][item["number"]]
        name = f"{item['repo']}#{item['number']} '{issue['title'][:70]}'"
        if issue["state"] != "open":
            closed.append(f"   {name}: already closed, left as it is")
        elif item["action"] == "keep":
            keep.append(f"   {name}: {item['reason']}")
        else:
            links = host.linked_open_prs(item["repo"], item["number"])
            if links is None:
                held.append(f"   {name}: its linked pull requests cannot be read")
            elif links:
                held.append(f"   {name}: open linked pull request {', '.join(links)}")
            else:
                first = bundle.close_comment(item, state.numbers).splitlines()[0]
                close.append(f"   {name}\n      comment: {first} | {item['reason']}")
    for title, rows in (("3. Then close as not planned, each with one comment", close),
                        ("Not closed automatically (reported)", held), ("Kept open", keep), ("Already closed", closed)):
        out += [f"{title} ({len(rows)}):", *rows, ""]
    return out + [f"Digest: {bundle.digest()}", "Dry run: nothing was posted."]


def checked(bundle: Bundle, host) -> State:
    problems = check_offline(bundle)
    state = None
    if not problems:
        state = State(bundle, host)
        problems = check_online(bundle, state)
    if problems:
        raise Stop("the bundle does not pass; nothing was posted:\n" + "\n".join(f"  - {x}" for x in problems))
    return state


def post(bundle: Bundle, host, digest: str, say=print) -> int:
    state = checked(bundle, host)
    if digest != bundle.digest():
        raise Stop(f"the bundle's digest is {bundle.digest()}, not the one given: it is not the text that was checked "
                   "and reported; nothing was posted")
    numbers = dict(state.numbers)

    for key in bundle.order():
        item = bundle.new[key]
        if key not in numbers:
            numbers[key] = host.create(item["repo"], item["title"], bundle.render(key, numbers), item["labels"])
            say(f"created {item['repo']}#{numbers[key]}: {item['title']}")

    final = {}
    for key in bundle.order():
        item = bundle.new[key]
        repo, number = item["repo"], numbers[key]
        want = bundle.render(key, numbers)
        found = host.issue(repo, number)
        if found["title"] != item["title"] or not bundle.matches(key, found["body"], numbers):
            raise Stop(f"{repo}#{number} does not read back as written; nothing was closed")
        if found["body"].replace("\r\n", "\n").rstrip() != want.rstrip():
            host.edit_body(repo, number, want)
            say(f"filled the numbers in {repo}#{number}")
        final[key] = want
    for key, want in final.items():
        repo, number = bundle.new[key]["repo"], numbers[key]
        found = host.issue(repo, number)
        if found["state"] != "open" or found["body"].replace("\r\n", "\n").rstrip() != want.rstrip():
            raise Stop(f"{repo}#{number} ({key}) is {found['state']} or does not hold its final text; nothing was closed")

    closed, held, failed = [], [], []
    for item in bundle.old:
        if item["action"] != "remove":
            continue
        repo, number = item["repo"], item["number"]
        where = f"{repo}#{number}"
        found = host.issue(repo, number)
        if found["state"] != "open":
            held.append(f"{where}: already closed, left as it is")
            continue
        ours = any(x["user"] == state.viewer and bundle.marker("close") in x["body"].splitlines()
                   for x in host.comments(repo, number))
        if ours and found["state_reason"] == "reopened":
            held.append(f"{where}: somebody reopened it after this bundle closed it; not closed again")
            continue
        links = host.linked_open_prs(repo, number)
        if links is None:
            failed.append(f"{where}: its linked pull requests cannot be read; not closed")
            continue
        if links:
            held.append(f"{where}: open linked pull request {', '.join(links)}; never closed automatically")
            continue
        gone = [k for k in item.get("replaced_by", [])
                if host.issue(bundle.new[k]["repo"], numbers[k])["state"] != "open"]
        if gone:
            failed.append(f"{where}: its replacement {', '.join(gone)} is not open; not closed")
            continue
        if not ours:
            host.comment(repo, number, bundle.close_comment(item, numbers))
        host.close_not_planned(repo, number)
        after = host.issue(repo, number)
        if after["state"] == "closed" and after["state_reason"] == "not_planned":
            closed.append(where)
            say(f"closed {where} as not planned")
        else:
            failed.append(f"{where}: reads back as {after['state']} {after['state_reason']}".rstrip())

    say("")
    say("New: " + ", ".join(f"{bundle.new[k]['repo']}#{numbers[k]}" for k in bundle.order()))
    say(f"Parent: {bundle.new[bundle.parent]['repo']}#{numbers[bundle.parent]}")
    say(f"Closed as not planned ({len(closed)}): {', '.join(closed) or 'none'}")
    for title, rows in (("Not closed (reported)", held), ("Failed: run post again once fixed", failed)):
        if rows:
            say(f"{title}:")
            for row in rows:
                say(f"  - {row}")
    return 1 if failed else 0


def main(argv: list[str], host=None) -> int:
    if argv[:1] == ["--self-test"]:
        return self_test()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "plan", "post"):
        command = sub.add_parser(name)
        command.add_argument("bundle")
        if name == "check":
            command.add_argument("--offline", action="store_true", help="only what needs no host")
        if name == "post":
            command.add_argument("--digest", required=True, help="the digest the dry run printed")
    args = parser.parse_args(argv)
    try:
        bundle = Bundle(Path(args.bundle))
        if args.command == "check" and args.offline:
            problems = check_offline(bundle)
            if problems:
                raise Stop("\n".join(f"  - {x}" for x in problems))
            print(f"OK offline: {len(bundle.new)} new issues, {len(bundle.old)} dispositions; the host was not read. "
                  f"Digest: {bundle.digest()}")
            return 0
        if host is None:
            if not shutil.which("gh"):
                raise Stop("gh is not installed")
            host = GhHost(read_only=args.command != "post")
        if args.command == "post":
            return post(bundle, host, args.digest)
        state = checked(bundle, host)
        if args.command == "plan":
            print("\n".join(dry_run(bundle, host, state)))
        else:
            print(f"OK: {len(bundle.new)} new issues, {len(bundle.old)} dispositions, every open issue listed. "
                  f"Digest: {bundle.digest()}")
        return 0
    except Stop as stop:
        print(f"STOP {stop}", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------------------------------- self-test

EXAMPLE = Path(__file__).resolve().parents[1] / "assets" / "example" / "bundle"
API, WEB = "example-org/orders-api", "example-org/orders-web"


class Interrupted(Exception):
    pass


class FakeHost:
    """An in-memory host. 'budget' interrupts the run after that many writes."""

    def __init__(self, bundle: Bundle):
        self.me = "poster"
        self.repos: dict = {repo: {} for repo in bundle.repos}
        self.notes: dict = {}
        self.links: dict = {}
        self.writes: list = []
        self.budget = None
        self.known = {x for item in bundle.new.values() for x in item["labels"]}
        for item in bundle.old:
            self.add(item["repo"], item["number"], f"Old issue {item['number']}", "somebody wrote this")
        self.add(API, 90, "A closed one", "done", state="closed", state_reason="completed")

    def add(self, repo, number, title, body, state="open", state_reason="", user="someone", is_pr=False):
        self.repos[repo][number] = {"number": number, "title": title, "body": body, "state": state,
                                    "state_reason": state_reason, "user": user, "is_pr": is_pr}

    def spend(self, *what):
        if self.budget is not None:
            if self.budget == 0:
                raise Interrupted()
            self.budget -= 1
        self.writes.append(what)

    def viewer(self):
        return self.me

    def issues(self, repo):
        return [dict(x) for x in self.repos[repo].values()]

    def issue(self, repo, number):
        return dict(self.repos[repo][number])

    def labels(self, repo):
        return list(self.known)

    def comments(self, repo, number):
        return list(self.notes.get((repo, number), []))

    def linked_open_prs(self, repo, number):
        return self.links.get((repo, number), [])

    def create(self, repo, title, body, labels):
        self.spend("create", repo, title)
        number = max([100, *self.repos[repo]]) + 1
        self.add(repo, number, title, body, user=self.me)
        return number

    def edit_body(self, repo, number, body):
        self.spend("edit", repo, number)
        self.repos[repo][number]["body"] = body

    def comment(self, repo, number, body):
        self.spend("comment", repo, number)
        self.notes.setdefault((repo, number), []).append({"user": self.me, "body": body})

    def close_not_planned(self, repo, number):
        self.spend("close", repo, number)
        self.repos[repo][number].update(state="closed", state_reason="not_planned")

    def picture(self):
        return (self.repos, self.notes)


def self_test() -> int:
    quiet = lambda *_: None  # noqa: E731
    good = Bundle(EXAMPLE)
    assert check_offline(good) == [], check_offline(good)
    removals = [x for x in good.old if x["action"] == "remove"]
    kept = [x for x in good.old if x["action"] == "keep"]
    assert removals and kept and len(good.repos) == 2, "the example shows both actions across two repositories"

    # offline: each broken rule is a finding
    with tempfile.TemporaryDirectory() as folder:
        def broken(change, needle: str, name: str | None = None) -> None:
            target = Path(folder, "b")
            shutil.rmtree(target, ignore_errors=True)
            shutil.copytree(EXAMPLE, target)
            data = json.loads((target / "bundle.json").read_text(encoding="utf-8"))
            if name:
                path = target / name
                before = path.read_text(encoding="utf-8")
                after = change(before)
                assert after != before, f"the case for {needle!r} changed nothing"
                path.write_text(after, encoding="utf-8")
            else:
                change(data)
                (target / "bundle.json").write_text(json.dumps(data), encoding="utf-8")
            try:
                found = check_offline(Bundle(target))
            except Stop as stop:
                found = [str(stop)]
            assert any(needle in x for x in found), (needle, found)

        broken(lambda d: d.update(extra=1), "exactly the fields")
        broken(lambda d: d["new"][1].update(body="../outside.md"), "inside the bundle")
        broken(lambda d: d["new"][1].update(body="/etc/hostname"), "inside the bundle")
        broken(lambda d: d["new"][1].update(repo="other/repo"), "not in repos")
        broken(lambda d: d["new"][1].update(key="close"), "unusable key")
        broken(lambda d: d["new"][1].update(kind="epic"), "exactly one new issue is the epic")
        broken(lambda d: d["new"][1].update(title="no id here"), "title")
        broken(lambda d: d["new"][1].update(labels=["refactor"]), "exactly one lane")
        broken(lambda d: d["new"][2].update(title=d["new"][1]["title"]), "the same title twice")
        broken(lambda d: d["old"][0].update(action="delete"), "action is remove or keep")
        broken(lambda d: d["old"][0].update(reason=""), "reason is one line")
        broken(lambda d: d["old"][0].update(reason="a\nb"), "reason is one line")
        broken(lambda d: d["old"][0].update(reason="use token=abcdefghij123"), "secret")
        broken(lambda d: d["old"][0].update(replaced_by=["nothing"]), "replaced_by lists keys")
        broken(lambda d: [x for x in d["old"] if x["action"] == "keep"][0].update(replaced_by=[]), "only a removal")
        broken(lambda d: d["old"].append(dict(d["old"][0])), "listed twice")
        broken(lambda t: t.replace("## Analysis", "## Background"), "filled '## Analysis'", "issues/api-1.md")
        broken(lambda t: t.replace("## Recommended solution", "## Idea"), "'## Recommended solution'", "issues/api-1.md")
        broken(lambda t: t.replace("## Done when", "## Later"), "Done when", "issues/api-1.md")
        broken(lambda t: t.replace("Difficulty: medium", "Difficulty: simple"), "difficulty label", "issues/api-1.md")
        broken(lambda t: "<!--\n" + t, "header", "issues/api-1.md")
        broken(lambda t: t.replace("Priority: medium\n", "Priority: medium\nPipeline: quick\n"), "marks no issue", "issues/api-1.md")
        broken(lambda t: t.replace("Created: ", f"{good.marker('x')}\n\nCreated: "), "do not write the marker", "issues/api-1.md")
        broken(lambda t: t.replace("Created: ", "Created: Somebody "), "the bundle's author", "issues/api-1.md")
        broken(lambda t: t.replace("{{new:epic}}", "{{new:nobody}}"), "names no new issue", "issues/api-1.md")
        broken(lambda t: t.replace("{{new:epic}}", "{{new: epic}}"), "not exactly", "issues/api-1.md")
        broken(lambda t: t.replace("{{new:epic}}", "#{{new:epic}}"), "without '#'", "issues/api-1.md")
        broken(lambda t: t.replace("{{new:epic}}", "the parent"), "names its parent", "issues/api-1.md")
        broken(lambda t: t.replace("{{new:api-2}}", "the second"), "does not list the child", "issues/epic.md")
        broken(lambda t: t.replace("Wave: 2", "Wave: 1"), "a dependency is in an earlier wave", "issues/api-2.md")
        broken(lambda t: t.replace("Wave: 2", "Wave: 4"), "without a gap", "issues/api-2.md")
        # two packages of one repository in one wave may not own the same file; in two repositories they may
        broken(lambda t: t.replace("Wave: 2", "Wave: 1").replace("`internal/http/orders.go`", "`internal/orders/`"),
               "never shares a file", "issues/api-2.md")
    assert overlap("internal/orders", "internal/orders/query.go") and overlap("web/*.ts", "web/a.ts")
    assert not overlap("internal/orders", "internal/orders2/x.go")

    host = FakeHost(good)
    assert check_online(good, State(good, host)) == [], check_online(good, State(good, host))
    first, second = removals[0], removals[1]

    def online(change, needle: str) -> None:
        fake = FakeHost(good)
        change(fake)
        found = check_online(good, State(good, fake))
        assert any(needle in x for x in found), (needle, found)

    online(lambda h: h.add(WEB, 77, "Nobody listed me", "x"), "no disposition")
    online(lambda h: h.repos[first["repo"]].pop(first["number"]), "not there")
    online(lambda h: h.repos[first["repo"]][first["number"]].update(is_pr=True), "a pull request")
    online(lambda h: h.known.discard("refactor"), "has no label")
    online(lambda h: h.repos[kept[0]["repo"]][kept[0]["number"]].update(title=good.new["api-1"]["title"])
           if kept[0]["repo"] == API else h.add(API, 78, good.new["api-1"]["title"], "x"), "same title")
    online(lambda h: h.add(API, 79, "marker", good.render("api-1", {}), user="stranger"), "'stranger' opened it")
    online(lambda h: [h.add(API, n, good.new["api-1"]["title"], good.render("api-1", {}), user=h.me) for n in (80, 81)],
           "are both the new issue")
    online(lambda h: h.add(API, 82, good.new["api-1"]["title"], good.render("api-1", {}).replace("## Goal", "## Goal\nedited"),
                           user=h.me), "was changed")
    online(lambda h: h.add(API, 83, "x", f"text\n\n{good.marker('gone')}\n\nCreated: x\n", user=h.me), "needs a new bundle name")
    online(lambda h: h.add(API, 84, good.new["api-1"]["title"], good.render("api-1", {}) + "\nadded later\n",
                           state="closed", user=h.me), "could duplicate it")
    assert marked_key(good, f"quoting {good.marker('api-1')} in text\n\nCreated: x") is None
    assert marked_key(good, f"{good.marker('api-1')}\n\nmore text\n\nCreated: x") is None

    # references written as plain numbers resolve too
    with tempfile.TemporaryDirectory() as folder:
        for ref, needle in (("#4444", "is not an issue"), ("other/repo#1", "is not an issue"),
                            (f"#{first['number']}", "which the bundle removes")):
            target = Path(folder, "r")
            shutil.rmtree(target, ignore_errors=True)
            shutil.copytree(EXAMPLE, target)
            path = target / "issues/api-1.md"
            path.write_text(path.read_text(encoding="utf-8").replace("## Depends on\n", f"## Depends on\n- {ref}\n"),
                            encoding="utf-8")
            changed = Bundle(target)
            found = check_online(changed, State(changed, FakeHost(changed)))
            assert any(needle in x for x in found), (needle, found)

    # the dry run writes nothing
    host = FakeHost(good)
    text = "\n".join(dry_run(good, host, State(good, host)))
    assert host.writes == [] and good.digest() in text and "nothing was posted" in text
    assert f"{first['repo']}#{first['number']}" in text

    def fresh() -> FakeHost:
        fake = FakeHost(good)
        fake.links[(second["repo"], second["number"])] = ["https://example.invalid/pull/5"]
        return fake

    # a full run
    host = fresh()
    said: list[str] = []
    assert post(good, host, good.digest(), said.append) == 0, said
    kinds = [x[0] for x in host.writes]
    assert max(i for i, k in enumerate(kinds) if k in ("create", "edit")) < kinds.index("comment"), "create first, then close"
    assert kinds.count("create") == len(good.new) and kinds.count("close") == len(removals) - 1
    numbers = State(good, host).numbers
    assert set(numbers) == set(good.new) and State(good, host).problems == []
    for key, item in good.new.items():
        body = host.repos[item["repo"]][numbers[key]]["body"]
        assert "{{" not in body and body == good.render(key, numbers) and L.header_problem(body) == ""
    assert f"{WEB}#{numbers['web-1']}" in host.repos[API][numbers["epic"]]["body"], "another repository: the full reference"
    for item in removals:
        issue = host.repos[item["repo"]][item["number"]]
        if item is second:
            assert issue["state"] == "open" and (second["repo"], second["number"]) not in host.notes
        else:
            assert (issue["state"], issue["state_reason"]) == ("closed", "not_planned")
            notes = host.notes[(item["repo"], item["number"])]
            assert len(notes) == 1 and item["reason"] in notes[0]["body"] and "{{" not in notes[0]["body"]
            with anybodys_text():
                assert L.lint_comment("close", notes[0]["body"]) == []
    for item in kept:
        assert host.repos[item["repo"]][item["number"]]["state"] == "open" and (item["repo"], item["number"]) not in host.notes
    assert any("never closed automatically" in x for x in said)
    total, done = len(host.writes), json.dumps(sorted((r, sorted(v.items())) for r, v in host.repos.items()))
    assert post(good, host, good.digest(), quiet) == 0 and len(host.writes) == total, "a second run writes nothing"

    # interrupted after any number of writes, then run again: the same end, no duplicate issue, no second comment
    for budget in range(total):
        fake = fresh()
        fake.budget = budget
        try:
            post(good, fake, good.digest(), quiet)
        except Interrupted:
            pass
        else:
            raise AssertionError(f"budget {budget} did not interrupt")
        if any(x[0] in ("comment", "close") for x in fake.writes):
            assert len([x for x in fake.writes if x[0] == "create"]) == len(good.new)
        fake.budget = None
        assert post(good, fake, good.digest(), quiet) == 0, budget
        assert json.dumps(sorted((r, sorted(v.items())) for r, v in fake.repos.items())) == done, budget
        assert all(len(v) == 1 for v in fake.notes.values()) and len(fake.writes) == total, budget

    def refused(fake: FakeHost, needle: str, digest: str | None = None) -> None:
        try:
            post(good, fake, digest or good.digest(), quiet)
        except Stop as stop:
            assert needle in str(stop), (needle, str(stop))
        else:
            raise AssertionError(f"post went on: {needle}")
        assert not any(x[0] in ("comment", "close") for x in fake.writes), needle

    fake = fresh()
    refused(fake, "not the text that was checked", "0" * 64)
    assert fake.writes == []
    fake = fresh()
    fake.add(API, 77, "Opened after the plan", "x")
    refused(fake, "no disposition")
    assert fake.writes == []

    # a new issue somebody edited or closed: nothing is overwritten and nothing is closed
    for change, needle in ((lambda i: i.update(body=i["body"].replace("## Goal", "## Goal\nmine")), "was changed"),
                           (lambda i: i.update(state="closed"), "nothing was closed")):
        fake = fresh()
        fake.budget = len(good.new)
        with contextlib.suppress(Interrupted):
            post(good, fake, good.digest(), quiet)
        victim = fake.repos[API][State(good, fake).numbers["api-1"]]
        change(victim)
        before = victim["body"]
        fake.budget = None
        refused(fake, needle)
        assert victim["body"] == before, "an edited issue is not overwritten"

    # an issue opened while a run was stopped: the architect adds its disposition under the same name, and the posted
    # issues are found again
    with tempfile.TemporaryDirectory() as folder:
        fake = fresh()
        fake.budget = 2
        with contextlib.suppress(Interrupted):
            post(good, fake, good.digest(), quiet)
        fake.budget = None
        fake.add(WEB, 55, "Opened while the run was stopped", "x")
        target = Path(folder, "again")
        shutil.copytree(EXAMPLE, target)
        data = json.loads((target / "bundle.json").read_text(encoding="utf-8"))
        data["old"].append({"repo": WEB, "number": 55, "action": "keep", "reason": "Not part of this plan."})
        (target / "bundle.json").write_text(json.dumps(data), encoding="utf-8")
        again = Bundle(target)
        assert again.digest() != good.digest() and post(again, fake, again.digest(), quiet) == 0
        assert len([x for x in fake.writes if x[0] == "create"]) == len(good.new)

    # reopened after our close: reported, not closed again; closed by somebody else: left alone
    fake = fresh()
    assert post(good, fake, good.digest(), quiet) == 0
    fake.repos[first["repo"]][first["number"]].update(state="open", state_reason="reopened")
    total, said = len(fake.writes), []
    assert post(good, fake, good.digest(), said.append) == 0 and len(fake.writes) == total
    assert any("reopened" in x for x in said)
    fake = fresh()
    fake.repos[first["repo"]][first["number"]].update(state="closed", state_reason="completed")
    assert post(good, fake, good.digest(), quiet) == 0 and (first["repo"], first["number"]) not in fake.notes

    # links that cannot be read: left open, and the run fails
    fake = fresh()
    fake.links[(first["repo"], first["number"])] = None
    assert post(good, fake, good.digest(), quiet) == 1 and fake.repos[first["repo"]][first["number"]]["state"] == "open"
    assert (first["repo"], first["number"]) not in fake.notes

    gh_self_test()
    print("self-test passed: every open issue disposed, new issues linted, create before close, resumable, nothing deleted")
    return 0


def gh_self_test() -> None:
    """GhHost against a scripted gh: what it sends, and that a doubtful answer about linked PRs is never 'none'."""
    calls: list = []
    answers: list = []

    class Done:
        def __init__(self, stdout, code=0):
            self.stdout, self.stderr, self.returncode = stdout, "boom" if code else "", code

    def run(argv, input=None, **_):
        calls.append((argv, input))
        return answers.pop(0)

    host = GhHost(read_only=False, run=run)
    raw = {"number": 1, "title": "t", "body": None, "state": "open", "user": {"login": "u"}}
    answers.append(Done(json.dumps([raw]) + "\n" + json.dumps([{**raw, "number": 2, "pull_request": {}}])))
    assert [(x["number"], x["is_pr"], x["body"]) for x in host.issues("o/r")] == [(1, False, ""), (2, True, "")]
    assert calls[-1][0] == ["gh", "api", "--paginate", "repos/o/r/issues?state=all&per_page=100"]
    answers.append(Done("{}"))
    host.close_not_planned("o/r", 3)
    assert calls[-1][0] == ["gh", "api", "-X", "PATCH", "repos/o/r/issues/3", "--input", "-"]
    assert json.loads(calls[-1][1]) == {"state": "closed", "state_reason": "not_planned"}
    answers.append(Done('{"number": 9}'))
    assert host.create("o/r", "t", "$(rm -rf /) `x`", ["a"]) == 9 and "rm -rf" not in " ".join(calls[-1][0])

    def links(nodes=(), closing=(), more=False, cursor=False) -> str:
        return json.dumps({"data": {"repository": {"issue": {
            "closedByPullRequestsReferences": {"pageInfo": {"hasNextPage": more}, "nodes": list(closing)},
            "timelineItems": {"pageInfo": {"hasNextPage": cursor, "endCursor": "c1"}, "nodes": list(nodes)}}}}})

    pr = {"__typename": "PullRequest", "url": "u1", "state": "OPEN"}
    answers += [Done(links(nodes=[{"source": {"__typename": "Issue"}}], cursor=True)),
                Done(links(nodes=[{"subject": pr}, {"source": {**pr, "url": "u2", "state": "MERGED"}}],
                           closing=[{"url": "u3", "state": "OPEN"}]))]
    assert host.linked_open_prs("o/r", 3) == ["u1", "u3"] and "after=c1" in calls[-1][0]
    answers.append(Done(links()))
    assert host.linked_open_prs("o/r", 3) == []
    for answer in (Done("", 1), Done("not json"), Done('{"errors": [1]}'), Done('{"data": {"repository": null}}'),
                   Done(links(more=True))):
        answers.append(answer)
        assert host.linked_open_prs("o/r", 3) is None, answer.stdout
    def slow(argv, **_):
        raise subprocess.TimeoutExpired(argv, 120)

    assert GhHost(read_only=True, run=slow).linked_open_prs("o/r", 3) is None
    try:
        GhHost(read_only=False, run=slow).create("o/r", "t", "b", [])
    except Stop as stop:
        assert "timed out" in str(stop)
    else:
        raise AssertionError("a timed out write went unnoticed")
    reader = GhHost(read_only=True, run=run)
    for write in (lambda: reader.create("o/r", "t", "b", []), lambda: reader.edit_body("o/r", 1, "b"),
                  lambda: reader.comment("o/r", 1, "b"), lambda: reader.close_not_planned("o/r", 1)):
        count = len(calls)
        try:
            write()
        except Stop:
            assert len(calls) == count
        else:
            raise AssertionError("a read-only host wrote")
    assert not any("DELETE" in " ".join(argv) or "delete" in argv for argv, _ in calls)
    source = Path(__file__).read_text(encoding="utf-8")
    assert not re.search(r'"(DELETE|delete)"[,\]]|deleteIssue', source.split("def gh_self_test")[0])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
