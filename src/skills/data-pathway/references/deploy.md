# Deploying a Pathway pipeline

- **One container per pipeline**, built from `assets/template/Dockerfile` (non-root, state volume at `/var/lib/pw-state`).
- **Swarm**: one replica, `restart_policy: on-failure`, the state directory on a named volume, Kafka credentials as secrets
  (`KAFKA_PASSWORD_FILE`), `stop_grace_period` long enough to flush (30 s). Compose and Traefik conventions:
  the `deployment-setup` skill. A streaming job has no HTTP port; if the platform wants a health check, expose none and rely
  on `stream_pipeline_running` and the last-message-age alert instead.
- **Scaling**: Pathway scales with threads/processes (`PATHWAY_THREADS`, `PATHWAY_PROCESSES`) before replicas. Two replicas in
  one consumer group split partitions but each holds its own window state: only shard when keys are partitioned the same way.
- **Resources**: memory grows with open windows and join state; set a memory limit and an alert on restarts.
- **Alerts** (from the shared metrics): running = 0 for 2 min, last message age above the topic's normal gap, consumer lag
  rising for 10 min, restarts above 3 per hour, errors rate above 0.
- **Rollout**: stop old, start new with the same persistence directory only if the dataflow shape is unchanged; otherwise
  clear the directory and replay from earliest into a new output topic version.
- **Logging and errors**: `service-logging` and `service-errors` apply as for any Python service.
