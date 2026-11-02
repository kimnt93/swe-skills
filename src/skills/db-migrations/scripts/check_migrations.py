#!/usr/bin/env python3
"""Lint a directory of goose SQL migrations (schemas/NNNN_name.sql).

    python3 scripts/check_migrations.py schemas        # exit 0 = clean
    python3 scripts/check_migrations.py --self-test    # prove the checks work

Checks, per file and across the directory:
  * name is NNNN_snake_case.sql; versions are unique and contiguous from 0001
  * `-- +goose Up` comes first and `-- +goose Down` exists and is not empty
    (an intentionally irreversible step says so with `-- irreversible: reason`)
  * CREATE INDEX on a table that already exists must be CONCURRENTLY, inside
    a file marked `-- +goose NO TRANSACTION`
  * ADD COLUMN ... NOT NULL needs a DEFAULT (existing rows would break)
  * DROP TABLE / DROP COLUMN in Up needs `-- destructive: reason`
  * layout: at most 100 columns, one statement per line, no tabs
Standard library only.
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

NAME_RE = re.compile(r"^(\d{4})_[a-z0-9]+(?:_[a-z0-9]+)*\.sql$")
MAX_COLUMNS = 100


def split_sections(text: str) -> tuple[str, str] | None:
    up_at = text.find("-- +goose Up")
    down_at = text.find("-- +goose Down")
    if up_at < 0 or down_at < 0 or down_at < up_at:
        return None
    return text[up_at:down_at], text[down_at:]


def statements(section: str) -> list[str]:
    body = "\n".join(
        line
        for line in section.splitlines()
        if not line.lstrip().startswith("--")
    )
    return [s.strip() for s in body.split(";") if s.strip()]


def check_file(path: Path) -> list[str]:
    problems: list[str] = []
    text = path.read_text(encoding="utf-8")

    sections = split_sections(text)
    if sections is None:
        return [f"{path.name}: needs `-- +goose Up` and then `-- +goose Down`"]
    up, down = sections

    if not statements(down) and "-- irreversible:" not in text:
        problems.append(
            f"{path.name}: the Down section is empty; write it or add "
            "`-- irreversible: reason`"
        )

    no_transaction = "-- +goose NO TRANSACTION" in text
    created_here = {
        m.group(1).lower()
        for m in re.finditer(
            r"create\s+table\s+(?:if\s+not\s+exists\s+)?([a-z_][a-z0-9_.]*)",
            up,
            re.I,
        )
    }

    for statement in statements(up):
        flat = " ".join(statement.split())

        index = re.match(
            r"create\s+(?:unique\s+)?index\s+(concurrently\s+)?"
            r"(?:if\s+not\s+exists\s+)?\S+\s+on\s+([a-z_][a-z0-9_.]*)",
            flat,
            re.I,
        )
        if index:
            table = index.group(2).lower()
            if table not in created_here and not index.group(1):
                problems.append(
                    f"{path.name}: CREATE INDEX on existing table {table} "
                    "must be CONCURRENTLY"
                )
            if index.group(1) and not no_transaction:
                problems.append(
                    f"{path.name}: CREATE INDEX CONCURRENTLY needs "
                    "`-- +goose NO TRANSACTION` at the top of the file"
                )

        add_column = re.search(
            r"add\s+column\s+(?:if\s+not\s+exists\s+)?\S+\s+[^,]*", flat, re.I
        )
        if add_column:
            clause = add_column.group(0).lower()
            if "not null" in clause and "default" not in clause:
                problems.append(
                    f"{path.name}: ADD COLUMN ... NOT NULL needs a DEFAULT "
                    "(or add it nullable, backfill, then tighten)"
                )

        drops = re.search(r"\bdrop\s+(table|column)\b", flat, re.I)
        if drops and "-- destructive:" not in text:
            problems.append(
                f"{path.name}: DROP TABLE/COLUMN in Up needs "
                "`-- destructive: reason` (expand and contract first)"
            )

    for number, line in enumerate(text.splitlines(), start=1):
        if len(line.expandtabs(4)) > MAX_COLUMNS:
            problems.append(
                f"{path.name}:{number}: longer than {MAX_COLUMNS} columns"
            )
        if "\t" in line:
            problems.append(
                f"{path.name}:{number}: tab; indent SQL with 4 spaces"
            )
        code = line.split("--", 1)[0]
        if re.search(r";\s*\S", code):
            problems.append(
                f"{path.name}:{number}: more than one statement on a line"
            )

    return problems


def check_directory(directory: Path) -> list[str]:
    problems: list[str] = []
    files = sorted(directory.glob("*.sql"))
    if not files:
        return [f"{directory}: no .sql migrations found"]

    versions: list[int] = []
    for path in files:
        match = NAME_RE.match(path.name)
        if not match:
            problems.append(f"{path.name}: name must be NNNN_snake_case.sql")
            continue
        versions.append(int(match.group(1)))
        problems.extend(check_file(path))

    if len(versions) != len(set(versions)):
        problems.append(f"{directory}: duplicate version numbers")
    elif versions and versions != list(range(1, len(versions) + 1)):
        problems.append(f"{directory}: versions must be contiguous from 0001")
    return problems


def self_test() -> int:
    good = """-- +goose Up
