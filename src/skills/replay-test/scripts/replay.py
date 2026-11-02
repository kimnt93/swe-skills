#!/usr/bin/env python3
"""Replay a recorded event stream through the real code and compare the end state to a golden file.

    replay.py check --events events.jsonl --cmd "go run ./cmd/replay" --golden golden.json
    replay.py check ... --mutate duplicate        every event delivered twice: the state must not change
    replay.py check ... --mutate redeliver:3      after each event, redeliver the 3 before it (Kafka after a crash)
    replay.py record --events events.jsonl --cmd "..." --golden golden.json [--force]
    replay.py --self-test

The command reads JSON Lines on stdin (one event per line, in order) and prints one JSON object on
stdout: the end state (positions, balances, P&L, order states, ...). Numbers are compared exactly as
decimals, never as floats. Exit 0 = the state equals the golden file, 1 = it differs (a diff is
printed), 2 = usage or a failing command.
Standard library only.
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import tempfile
from decimal import Decimal
from pathlib import Path


def load_json(text: str):
    return json.loads(text, parse_float=Decimal, parse_int=Decimal)


def read_events(path: Path) -> list[str]:
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    for number, line in enumerate(lines, 1):
        try:
            json.loads(line)
        except ValueError as exc:
            sys.exit(f"replay: {path}:{number} is not JSON ({exc})")
    return lines


def mutate(events: list[str], how: str) -> list[str]:
    if how == "none":
        return events
    if how == "duplicate":
        return [event for event in events for _ in range(2)]
    if how.startswith("redeliver:"):
        back = int(how.split(":", 1)[1])
        out: list[str] = []
        for index, event in enumerate(events):
            out.append(event)
            out.extend(events[max(0, index - back + 1):index + 1])
        return out
    sys.exit(f"replay: unknown --mutate {how!r} (none, duplicate, redeliver:N)")


def run(cmd: str, events: list[str]):
    result = subprocess.run(shlex.split(cmd), input="\n".join(events) + "\n", capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout[-2000:] + result.stderr[-2000:], file=sys.stderr)
        sys.exit(f"replay: command failed with exit {result.returncode}: {cmd}")
    try:
        return load_json(result.stdout)
    except ValueError:
        sys.exit(f"replay: command output is not one JSON object:\n{result.stdout[-2000:]}")


def diff(expected, actual, path: str = "$") -> list[str]:
    if isinstance(expected, dict) and isinstance(actual, dict):
        out = []
        for key in sorted(set(expected) | set(actual)):
            if key not in actual:
                out.append(f"{path}.{key}: missing (expected {expected[key]})")
            elif key not in expected:
                out.append(f"{path}.{key}: unexpected {actual[key]}")
            else:
                out.extend(diff(expected[key], actual[key], f"{path}.{key}"))
        return out
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            return [f"{path}: {len(actual)} items, expected {len(expected)}"]
        return [line for i, (e, a) in enumerate(zip(expected, actual)) for line in diff(e, a, f"{path}[{i}]")]
    if expected != actual:
        return [f"{path}: {actual} (expected {expected})"]
    return []


def dump(value) -> str:
    return json.dumps(value, indent=2, sort_keys=True, default=str) + "\n"


def check(args: argparse.Namespace) -> int:
    events = mutate(read_events(Path(args.events)), args.mutate)
    golden = load_json(Path(args.golden).read_text(encoding="utf-8"))
    problems = diff(golden, run(args.cmd, events))
    label = f"{args.events} ({args.mutate}, {len(events)} deliveries)"
    if problems:
        print(f"FAIL {label}: {len(problems)} difference(s)")
        for line in problems[:50]:
            print("  " + line)
        return 1
    print(f"PASS {label}: end state equals {args.golden}")
    return 0


def record(args: argparse.Namespace) -> int:
    golden = Path(args.golden)
    if golden.exists() and not args.force:
        sys.exit(f"replay: {golden} exists; a golden file changes only on purpose (--force, and say why in the commit)")
    golden.write_text(dump(run(args.cmd, read_events(Path(args.events)))), encoding="utf-8")
    print(f"wrote {golden}: check it by hand before you commit it")
    return 0


FAKE_ENGINE = r'''
import json, sys
from decimal import Decimal
idempotent = sys.argv[1] == "idempotent"
seen, positions, cash = set(), {}, Decimal("0")
for line in sys.stdin:
    if not line.strip():
        continue
    e = json.loads(line, parse_float=Decimal)
    if e["type"] != "fill" or (idempotent and e["fill_id"] in seen):
        continue
    seen.add(e["fill_id"])
    qty = Decimal(str(e["qty"])) * (1 if e["side"] == "buy" else -1)
    positions[e["symbol"]] = positions.get(e["symbol"], Decimal("0")) + qty
    cash -= qty * Decimal(str(e["price"]))
print(json.dumps({"positions": {k: str(v) for k, v in sorted(positions.items())}, "cash": str(cash)}))
'''


def self_test() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        engine = root / "engine.py"
        engine.write_text(FAKE_ENGINE, encoding="utf-8")
        events = root / "events.jsonl"
        events.write_text("\n".join(json.dumps(e) for e in [
            {"type": "order", "order_id": "o1"},
            {"type": "fill", "fill_id": "f1", "symbol": "VN30F", "side": "buy", "qty": 2, "price": "1250.5"},
            {"type": "fill", "fill_id": "f2", "symbol": "VN30F", "side": "sell", "qty": 1, "price": "1251.0"},
            {"type": "fill", "fill_id": "f3", "symbol": "FPT", "side": "buy", "qty": 100, "price": "0.1"},
        ]) + "\n", encoding="utf-8")
        golden = root / "golden.json"
        good = f"{sys.executable} {engine} idempotent"
        bad = f"{sys.executable} {engine} naive"
        base = ["--events", str(events), "--golden", str(golden)]

        def call(*argv: str) -> int:
            result = subprocess.run([sys.executable, __file__, *argv], capture_output=True, text=True)
            return result.returncode

        assert call("record", "--cmd", good, *base) == 0, "record"
        assert call("record", "--cmd", good, *base) != 0, "record must refuse to overwrite"
        assert '"cash": "-1260.0"' in golden.read_text(), golden.read_text()
        assert call("check", "--cmd", good, *base) == 0, "clean replay"
        assert call("check", "--cmd", good, *base, "--mutate", "duplicate") == 0, "idempotent under duplicates"
        assert call("check", "--cmd", good, *base, "--mutate", "redeliver:2") == 0, "idempotent under redelivery"
        assert call("check", "--cmd", bad, *base) == 0, "naive engine is right without duplicates"
        assert call("check", "--cmd", bad, *base, "--mutate", "duplicate") == 1, "duplicates must expose the naive engine"
        assert call("check", "--cmd", bad, *base, "--mutate", "redeliver:2") == 1, "redelivery must expose the naive engine"
        assert diff({"a": Decimal("1.10")}, {"a": Decimal("1.1")}) == [], "decimal equality"
        assert diff({"a": Decimal("1.1")}, {"a": Decimal("1.2")}), "decimal difference"
    print("self-test passed: record guard, exact decimals, duplicate and redelivery catch a non-idempotent engine")
    return 0


def main() -> int:
    if "--self-test" in sys.argv[1:]:
        return self_test()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="action", required=True)
    for name in ("check", "record"):
        p = sub.add_parser(name)
        p.add_argument("--events", required=True)
        p.add_argument("--cmd", required=True)
        p.add_argument("--golden", required=True)
        if name == "check":
            p.add_argument("--mutate", default="none")
        else:
            p.add_argument("--force", action="store_true")
    args = parser.parse_args()
    return check(args) if args.action == "check" else record(args)


if __name__ == "__main__":
    sys.exit(main())
