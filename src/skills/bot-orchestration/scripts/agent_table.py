#!/usr/bin/env python3
"""The team's one agent table: which harness, model and reasoning effort a row runs on.

    agent_table.py path                              (where the team's copy is looked for)
    agent_table.py check [--table FILE]              (every row is there and filled)
    agent_table.py row <row> [--table FILE]          (simple | medium | hard | planner/architect)
    agent_table.py init [FILE]                       (copy the empty template; never overwrites)
    agent_table.py --self-test

The table is the only place that sets harness, model and reasoning effort. There is **no default**: a table, a row
or a cell that is missing or unfilled stops with 'STOP ... ask the owner'. The team's copy is, first match:
--table, $AGENT_TABLE, the 'agent_table' key of the user's config.json ($SWE_CONFIG, else
~/.config/@PLUGIN@/config.json), then ~/.config/@PLUGIN@/agent-table.md. A named file that does not exist stops the
search. Nothing is read from the working directory, so a repository cannot choose the agents that work on it.
Exit 0 = ok, 1 = stop and ask, 2 = usage. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROWS = ("simple", "medium", "hard", "planner/architect")
HEADER = ["role or difficulty", "harness", "model", "reasoning effort"]
TEMPLATE = Path(__file__).resolve().parents[1] / "assets" / "agent-table.template.md"
# a value goes to a command line: it starts with a letter, digit or '@' (a harness's model role), never with '-'
VALUE_RE = {"harness": re.compile(r"[a-z0-9][a-z0-9._-]*"),
            "model": re.compile(r"[A-Za-z0-9@][A-Za-z0-9@._:/\[\]-]*"),
            "effort": re.compile(r"[a-z]+")}


class Stop(Exception):
    """The table cannot answer: the run stops and the owner is asked."""


def plugin_name() -> str:
    built = "@PLUGIN@"  # the build writes the plugin's name here; in the source tree the placeholder is still there
    return os.environ.get("PLUGIN_NAME", "swe") if built.startswith("@") else built


def config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / plugin_name()


def configured_table() -> str:
    """The 'agent_table' key of the user's own config.json, or ''. A config that cannot be read stops."""
    named = os.environ.get("SWE_CONFIG", "").strip()
    path = Path(named).expanduser() if named else config_dir() / "config.json"
    if not path.is_file():
        return ""
    try:
        value = json.loads(path.read_text(encoding="utf-8")).get("agent_table", "")
    except (ValueError, AttributeError, OSError) as error:
        raise Stop(f"{path} cannot be read ({error}), so the agent table it may name is unknown")
    if not isinstance(value, str):
        raise Stop(f"{path}: 'agent_table' is not a path")
    return value.strip()


def table_path(explicit: str | None = None) -> Path:
    for source in (explicit, os.environ.get("AGENT_TABLE", "").strip()):
        if source:
            return Path(source).expanduser()
    configured = configured_table()
    return Path(configured).expanduser() if configured else config_dir() / "agent-table.md"


def cells(line: str) -> list[str]:
    return [x.strip().strip("`").strip() for x in line.strip().strip("|").split("|")]


def parse(text: str) -> dict[str, list[str]]:
    """row name -> [harness, model, effort] as written. Exactly one table with the four columns."""
    tables: list[list[str]] = []
    inside, fenced = False, False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced, inside = not fenced, False
            continue
        if fenced or not line.lstrip().startswith("|"):
            inside = False
            continue
        if [x.lower() for x in cells(line)] == HEADER:
            tables.append([])
            inside = True
        elif inside and not re.fullmatch(r"[\s|:-]+", line):
            tables[-1].append(line)
    if len(tables) != 1:
        raise Stop(f"it needs exactly one table with the columns {' | '.join(HEADER)} (found {len(tables)})")
    rows: dict[str, list[str]] = {}
    for line in tables[0]:
        found = cells(line)
        name = found[0].lower()
        if len(found) != 4:
            raise Stop(f"the row '{name}' has {len(found)} cells, not 4")
        if name not in ROWS:
            raise Stop(f"'{found[0]}' is not a row of the table: the rows are {', '.join(ROWS)}")
        if name in rows:
            raise Stop(f"the row '{name}' is there twice")
        rows[name] = found[1:]
    return rows


