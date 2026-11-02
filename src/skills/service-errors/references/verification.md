# Verification

Three levels, cheapest first. A claim that errors reach Sentry needs the second level at least; the third needs access
to the real project.

## 1. Unit tests (shipped with every template)

The tests start a fake ingest inside the test process and assert the contract: one event for a repeated error, release,
environment, trace id, no private scope data, nothing for warnings or an empty DSN, no DSN in an error.
Go: `go test ./internal/errtracking/`. Python: `pytest tests/test_errors.py`. Rust: `cargo test errtracking`.
Keep them in CI: SDK upgrades change defaults.

## 2. The running service against the local receiver

```bash
python3 scripts/sentry_receiver.py serve --port 9100 --out events.jsonl &
SENTRY_DSN=http://test-key@127.0.0.1:9100/1 ENV_NAME=stg SERVICE_NAME=account-api SERVICE_VERSION=1.4.2 \
  <start the service, cause one failure that logs an error, stop it>     # stopping flushes
python3 scripts/sentry_receiver.py check events.jsonl --environment stg --service account-api \
  --release account-api@1.4.2 --forbid "<a secret you put in a log field>"
```

`check` fails on: a wrong environment or release, a `service_name` tag that is not the service, tags outside the
allowlist, request/user/breadcrumbs/contexts/extra, exception text (unless `--allow-exception-text`), stack-frame
locals, and any `--forbid` text. It also fails when no event arrived.

## 3. The real project

With the project's DSN in the plane, trigger a controlled failure on stg and confirm in GlitchTip: the event is in the
service's project, `environment` is `stg`, `release` is the deployed `<service>@<version>`, and the `trace_id` opens the
trace in Tempo and the lines in Loki. Say which of these you actually saw; do not report a rollout you did not observe.

## Static audit

`python3 scripts/audit_errors.py path/to/service` reports `ERR-1..6` (SDK init, hard-coded DSN, privacy switches,
environment and release, scrubber, DSN in env example and Compose). `0 FAIL` is the bar; every WARN is reviewed.
On the reference projects: `trading-simulator` 0 FAIL, `alpha-server` 0 FAIL with a WARN for the DSN committed in
`deploy/stg.env`, `account-engine` 1 FAIL (`ERR-1`: nothing is initialised yet).
