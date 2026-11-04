#!/usr/bin/env python3
"""Check that every metric a Grafana dashboard queries is emitted by the code.

    python3 scripts/check_dashboard.py assets/grafana-dashboard.json assets/template/src/dag/metrics.py
    python3 scripts/check_dashboard.py ../data-pathway/assets/grafana-dashboard.json \
        ../data-pathway/assets/template/src/pipeline/pipeline_metrics.py

Exit 0 when every metric name in the dashboard's expressions appears in the source,
1 with the missing names otherwise. Standard library only.
"""

from __future__ import annotations

import json
import re
import sys

NAME = re.compile(r"\b((?:stream_pipeline|dagster)_[a-z_]+)")
SUFFIXES = ("_bucket", "_sum", "_count")


def queried(dashboard: dict) -> set[str]:
    names: set[str] = set()
    for panel in dashboard.get("panels", []):
        for target in panel.get("targets", []):
            for name in NAME.findall(target.get("expr", "")):
                for suffix in SUFFIXES:
                    if name.endswith(suffix):
                        name = name[: -len(suffix)]
                names.add(name)
    variables = dashboard.get("templating", {}).get("list", [])
    for variable in variables:
        names.update(NAME.findall(variable.get("definition", "")))
    return names


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    with open(sys.argv[1], encoding="utf-8") as handle:
        dashboard = json.load(handle)
    with open(sys.argv[2], encoding="utf-8") as handle:
        source = handle.read()
    # dagster_run_duration_seconds is a histogram: the source names the base.
    missing = sorted(name for name in queried(dashboard) if name not in source)
    if missing:
        print("not emitted by the source: " + ", ".join(missing))
        return 1
    print(f"ok: {len(queried(dashboard))} metric(s) queried, all emitted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
