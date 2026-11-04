# Pathway pipeline reference

Template: `assets/template/src/pipeline/` (`config.py`, `transform.py`, `pipeline.py`, `__main__.py`).

## Input

```python
class OrderIn(pw.Schema):
    order_id: str
    symbol: str
    price: float
    qty: float
    ts: int            # event time, epoch seconds

orders = pw.io.kafka.read(
    settings.kafka(),                  # rdkafka dict from config.py
    topic=settings.topic_in,
    schema=OrderIn,
    format="json",
    autocommit_duration_ms=100,        # latency/throughput trade-off
)
```

- Declare every column and its type; a message that does not match the schema is an error to count, not a crash.
- `autocommit_duration_ms` bounds how long Pathway buffers before emitting: lower for latency, higher for throughput.
- Consumer group id comes from config; one replica per group unless you shard topics on purpose.
- `auto.offset.reset=earliest` is for a new pipeline; with persistence on, a restart resumes where it stopped.

## Transform

- Per-row logic: `pw.apply(fn, pw.this.col, ...)` for a plain Python function (keep the function in `transform.py`).
  For heavy or async calls use `pw.udf` / `pw.udfs.async_executor`, with a timeout and a retry strategy.
- Filtering: `table.filter(expression)`; the rejected side is `table.filter(~expression)`, counted as `dropped`.
- Select/rename: `table.select(name=pw.this.col, ...)`; never mutate in place.

## Windows

```python
agg = clean.windowby(
    pw.this.ts,
    window=pw.temporal.tumbling(duration=60),     # or sliding(hop=10, duration=60), session(max_gap=30)
    instance=pw.this.symbol,                      # per-key windows
).reduce(
    symbol=pw.this._pw_instance,
    window_start=pw.this._pw_window_start,
    orders=pw.reducers.count(),
    qty=pw.reducers.sum(pw.this.qty),
)
```

- Windows are by **event time**. Decide lateness: use a `pw.temporal.exactly_once_behavior()` / `common_behavior(cutoff=...)`
  so state for closed windows is released; without a cutoff state grows without bound.
- Output is incremental: a window updates as rows arrive (retractions and additions). A Kafka sink emits each change;
  if consumers want one row per closed window, use the exactly-once behaviour and key on `(symbol, window_start)`.

## Joins and state

- `left.join(right, left.key == right.key).select(...)` is incremental on both sides; for "latest quote per symbol",
  reduce the quote stream with `pw.reducers.argmax(pw.this.ts)` first, then join.
- Everything stateful is held in memory unless persistence is configured: keep keys bounded, put cutoffs on windows.

## Output

```python
pw.io.kafka.write(clean, settings.kafka(), topic_name=settings.topic_out, format="json")
```

- JSON output carries `time` and `diff` columns (the change time and +1/-1); consumers must handle `diff = -1` or you must
  filter retractions before writing. Decide this in the contract and test it.
- PostgreSQL/ClickHouse sinks exist (`pw.io.postgres`); prefer Kafka out and the existing sink services (`sink` role).

## Persistence

```python
backend = pw.persistence.Backend.filesystem(settings.persistence_dir)
pw.run(persistence_config=pw.persistence.Config(backend))
```

A mounted volume lets a restart resume without replaying the whole input. Change the dataflow shape and the old state is
invalid: clear the directory on a deliberate shape change and replay from earliest.

## Testing

- `transform.py`: plain pytest, no Pathway.
- `build(...)`: `pw.debug.table_from_rows(Schema, rows)` then `pw.debug.table_to_pandas(table)`; assert rows, the rejected
  side, and the window counts. Static tables compute the final state, which is what you assert.
- Live: a local Kafka, produce the sample messages, read both output topics.
