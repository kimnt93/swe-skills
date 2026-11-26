#!/usr/bin/env python3
"""Check a message between bots and agents against its template (assets/<kind>.template.md).

    message_lint.py <delegate|agent-brief|agent-report|bot-report|follow-up> --body-file msg.md
    message_lint.py --self-test

The template is the rule. Each line 'Key: <...>' must appear with the placeholder replaced; a line without a
placeholder is a fixed rule and must appear exactly, with nothing added to it; a first line '<A | B>: ...' means the message starts with
one of those words. An angle-bracket list such as '<simple | medium | hard>' limits the value to those words.
AGENT_TEMPLATES=<dir> overrides the templates.
Exit 0 = clean, 1 = findings, 2 = usage. Standard library only.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[1] / "assets"
KINDS = ("delegate", "agent-brief", "agent-report", "bot-report", "follow-up")
CHOICES_RE = re.compile(r"^<([\w /]+(?: \| [\w /]+)+)>")
PLACEHOLDER_RE = re.compile(r"<[^<>\n]+>")
# a template placeholder left in a message; an example may still write <owner>/<repo> in a link
UNFILLED_RE = re.compile(r"<[a-z][^<>\n]*[ |][^<>\n]*>|<url>|<ID[^<>]*>")
ADDRESS_RE = re.compile(r"^bot:.+, chat [\w:-]+$")
ADDRESS_KEYS = {"delegate": "Return to", "follow-up": "Return to", "bot-report": "From"}
SECRET_RE = re.compile(
    r"(?i)(ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|(?:token|password|secret)\s*[:=]\s*\S{8,})"
)


def template(kind: str) -> list[str]:
    override = os.environ.get("AGENT_TEMPLATES", "").strip()
    own = Path(override) / f"{kind}.template.md" if override else None
    path = own if own and own.is_file() else ASSETS / f"{kind}.template.md"
    return [x for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def lint(kind: str, body: str) -> list[str]:
    wanted = template(kind)
    lines = [x.rstrip() for x in body.splitlines() if x.strip()]
    problems = []
    if SECRET_RE.search(body):
        problems.append("it looks like it holds a secret: never send one; say 'read it from the environment'")
    first = CHOICES_RE.match(wanted[0])
    if first:
        words = [x.strip() for x in first.group(1).split("|")]
        match = re.match(rf"^({'|'.join(map(re.escape, words))}): \S", lines[0] if lines else "")
        if not match or UNFILLED_RE.search(lines[0]):
            problems.append(f"the first line is '<{' | '.join(words)}>: ...' with every placeholder replaced")
        wanted = wanted[1:]
    for rule in wanted:
        if not PLACEHOLDER_RE.search(rule):
            if rule not in lines:
                problems.append(f"missing the rule line, exactly as the template writes it: '{rule}'")
            continue
        key, _, shape = rule.partition(": ")
        values = [x[len(key) + 2:].strip() for x in lines if x.startswith(f"{key}: ")]
        if len(values) != 1 or not values[0]:
            problems.append(f"needs exactly one '{key}: ...' line with a value")
            continue
        value = values[0]
        choices = CHOICES_RE.match(shape)
        if choices:
            allowed = [x.strip() for x in choices.group(1).split("|")]
            if value.split(" (")[0] not in allowed:
                problems.append(f"'{key}' is one of {', '.join(allowed)} (got {value!r})")
        elif UNFILLED_RE.search(value):
            problems.append(f"'{key}' still holds a placeholder: {value!r}")
        if key == ADDRESS_KEYS.get(kind) and not ADDRESS_RE.match(value):
            problems.append(f"'{key}' is an address: 'bot:<name>, chat <id>'")
    return problems


def self_test() -> int:
    os.environ.pop("AGENT_TEMPLATES", None)
    for kind in KINDS:
        raw = (ASSETS / f"{kind}.template.md").read_text(encoding="utf-8")
        assert lint(kind, raw), f"{kind}: an unfilled template must fail"
    good = {path.stem: path.read_text(encoding="utf-8") for path in (ASSETS / "example").glob("*.md")}
    for kind in KINDS:
        assert kind in good and lint(kind, good[kind]) == [], (kind, lint(kind, good.get(kind, "")))
    brief = good["agent-brief"]
    without = "\n".join(x for x in brief.splitlines() if not x.startswith("Message no other"))
    assert "rule line" in lint("agent-brief", without)[0], "an agent must be told to message nobody else"
    assert any("Row" in x for x in lint("agent-brief", re.sub(r"(?m)^Row: .*$", "Row: huge", brief)))
    assert lint("agent-brief", re.sub(r"(?m)^Row: .*$", "Row: planner/architect", brief)) == []
    assert any("Run on" in x for x in lint("agent-brief", re.sub(r"(?m)^Run on: .*\n", "", brief))), "a brief names its agent"
    unsourced = "\n".join(x for x in good["delegate"].splitlines() if not x.startswith("Agents: "))
    assert any("agent table" in x for x in lint("delegate", unsourced)), "a handoff takes its agents from the table"
    assert any("Evidence command" in x for x in lint("agent-brief", re.sub(r"(?m)^Evidence command: .*$", "", brief)))
    nowhere = re.sub(r"(?m)^Return to: .*$", "Return to: me", good["delegate"])
    assert any("address" in x for x in lint("delegate", nowhere)), "a handoff without a return address is lost"
    for old, new in (("start no helpers", "start no helpers unless you want to; message agent B too"),
                     ("Never merge", "Never merge unless checks are green"),
                     ("once, with worker_done", "once, with worker_done, and also mail the CEO bot")):
        assert old in brief and "rule line" in lint("agent-brief", brief.replace(old, new))[0], new
    assert "send an orchestration status to the return address" in good["delegate"], "the receiver is told to report"
    assert any("Deliver" in x for x in lint("agent-brief", re.sub(r"(?m)^Deliver: .*$", "Deliver: whatever", brief)))
    assert "first line" in lint("bot-report", good["bot-report"].replace("PR READY", "All good", 1))[0]
    assert "secret" in lint("agent-report", good["agent-report"] + "token = abcdefgh12345678\n")[0]
    print("self-test passed: five messages, their return addresses and agent limits that cannot be weakened")
    return 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv[:1]:
        return self_test()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("kind", choices=KINDS)
    parser.add_argument("--body-file", required=True)
    args = parser.parse_args(argv)
    problems = lint(args.kind, Path(args.body_file).read_text(encoding="utf-8"))
    for problem in problems:
        print("PROBLEM", problem)
    print(f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
