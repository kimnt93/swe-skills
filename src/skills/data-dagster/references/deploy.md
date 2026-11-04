# Deploying Dagster

- **Two processes, one image**: `dagster-webserver` (UI and GraphQL, port 3000) and `dagster-daemon` (schedules, sensors, run
  queue). Without the daemon nothing is scheduled and the metrics sensor never runs. Template: `Dockerfile`,
  `docker-compose.yaml` (local), `dagster.yaml`, `workspace.yaml`.
- **Storage**: a PostgreSQL database for Dagster itself (`dagster.yaml` `storage.postgres`), separate from the data; back it up.
- **Run launching**: the default launcher runs each run as a subprocess of the daemon (fine for one host). Use
  `DockerRunLauncher` or a per-run container when runs need isolation or different dependencies.
- **Run coordinator**: `QueuedRunCoordinator` with `max_concurrent_runs` (4 here); add tag concurrency limits for shared
  resources such as the source database.
- **Swarm / routing**: the webserver is behind Traefik with auth in front (it has no login of its own); the daemon has no port.
  Compose, labels, secrets and resources: the `deployment-setup` skill. Secrets as files (`*_FILE`), never in `dagster.yaml`.
- **Persistence**: `DAGSTER_HOME` on a volume for local run storage if you are not on PostgreSQL; the asset output directory on a volume.
- **Upgrades**: stop the daemon, `dagster instance migrate`, start. Pin `dagster` in `pyproject.toml`.
- **Logging and errors**: `service-logging` and `service-errors` apply to the code-location process.
