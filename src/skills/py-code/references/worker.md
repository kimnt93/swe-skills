# Python workers

*Verified with: Kafka consumer pattern verified in the scaffold template (live broker). Run a smoke test in the target project before relying on specifics.*

A worker is a separate **process** with its own command (`service worker --queues ...`, `service consume`), health check and
replica policy; the API never imports worker-only dependencies and never runs long work in a request.

## Celery (jobs with retries, schedules, fan-out)

- **Tasks carry ids and the trace context, not data:** `task(submission_id, traceparent)`; the worker loads state from PostgreSQL
  (the source of truth). Messages stay small and replayable.
- **Idempotent by design.** A task may run twice (retry, redelivery, worker crash): guard with a database state transition
  (`UPDATE ... WHERE status = 'queued' RETURNING`), a unique key, or `ON CONFLICT`. Set `acks_late=True` with
  `reject_on_worker_lost=True` only for idempotent tasks.
- **Routing:** one queue per workload class (control vs heavy simulation), `worker_prefetch_multiplier=1` for long tasks,
  `--max-tasks-per-child` to bound leaks, explicit `soft_time_limit`/`time_limit`, and memory limits in the Swarm file sized
  as concurrency x per-task memory + headroom.
- **Retries:** `autoretry_for=(TransientError,)`, exponential backoff with jitter, a max; permanent failures mark the row
  failed and stop. Never retry on validation errors.
- **Beat** is exactly one replica (a second one double-schedules); a reaper task republishes work stuck in `queued`.
- **Prefork lifecycle:** build clients, tracing and logging in `worker_process_init` (per child), shut them down in
  `worker_process_shutdown`; never share a connection pool across `fork()`.
- **Tracing:** `CeleryInstrumentor().instrument()` in each child and in the publisher; pass `traceparent` explicitly as well so
  re-published tasks stay in one trace (`service-tracing`).
- **Results:** do not use the result backend for business data; write results to PostgreSQL/object storage.

## Kafka consumer process

Use `messaging/kafka.py` from the scaffold template: `Consumer` with `enable.auto.commit=False`, poll in an executor, commit after the
handler, `close()` in `finally`. Rules: idempotent handlers (`ON CONFLICT`), one consumer group per logical consumer
(`KAFKA_CONSUMER_GROUP`), create topics first, decode with a reused `msgspec` decoder ([data](data.md)), poison
messages go to a `.dlq` topic after N attempts, metrics per `data-realtime-metrics`, and SIGTERM sets the stop event (finish the
current message, commit, leave the group).

## Process layout and deployment

One compose service per command; same image, different `command:`; `HEALTH_DEPS` lists what that process uses
(`postgres,redis,kafka`); workers have no HTTP port, so the health check is `scripts/health.sh` (infrastructure only);
single-writer or single-consumer services run `replicas: 1` with `stop-first` updates (`deployment-setup`).

## Example usage

- “Add a Celery task that validates a submission, then fans out two simulations and a notify step.”
- “Write a Kafka consumer process that upserts ticks and shuts down cleanly.”
