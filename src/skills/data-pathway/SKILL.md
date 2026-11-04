---
name: data-pathway
description: Build realtime data pipelines with Pathway (Python, Rust engine) - Kafka in, streaming transforms, tumbling and sliding windows, joins, Kafka or database out - from a tested project template with config from env, pure business logic, persistence, the shared stream_pipeline_* OTel metrics and a Grafana dashboard. Use when starting, changing or reviewing a Pathway streaming job, a realtime aggregate or enrichment over Kafka, or when asked for Pathway, streaming ETL, live windows or incremental recomputation in Python.
compatibility: Python 3.11+ and the pathway package (Linux or macOS). The template's pure-logic tests run with pytest alone; its Pathway tests need pathway and pandas installed. Not yet run end to end against a live Pathway install by the authors - treat versions as a starting point and run the checks below.
metadata:
  group: data
  summary: "Realtime Pathway pipelines: Kafka in/out, windows, template, OTel metrics, dashboard"
  version: "1.0"
---

# Pathway pipelines

Pathway runs a streaming dataflow written as ordinary Python table operations and keeps every output
incrementally up to date as input rows arrive. In this stack it is the tool for **realtime transforms,
windows and joins over Kafka** where the result must update continuously. Batch jobs and schedules are
Dagster ([data-dagster](../data-dagster/SKILL.md)); plain consume-and-act services are Go (`go-code`).

## When to use it

| The need | Use |
|---|---|
| Kafka topic in, cleaned/enriched/aggregated topic out, continuously | **Pathway** (this skill) |
| Rolling or tumbling window per key, latest-value-per-key, streaming joins | **Pathway** |
| A stateless consumer that calls an API or writes rows | `go-code` (Kafka reference) |
| Hourly/daily batch, backfills, asset lineage | `data-dagster` |
| Model training and evaluation | `py-code` (ml) |

## How to work

1. **Pick the shape**: input topic(s) and schema, the outputs, the window and its event-time column, the
   allowed lateness. Write the contract (topic names, JSON fields, units) before code.
2. **Copy the template** `assets/template/` into the repo (`pyproject.toml`, `src/pipeline/`, `tests/`,
   `Dockerfile`, `Makefile`, `.env.example`). Rename the package and the service.
3. **Keep business logic pure** in `transform.py` (no `pathway` import) and wire it with `pw.apply` in
   `pipeline.py`. The pure functions get ordinary pytest tests; the table logic (`build`) gets static-table
   tests with `pw.debug.table_from_rows`. Read [pipeline](references/pipeline.md).
4. **Config from the environment** (`config.py`): every setting named, secrets from `NAME` or `NAME_FILE`,
   no defaults for secrets. Kafka settings in [pipeline](references/pipeline.md).
5. **Metrics**: the shared `stream_pipeline_*` set via `pipeline_metrics.py` (a copy of the
   `data-realtime-metrics` template) fed from `pw.io.subscribe`. Read [metrics](references/metrics.md);
   verify with `data-realtime-metrics/scripts/otlp_check.py --role transform`.
6. **Dashboard**: import `assets/grafana-dashboard.json` (uid `pathway-pipelines`): rows in, rejected, out,
   event-to-output latency, lag, freshness, restarts. No per-service edits.
7. **Persistence and deploy**: a volume for `PERSISTENCE_DIR`, one replica per consumer group,
   restart policy, health. Read [deploy](references/deploy.md) and the `deployment-setup` skill.
8. **Verify**: `make verify` (ruff + pytest), then a live run against a local Kafka that produces the
   sample JSON and reads both output topics. Report what ran.

## Rules

- **Event time, not arrival time**, for windows. Name the time column, its unit (epoch seconds here) and the
  lateness you accept; late rows are dropped on purpose and counted as `dropped`.
- **Exact numbers**: money and prices become integers (ticks) or `Decimal` in `transform.py`, never float
  arithmetic in the dataflow.
- **Pure functions, thin wiring**: logic outside `pw.apply` closures so it is testable without Pathway.
- **One status per arrival**: each input row is `received` once and is either `published` or `dropped`.
- **At-least-once at the edges**: the Kafka writer can repeat rows after a restart; give downstream keys
  (`order_id`) and make consumers idempotent (the `idempotency` principle).
- **No per-key metric labels**: symbols, users and topics never become labels (the metric contract).
- **No secrets in logs or settings dumps**; Kafka credentials from files on Swarm.
- Versions: pin `pathway` in `pyproject.toml`; the API moves between minor versions, so re-run the tests on every bump.

## Verify

```bash
uv run ruff format --check src tests && uv run ruff check src tests
uv run pytest                      # pure tests always; Pathway tests when pathway is installed
python3 ../data-realtime-metrics/scripts/otlp_check.py --role transform --wait 60 &   # then start the pipeline
```

## Example prompts

- "Aggregate orders per symbol per minute from Kafka with Pathway" -> template + pipeline reference
- "Add a Pathway job that joins trades with the latest quote" -> pipeline reference (joins)
- "Why is the Pathway pipeline's latency high?" -> metrics + deploy references (autocommit, lag)
