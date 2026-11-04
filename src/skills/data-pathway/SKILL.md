---
name: data-pathway
description: Build realtime data pipelines with Pathway (Python, Rust engine) - Kafka in, streaming transforms, tumbling and sliding windows, joins, Kafka or database out - from a tested project template with config from env, pure business logic, persistence, the stream_pipeline_* OTel metric contract, its timeframes and a Grafana dashboard. Use when starting, changing or reviewing a Pathway streaming job, a realtime aggregate or enrichment over Kafka, or when asked for Pathway, streaming ETL, live windows or incremental recomputation in Python.
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
4. **Config from the environment** (`settings/`, the py-code format): Kafka is `KAFKA_BOOTSTRAP_SERVERS`,
   `KAFKA_SECURITY_PROTOCOL`, `KAFKA_SASL_*`, `KAFKA_CONSUMER_GROUP`; secrets from `NAME` or `NAME_FILE`, no defaults.
   Logs, traces and errors: [see below](#settings-logs-traces-and-errors-same-as-every-python-project). Kafka settings in [pipeline](references/pipeline.md).
5. **Metrics**: the `stream_pipeline_*` contract ([metric-contract](references/metric-contract.md)) via the template's
   `pipeline_metrics.py`, fed from `pw.io.subscribe`; the windows and clocks (event time, commit interval, export interval, query
   windows) are in [timeframes](references/timeframes.md). Wiring: [metrics](references/metrics.md). Verify with
   `scripts/otlp_check.py --role transform`.
6. **Dashboard**: import `assets/grafana-dashboard.json` (uid `pathway-pipelines`): rows in, rejected, out,
   event-to-output latency, lag, freshness, restarts. No per-service edits.
7. **Persistence and deploy**: a volume for `PERSISTENCE_DIR`, one replica per consumer group,
   restart policy, health. Read [deploy](references/deploy.md) and the `deployment-setup` skill.
8. **Verify**: `make verify` (ruff + pytest), then a live run against a local Kafka that produces the
   sample JSON and reads both output topics. Report what ran.


## Settings, logs, traces and errors (same as every Python project)

The template follows the [py-code](../py-code/SKILL.md) rules; do not invent a second format.

| Concern | Where | Rule |
|---|---|---|
| Settings | `pipeline/settings/` | environment only; one class per infrastructure; `Secret` read from `NAME` or `NAME_FILE`, **no default**; one `SettingsError` that names every bad variable and never a value; `.env.example` lists all of it with secrets blank and a test loads it |
| Logs | `pipeline/observability/service_logging.py` | jlogger JSON, the `service-logging` format (`SERVICE_NAME`, `DEVELOPMENT_ENVIRONMENT` or `ENV_NAME`, `NODE_NAME`, `LOG_LEVEL`); never `print` or a bare `logging.basicConfig` |
| Traces | `pipeline/observability/service_tracing.py` | OpenTelemetry through `OTEL_*` (`OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_AUTH_TOKEN(_FILE)`, sampler, `TRACING_DETAIL`); an empty endpoint is a harmless no-op |
| Errors | `pipeline/observability/errors.py` | Sentry or GlitchTip through `SENTRY_DSN(_FILE)`; every `error` log line becomes one scrubbed event; empty DSN sends nothing |

`observability.setup(settings, component=...)` wires the three once at startup and returns the function that flushes them.
The three vendored files come from the `service-logging`, `service-tracing` and `service-errors` skills: update them there, not in the
copy (ruff excludes them). The metrics below use the same endpoint and token as the traces.

## Rules

- **Event time, not arrival time**, for windows. Name the time column, its unit (epoch seconds here) and the
  lateness you accept; late rows are dropped on purpose and counted as `dropped`.
- **Exact numbers**: money and prices become integers (ticks) or `Decimal` in `transform.py`, never float
  arithmetic in the dataflow.
- **Pure functions, thin wiring**: logic outside `pw.apply` closures so it is testable without Pathway.
- **One status per arrival**: each input row is `received` once and is either `published` or `dropped`.
- **At-least-once at the edges**: the Kafka writer can repeat rows after a restart; give downstream keys
  (`order_id`) and make consumers idempotent (the `idempotency` principle).
- **No per-key metric labels**: symbols, users, topics and window lengths never become labels ([metric-contract](references/metric-contract.md)).
- **No secrets in logs or settings dumps**; Kafka credentials from files on Swarm (`KAFKA_SASL_PASSWORD_FILE`).
- Versions: pin `pathway` in `pyproject.toml`; the API moves between minor versions, so re-run the tests on every bump.

## Verify

```bash
uv run ruff format --check src tests && uv run ruff check src tests
uv run pytest                      # pure and settings tests always; Pathway tests when pathway is installed
python3 scripts/otlp_check.py --role transform --wait 60 &   # then start the pipeline
```

## Example prompts

- "Aggregate orders per symbol per minute from Kafka with Pathway" -> template + pipeline reference
- "Add a Pathway job that joins trades with the latest quote" -> pipeline reference (joins)
- "Why is the Pathway pipeline's latency high?" -> metrics + deploy references (autocommit, lag)
