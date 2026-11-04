"""The code location reads its settings at import (dag.definitions), so the
tests give the required variables a value before anything is imported."""

import os

for name, value in {
    "SERVICE_NAME": "orders-dagster-test",
    "POSTGRES_HOST": "127.0.0.1",
    "POSTGRES_DB": "orders",
    "POSTGRES_USER": "reader",
    "POSTGRES_PASSWORD": "test-only",
    "DAGSTER_PG_PASSWORD": "test-only",
}.items():
    os.environ.setdefault(name, value)
