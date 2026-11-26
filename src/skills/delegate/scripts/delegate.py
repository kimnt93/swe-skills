#!/usr/bin/env python3
"""Start one Orca worker for a brief, on the harness, model and effort of a row of the team's agent table.

    delegate.py --brief brief.md [--row medium] [--worktree new-child] [--repo R] [--name N] [--from HANDLE]
                [--table FILE] [--dry-run]
    delegate.py --self-test

It runs `orca orchestration worker-start` and nothing else. There is no option to pick a harness, a model or an
effort: they come from the table (bot-orchestration/scripts/agent_table.py), and a missing table or row stops. The
row is --row or the brief's 'Row:' line; when the brief names both, or has a 'Run on:' line, they must agree with
the table. Exit 0 = started (or the dry run), 1 = stopped, 2 = usage.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile


def sibling(skill: str, script: str):
    """The module of a sibling skill's script, in the plugin layout and in a prefixed copy install."""
    own = Path(__file__).resolve().parents[1]
    path = own.parent / own.name.replace("delegate", skill) / "scripts" / f"{script}.py"
    spec = importlib.util.spec_from_file_location(script, path)
    if spec is None or not path.is_file():
        raise SystemExit(f"STOP: {path} is missing: install the {skill} skill beside this one")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TABLE = sibling("bot-orchestration", "agent_table")


def orca_command(env: dict[str, str] | None = None, which=shutil.which) -> str:
    """The Orca executable. A bare 'orca' is used only inside an Orca terminal: elsewhere on Linux that name is the
    GNOME screen reader. Nothing found stops: there is no other way to start a worker."""
    env = dict(os.environ) if env is None else env
    named = env.get("ORCA_CLI_COMMAND")
    if named:
        found = which(named)
        if found:
            return found
        raise TABLE.Stop(f"ORCA_CLI_COMMAND names {named!r}, which cannot be run")
    names = ["orca-dev"] if env.get("ORCA_DEV_REPO_ROOT") else ["orca-ide"]
    if env.get("TERM_PROGRAM") == "Orca" or env.get("ORCA_AGENT_PANE"):
        names.append("orca")
    for name in names:
        found = which(name)
        if found:
            return found
    raise TABLE.Stop(f"no Orca CLI ({', '.join(names)}): run this in Orca, or set ORCA_CLI_COMMAND")


def line_of(brief: str, key: str) -> str | None:
    found = [x[len(key) + 1:].strip() for x in brief.splitlines() if x.startswith(f"{key}:")]
    if len(found) > 1:
        raise TABLE.Stop(f"the brief has {len(found)} '{key}:' lines: keep one")
    return found[0] if found else None


def run_on(found: dict[str, str]) -> str:
    return f"harness {found['harness']}, model {found['model']}, reasoning effort {found['effort'] or 'none'}"


def pick(brief: str, row: str | None, table: str | None) -> dict[str, str]:
    """The table's row for this brief: --row or the brief's own Row line, and they may not disagree."""
    written = line_of(brief, "Row")
    if row and written and row != written:
        raise TABLE.Stop(f"--row is {row!r} but the brief says 'Row: {written}'")
    if not (row or written):
        raise TABLE.Stop("no row: give --row, or write the 'Row:' line in the brief")
    found = TABLE.row_of(row or written, table)
    stated = line_of(brief, "Run on")
    if stated is not None and stated.rstrip(".") != run_on(found):
        raise TABLE.Stop(f"the brief says 'Run on: {stated}' but the table's row {found['row']!r} is "
                         f"'{run_on(found)}': take the line from the table")
    return found


def command(orca: str, spec: str, found: dict[str, str], args: argparse.Namespace) -> list[str]:
    cmd = [orca, "orchestration", "worker-start", "--spec-file", spec, "--agent", found["harness"],
           "--model", found["model"]]
    if found["effort"]:
        cmd += ["--effort", found["effort"]]
    cmd += ["--worktree", args.worktree]
    for flag, value in (("--repo", args.repo), ("--name", args.name), ("--from", args.sender)):
        if value:
            cmd += [flag, value]
    return cmd + ["--json"]


def parser() -> argparse.ArgumentParser:
    out = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    out.add_argument("--brief", help="the brief file Orca gives the worker")
    out.add_argument("--row", help=" | ".join(TABLE.ROWS) + " (default: the brief's 'Row:' line)")
    out.add_argument("--table", help="the team's agent table (default: see agent_table.py)")
    out.add_argument("--worktree", default="new-child", help="current, new-child, new-top-level or a selector")
    out.add_argument("--repo", help="Orca repository selector, for a new worktree")
    out.add_argument("--name", help="name of a new worktree")
    out.add_argument("--from", dest="sender", help="the coordinator handle")
    out.add_argument("--dry-run", action="store_true", help="print the command and start nothing")
    out.add_argument("--self-test", action="store_true")
    return out