def pick(rows: dict[str, list[str]], row: str) -> dict[str, str]:
    """{'row', 'harness', 'model', 'effort'} of one filled row; effort is '' only when the row says 'none'."""
    if row not in ROWS:
        raise Stop(f"'{row}' is not a row: the rows are {', '.join(ROWS)}")
    if row not in rows:
        raise Stop(f"the row '{row}' is missing")
    found = dict(zip(("harness", "model", "effort"), rows[row]))
    for key, value in found.items():
        if not value or "<" in value:
            raise Stop(f"the row '{row}' has no {key}")
        if not VALUE_RE[key].fullmatch(value) or (key != "effort" and value.lower() == "none"):
            raise Stop(f"the row '{row}' has an unusable {key}: {value!r}")
    return {"row": row, **found, "effort": "" if found["effort"] == "none" else found["effort"]}


def load(explicit: str | None = None) -> tuple[Path, dict[str, list[str]]]:
    path = table_path(explicit)
    if not path.is_file():
        raise Stop(f"there is no agent table at {path}: the team copies the template there and fills it "
                   "(agent_table.py init)")
    try:
        return path, parse(path.read_text(encoding="utf-8"))
    except Stop as stop:
        raise Stop(f"{path}: {stop}")


def row_of(row: str, explicit: str | None = None) -> dict[str, str]:
    path, rows = load(explicit)
    try:
        return pick(rows, row)
    except Stop as stop:
        raise Stop(f"{path}: {stop}")


def init(target: Path) -> None:
    if target.exists():
        raise Stop(f"{target} exists; edit it, nothing was overwritten")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")


