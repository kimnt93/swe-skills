---
name: blast-radius
description: "Find what a change could break elsewhere before it ships, beyond the diff, and prove the one fact it is safe because of by running code. Use for a small-looking change to shared code, a config, a schema, a message format, an API response, or a dependency bump."
metadata:
  group: process
  upstream: "cursor/plugins pstack@ae5650f skills/blast-radius (rewritten)"
---

# Blast radius

Reading the code says what it does; its history says why. Blast radius says what it breaks somewhere else.

1. **Read the change**, including what the diff doesn't spell out: a changed default, a renamed JSON
   field, a new NOT NULL column, a narrower type, a different error code.
2. **Find the one fact it is safe because of** ("only this service reads the column", "the field is
   ignored by every consumer"). Most risky-looking changes are safe because of one fact.
3. **Look where grep stops:**
   - other repos and services: who calls this `/v1` route, who consumes this Kafka topic, who
     queries this table (`gh search code`, the deployment compose files);
   - the frontend: the TypeScript client generated from the OpenAPI file;
   - wire formats: JSON tags (`json:"..."`), msgspec field names, serde renames, Avro or protobuf;
   - Python packages with a Rust core: the PyO3 signature and its type stubs;
   - config: env variables in `deploy/*.env` and the compose files of every environment.
4. **Rate each risk** with a real chance and a real cost; list the ones you checked and cleared.
   Cite `file:line`; a search that finds nothing is still an answer.
5. **Prove the one fact** with code that runs: a test, a query on staging, a contract check
   (`audit_api.py`, `probe_api.py`), and paste the result.
6. For a wide change, ask another model family the same question and merge the answers.

**Reply:** the safety fact and its proof, the confirmed risks, the cleared ones.