def run(argv: list[str], resolve=orca_command, call=subprocess.run) -> int:
    args = parser().parse_args(argv)
    if not args.brief:
        print("usage: delegate.py --brief FILE [--row ROW] (see --help)", file=sys.stderr)
        return 2
    try:
        brief = Path(args.brief)
        if not brief.is_file() or not brief.read_text(encoding="utf-8").strip():
            raise TABLE.Stop(f"no brief at {brief}: write the brief to a file first")
        found = pick(brief.read_text(encoding="utf-8"), args.row, args.table)
        cmd = command(resolve(), str(brief), found, args)
    except TABLE.Stop as stop:
        print(f"STOP: {stop}. Nothing was started.", file=sys.stderr)
        return 1
    if args.dry_run:
        print(f"Row: {found['row']}\nRun on: {run_on(found)}\n{shlex.join(cmd)}")
        return 0
    return call(cmd, check=False).returncode


def self_test() -> int:
    import contextlib
    import io
    on_path = {"orca-ide": "/bin/orca-ide", "orca": "/usr/bin/orca", "/shim/orca": "/shim/orca"}
    which = on_path.get
    assert orca_command({}, which) == "/bin/orca-ide"
    assert orca_command({"ORCA_CLI_COMMAND": "/shim/orca"}, which) == "/shim/orca"
    only_bare = {"orca": "/usr/bin/orca"}.get
    assert orca_command({"TERM_PROGRAM": "Orca"}, only_bare) == "/usr/bin/orca"
    for env in ({}, {"ORCA_CLI_COMMAND": "/missing"}, {"ORCA_DEV_REPO_ROOT": "/x"}):
        try:
            orca_command(env, only_bare)
        except TABLE.Stop:
            continue
        raise AssertionError(f"{env}: a bare orca outside Orca, or another executable, was used")

    started: list[list[str]] = []

    class Done:
        returncode = 0

    def call(cmd, check):
        started.append(cmd)
        return Done()

    def shim() -> str:
        return "/shim/orca"

    quiet = io.StringIO()
    with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(quiet), \
            contextlib.redirect_stderr(quiet):
        table = Path(folder, "table.md")
        table.write_text(
            "| Role or difficulty | Harness | Model | Reasoning effort |\n|---|---|---|---|\n"
            "| simple | harness-a | model-a | none |\n| medium | harness-a | model-a | high |\n"
            "| planner/architect | harness-b | model-b | max |\n", encoding="utf-8")
        brief = Path(folder, "brief.md")

        def go(text: str, *extra: str) -> int:
            brief.write_text(text, encoding="utf-8")
            return run(["--brief", str(brief), "--table", str(table), *extra], shim, call)

        line = "Run on: harness harness-a, model model-a, reasoning effort high"
        assert go(f"Row: medium\n{line}\nbuild it\n", "--repo", "id:r", "--name", "api-03") == 0
        assert started[-1] == ["/shim/orca", "orchestration", "worker-start", "--spec-file", str(brief),
                               "--agent", "harness-a", "--model", "model-a", "--effort", "high",
                               "--worktree", "new-child", "--repo", "id:r", "--name", "api-03", "--json"]
        assert go("build it\n", "--row", "simple", "--worktree", "current") == 0
        assert "--effort" not in started[-1] and started[-1][-2:] == ["current", "--json"]
        assert go("Row: planner/architect\nplan it\n") == 0 and "model-b" in started[-1]
        count = len(started)
        assert go("Row: medium\nbuild it\n", "--dry-run") == 0 and len(started) == count
        for text, extra in (("Row: hard\nbuild it\n", ()),  # the table has no hard row: no other row stands in
                            ("build it\n", ()), ("Row: medium\nbuild it\n", ("--row", "simple")),
                            ("Row: medium\nRow: simple\n", ()), ("Row: huge\n", ()), ("", ("--row", "medium")),
                            (f"Row: medium\n{line.replace('model-a', 'model-z')}\n", ())):
            assert go(text, *extra) == 1 and len(started) == count, (text, extra)
        table.unlink()
        assert go("Row: medium\nbuild it\n") == 1 and len(started) == count, "no table, no worker"
        assert run([], shim, call) == 2
        for flag in ("--model", "--agent", "--effort"):
            try:
                parser().parse_args([flag, "x"])
            except SystemExit:
                continue
            raise AssertionError(f"{flag} would set a value outside the table")
    print("self-test passed: Orca only; harness, model and effort come only from the agent table")
    return 0


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else run(sys.argv[1:]))