def self_test() -> int:
    def stops(call, needle: str) -> None:
        try:
            call()
        except Stop as stop:
            assert needle in str(stop), (needle, str(stop))
        else:
            raise AssertionError(f"no stop for {needle!r}")

    empty = TEMPLATE.read_text(encoding="utf-8")
    assert tuple(parse(empty)) == ROWS, "the template has exactly the four rows"
    for row in ROWS:
        stops(lambda: pick(parse(empty), row), "has no harness")
    filled = empty.replace("<harness>", "harness-a").replace("<model>", "model-a").replace("<effort>", "high")
    rows = parse(filled)
    assert pick(rows, "hard") == {"row": "hard", "harness": "harness-a", "model": "model-a", "effort": "high"}
    assert len({tuple(rows[x]) for x in ROWS}) == 1, "every row may name the same agent"
    strong = parse(filled.replace("| planner/architect | harness-a | model-a |", "| planner/architect | harness-a | model-b |"))
    assert pick(strong, "planner/architect")["model"] == "model-b" and pick(strong, "hard")["model"] == "model-a"
    no_effort = filled.replace("| simple | harness-a | model-a | high |", "| simple | `harness-a` | vendor/model-a:1 | none |")
    assert pick(parse(no_effort), "simple") == {"row": "simple", "harness": "harness-a", "model": "vendor/model-a:1", "effort": ""}
    without = "\n".join(x for x in filled.splitlines() if not x.startswith("| hard "))
    stops(lambda: pick(parse(without), "hard"), "'hard' is missing")
    assert pick(parse(without), "medium")["model"] == "model-a", "the other rows still answer"
    stops(lambda: pick(rows, "strong"), "is not a row")
    for old, new, needle in (
            ("| simple | harness-a | model-a | high |", "| simple | harness-a |  | high |", "has no model"),
            ("| simple | harness-a | model-a | high |", "| simple | harness-a | none | high |", "unusable model"),
            ("| simple | harness-a | model-a | high |", "| simple | none | model-a | high |", "unusable harness"),
            ("| simple | harness-a | model-a | high |", "| simple | harness-a | --yolo | high |", "unusable model"),
            ("| simple | harness-a | model-a | high |", "| simple | harness-a | model a | high |", "unusable model"),
            ("| simple | harness-a | model-a | high |", "| simple | harness-a | model-a | |", "has no effort")):
        stops(lambda: pick(parse(filled.replace(old, new)), "simple"), needle)
    stops(lambda: parse(filled.replace("| medium |", "| simple |")), "twice")
    stops(lambda: parse(filled.replace("| medium |", "| midium |")), "is not a row")
    stops(lambda: parse(filled.replace("| medium | harness-a |", "| medium |")), "cells")
    stops(lambda: parse("no table here"), "exactly one table")
    stops(lambda: parse(filled + "\n" + filled), "exactly one table")
    stops(lambda: parse("```\n" + filled + "\n```"), "exactly one table")
    saved = {k: os.environ.get(k) for k in ("AGENT_TABLE", "SWE_CONFIG", "XDG_CONFIG_HOME")}
    previous = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as folder:
            for key in saved:
                os.environ.pop(key, None)
            os.environ["XDG_CONFIG_HOME"] = folder
            os.chdir(folder)
            Path(folder, "agent-table.md").write_text(filled, encoding="utf-8")
            Path(folder, "config.json").write_text('{"agent_table": "agent-table.md"}', encoding="utf-8")
            assert table_path() == config_dir() / "agent-table.md", "nothing is read from the working directory"
            stops(lambda: row_of("simple"), "there is no agent table")
            mine = config_dir() / "agent-table.md"
            init(mine)
            stops(lambda: init(mine), "exists")
            stops(lambda: row_of("simple"), "has no harness")
            mine.write_text(filled, encoding="utf-8")
            assert row_of("simple")["harness"] == "harness-a"
            other = Path(folder, "other.md")
            other.write_text(filled.replace("harness-a", "harness-b"), encoding="utf-8")
            (config_dir() / "config.json").write_text(json.dumps({"agent_table": str(other)}), encoding="utf-8")
            assert row_of("simple")["harness"] == "harness-b", "config.json names the copy"
            os.environ["AGENT_TABLE"] = str(mine)
            assert row_of("simple")["harness"] == "harness-a", "the environment wins over config.json"
            assert row_of("simple", str(other))["harness"] == "harness-b", "--table wins over both"
            os.environ["AGENT_TABLE"] = str(Path(folder, "gone.md"))
            stops(lambda: row_of("simple"), "there is no agent table")
            os.environ.pop("AGENT_TABLE")
            (config_dir() / "config.json").write_text("{broken", encoding="utf-8")
            stops(lambda: row_of("simple"), "cannot be read")
    finally:
        os.chdir(previous)
        for key, value in saved.items():
            os.environ.pop(key, None) if value is None else os.environ.update({key: value})
    print("agent_table.py self-test passed: four rows, no default, stop on anything missing")
    return 0


def main(argv: list[str]) -> int:
    if argv[:1] == ["--self-test"]:
        return self_test()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("path").add_argument("--table")
    sub.add_parser("check").add_argument("--table")
    one = sub.add_parser("row")
    one.add_argument("row")
    one.add_argument("--table")
    sub.add_parser("init").add_argument("target", nargs="?")
    args = parser.parse_args(argv)
    try:
        if args.command == "path":
            print(table_path(args.table))
        elif args.command == "init":
            target = table_path(args.target)
            init(target)
            print(f"copied the empty template to {target}: fill every cell")
        elif args.command == "row":
            found = row_of(args.row, args.table)
            print(f"Row: {found['row']}")
            print(f"Run on: harness {found['harness']}, model {found['model']}, reasoning effort {found['effort'] or 'none'}")
        else:
            path, rows = load(args.table)
            problems = []
            for row in ROWS:
                try:
                    pick(rows, row)
                except Stop as stop:
                    problems.append(str(stop))
            if problems:
                raise Stop(f"{path}: " + "; ".join(problems))
            print(f"{path}: all {len(ROWS)} rows are filled")
    except Stop as stop:
        print(f"STOP {stop}. Ask the owner; never use a default or another row.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
