---
name: data-dagster
description: Build and run batch and scheduled data pipelines as Dagster assets - daily partitioned assets, asset checks, jobs, schedules, resources, backfills - from a tested project template (polars, PostgreSQL source, Docker, compose) with dagster_* OTel metrics exported by a sensor and a Grafana dashboard for runs, durations, materializations, checks and freshness. Use when starting, changing or reviewing a Dagster project or DAG, scheduling or backfilling a data job, adding data-quality checks, or when asked for Dagster, assets, orchestration or pipeline lineage in Python.
compatibility: Python 3.11+, dagster 1.10 to 1.x (below 2.0), polars, psycopg 3. Template tests use Dagster's in-process execution and an in-memory OTel reader; no database or Docker needed. Tested with dagster 1.13, polars 1.x, opentelemetry-sdk 1.3x. The compose stack and Dockerfile were not run by the authors.
metadata:
  group: data
  summary: "Dagster DAGs: assets, checks, schedules, template, dagster_* OTel metrics, dashboard"
  version: "1.0"
---

# Dagster pipelines

Dagster models a pipeline as **assets** (the tables and files you want to exist) with dependencies, partitions, checks and
schedules. In this stack it is the tool for **batch, scheduled and backfilled data work**. Continuous streaming is Pathway
([data-pathway](../data-pathway/SKILL.md)); services are Go (`go-code`); ML training code is `py-code`, orchestrated here.

## When to use it

| The need | Use |
|---|---|
| Daily/hourly job that builds tables or files, with lineage, retries, backfills | **Dagster** (this skill) |
| Data-quality gates that must block downstream work | **Dagster** asset checks (`blocking=True`) |
| Continuous Kafka-to-Kafka transforms and live windows | `data-pathway` |
| A one-off script | a script; do not add Dagster for one run |
| A cron that calls one HTTP endpoint | the platform's scheduler, not Dagster |

## How to work

1. **Name the assets**, not the tasks: what exists after the run, what it depends on, its partitioning (daily here) and
   its freshness expectation. Write them down before code.
2. **Copy the template** `assets/template/` into the repo (`pyproject.toml`, `src/dag/`, `tests/`, `Dockerfile`,
   `docker-compose.yaml`, `dagster.yaml`, `workspace.yaml`, `Makefile`, `.env.example`). Rename the package and the assets.
3. **Assets are pure functions of their inputs and resources.** I/O goes through a `ConfigurableResource`
   (`resources.py`), never a client created inside the asset. Read [assets](references/assets.md).
4. **Partition by the data's natural unit** (day). A failed day re-runs alone; a backfill is a partition range.
5. **Add checks** next to the asset (`@asset_check`); make the ones that guard downstream work `blocking=True`.
6. **Schedule** with `build_schedule_from_partitioned_job` and a delay after the day ends; use a sensor for event-driven runs.
7. **Metrics**: the template's `metrics_sensor` exports `dagster_*` over OTLP. Read [metrics](references/metrics.md).
   Import `assets/grafana-dashboard.json` (uid `dagster-orchestration`).
8. **Test** with `dagster.materialize([...], resources={...}, partition_key=...)` and a fake resource; test the sensor with
   `build_sensor_context`. Read [testing](references/testing.md).
9. **Deploy** the webserver and the daemon from one image, with PostgreSQL storage and a queued run coordinator.
   Read [deploy](references/deploy.md) and the `deployment-setup` skill.
10. **Verify**: `make verify` (ruff + pytest), `dagster definitions validate -m dag.definitions`, and
    `python3 scripts/check_dashboard.py assets/grafana-dashboard.json assets/template/src/dag/metrics.py`.

## Rules

- **Idempotent assets**: re-materialising a partition gives the same result and replaces, never appends.
- **No secrets in definitions or logs**: passwords from `NAME` or `NAME_FILE`, read at call time, never stored in resource config.
- **No I/O at import time**: definitions load in the webserver, the daemon and every run worker; building a client, reading a
  file or calling the network at import breaks all three.
- **Bounded metric labels**: `job` and `asset` only; never partition keys, run ids or error text.
- **Exact numbers**: money is integers or `Decimal`; polars columns are typed explicitly at the boundary.
- **One code location per image**, `dagster>=1.10,<2`; re-run the tests on every Dagster bump (the event-log API used by the
  metrics sensor is deprecated for removal in 2.0).
- **Dagster's own storage is a separate PostgreSQL database** from the data, with its own backups.

## Verify

```bash
uv run ruff format --check src tests && uv run ruff check src tests
uv run pytest
uv run dagster definitions validate -m dag.definitions
python3 scripts/check_dashboard.py assets/grafana-dashboard.json assets/template/src/dag/metrics.py
```

## Example prompts

- "Add a daily asset that builds the positions table from orders" -> assets, testing
- "Backfill January and block on duplicate order ids" -> assets (partitions, checks)
- "Dagster runs are failing silently, add alerts" -> metrics, deploy
