"""Smoke test: emit every metric once so scripts/otlp_check.py can verify the
contract.

python3 scripts/otlp_check.py --role ingestion --wait 20 &
python3 assets/templates/python/smoke.py http://127.0.0.1:4318 ingestion
"""

import sys
import time

from pipeline_metrics import PipelineMetrics

endpoint, role = sys.argv[1], sys.argv[2]
m = PipelineMetrics(
    "feed-ws-"
    + {"ingestion": "feed", "transform": "transform"}.get(role, role),
    environment="local",
    endpoint=endpoint,
    export_interval_ms=1000,
    ingestion=role == "ingestion",
)
m.set_kafka_healthy(True)
m.set_backlog(lambda: 3)
if role == "ingestion":
    m.set_connected(True)
    m.set_in_flight(lambda: 2)
    m.reconnect()
m.received(2)
m.received(1, live=False)
m.dropped(1)
m.published(2, bytes=128, latency_ms=4.2)
m.error()
time.sleep(3)
m.shutdown()