CREATE TABLE things (
    id uuid PRIMARY KEY,
    name text NOT NULL DEFAULT ''
);
CREATE INDEX things_name_idx ON things (name);

-- +goose Down
DROP TABLE things;
"""
    bad_cases = {
        "0001_bad_index.sql": (
            "-- +goose Up\nCREATE INDEX x_idx ON existing (a);\n\n"
            "-- +goose Down\nDROP INDEX x_idx;\n",
            "must be CONCURRENTLY",
        ),
        "0001_bad_concurrently.sql": (
            "-- +goose Up\n"
            "CREATE INDEX CONCURRENTLY x_idx ON existing (a);\n\n"
            "-- +goose Down\nDROP INDEX x_idx;\n",
            "NO TRANSACTION",
        ),
        "0001_bad_not_null.sql": (
            "-- +goose Up\nALTER TABLE t ADD COLUMN c text NOT NULL;\n\n"
            "-- +goose Down\nALTER TABLE t DROP COLUMN c;\n",
            "needs a DEFAULT",
        ),
        "0001_bad_drop.sql": (
            "-- +goose Up\nDROP TABLE t;\n\n-- +goose Down\nSELECT 1;\n",
            "destructive",
        ),
        "0001_bad_down.sql": (
            "-- +goose Up\nCREATE TABLE t (id int);\n\n-- +goose Down\n",
            "Down section is empty",
        ),
        "0001_bad_layout.sql": (
            "-- +goose Up\n"
            "CREATE TABLE t (id int); CREATE TABLE u (id int);\n\n"
            "-- +goose Down\nDROP TABLE t;\n",
            "more than one statement",
        ),
        "bad name.sql": (good, "name must be"),
    }
    failures = 0
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        (root / "ok").mkdir()
        (root / "ok" / "0001_things.sql").write_text(good)
        if check_directory(root / "ok"):
            print("FAIL: a clean migration was rejected")
            failures += 1
        for name, (content, expected) in bad_cases.items():
            case = root / name.replace(".sql", "")
            case.mkdir()
            (case / name).write_text(content)
            found = " | ".join(check_directory(case))
            if expected not in found:
                print(f"FAIL: {name} expected {expected!r}, got {found!r}")
                failures += 1
        gap = root / "gap"
        gap.mkdir()
        (gap / "0001_a.sql").write_text(good)
        (gap / "0003_b.sql").write_text(good)
        if "contiguous" not in " ".join(check_directory(gap)):
            print("FAIL: a version gap was accepted")
            failures += 1
    print("self-test:", "FAILED" if failures else "ok")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    if argv == ["--self-test"]:
        return self_test()
    if len(argv) != 1:
        print(__doc__)
        return 2
    problems = check_directory(Path(argv[0]))
    for problem in problems:
        print("ERROR", problem)
    print(f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
