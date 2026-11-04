### Incident

**Diagnose a live symptom from what production already records.**

1. Define the symptom precisely: which service, which endpoint or topic, since when, how often.
2. Read the evidence, newest first: Sentry/GlitchTip events (the `service-errors` skill), logs in
   Loki by `service_name` and `trace_id` (`service-logging`), traces in Tempo (`service-tracing`),
   pipeline metrics on Grafana (`data-pathway`, `data-dagster` dashboards), recent deploys (`git log`, the CI deploy job).
3. Correlate: the first bad timestamp against deploys, config changes, traffic and dependency health
   (`/healthz` of the dependencies).
4. Reduce it to a repro you can run locally or on staging. If you can't, add the missing
   instrumentation in its own small PR and wait for the next occurrence.
5. Mitigate only with reversible steps (roll back, a feature flag); a deploy needs a human go.
6. Fix through the [bug-fix](bug-fix.md) playbook, with the repro as the failing test.

**Reply:** the timeline, the cause (or the strongest hypothesis, labelled), mitigation, the fix plan.
