# Python data and speed

*Verified with: Benchmarks in scripts/bench.py measured on Python 3.12 with msgspec 0.22, orjson 3.12, ciso8601 2.3, pandas 3.0, polars 2.0 (the repositories pin polars 1.44; the calls used exist in both).*

Choose the library from the job, then **measure on the target machine** (`python3 scripts/bench.py`). Measured here
(single tick of ~250 bytes, median):

| Job | Result (x = slower than fastest) |
|---|---|
| decode JSON to typed object | `msgspec` Struct 0.95 us (1.0x) · `orjson` dict 1.06 us (1.1x) · stdlib `json` 4.3 us (4.5x) |
| encode JSON | `orjson` 0.41 us (1.0x) · `msgspec` 0.67 us (1.6x) · stdlib 5.1 us (12x) |
| parse `2026-10-07T03:14:15.926Z` | `ciso8601` 0.14 us (1.0x) · `datetime.fromisoformat` 0.23 us (1.6x) · `dateutil` 6.4 us (45x) · `strptime` 6.5 us (46x) |
| group-by over 2M rows x 500 keys | polars lazy 11 ms (1.0x) · polars eager 32 ms (2.9x) · pandas 160 ms (14x) |
| per-row Python callback, 200k rows | polars expression 0.14 ms · pandas `apply(axis=1)` 2.5 s (about 17,000x) |

## JSON and messages

- **Messages you own the schema of** (Kafka, queues, files): `msgspec.Struct` with a reused `msgspec.json.Decoder(T)`.
  Validates types while decoding, no intermediate dict. `frozen=True`, `omit_defaults=True` for compact output;
  `array_like=True` for positional wire formats; `tag=` unions for message families. MessagePack:
  `msgspec.msgpack`.
- **Dict-shaped or unknown JSON, HTTP responses:** `orjson.loads/dumps` (bytes in, bytes out; native `datetime`, `UUID`,
  dataclasses; `OPT_SERIALIZE_NUMPY`, `OPT_NAIVE_UTC`; a `default=` hook for the rest).
- **API edges and settings:** `msgspec` as well (`Struct` + `Meta` constraints, `msgspec.convert(data, T)` for a decoded dict,
  `strict=False` for text from the environment). **Never pydantic**: it is slower (2-4x) and pulls FastAPI-style coupling in.
- **Forward, do not parse:** a frame you only relay stays `bytes` (hash it, publish it). Read a few fields from a big
  document with a targeted decode (a `Struct` with only those fields, ignoring the rest), not a full tree.
- Never `json.loads(json.dumps(x))` to copy; never build JSON by string concatenation.

## Timestamps

- Timezone-aware UTC end to end; parse once at the edge, keep `datetime`/integer ns inside, format once at the edge.
- Hot loops: `ciso8601.parse_datetime`. Elsewhere `datetime.fromisoformat` (3.11+ handles `Z`) is enough: the gap is 1.6x, not
  45x. Never `strptime`/`dateutil` per row.
- Prefer integer epoch (ms/ns) on the wire between your own services; document the unit in the field name (`ts_ns`).
- In polars use `pl.Datetime("ns", "UTC")`; convert with `str.to_datetime`/`dt.convert_time_zone`, not Python callbacks.
- Local-market times (for example UTC+7 sessions) are converted to UTC at the boundary with a documented rule.

## Tables and time series: polars, not pandas

- **Expressions, not loops:** `df.with_columns((pl.col("price") * pl.col("volume")).alias("value"))`; no `map_elements`/`apply`
  on a hot path; no `iter_rows` for transforms.
- **Lazy first:** `pl.scan_parquet(path).filter(...).group_by(...).agg(...).collect()` so predicates and projections push down;
  `collect(engine="streaming")` for data larger than RAM; `collect()` once, at the end.
- **Types:** explicit dtypes (`pl.Int64`, `pl.Float64`, `pl.Categorical` for repeated symbols), UTC datetimes, `null` for
  missing (never `0`/`NaN` as a sentinel unless the contract says so).
- **Joins on time:** `join_asof` (backward, `by=` key) for point-in-time correctness; never forward-fill into the past.
- **Storage/interchange:** Parquet (zstd) and Arrow IPC; `df.to_arrow()` / `pl.from_arrow` are zero-copy; `to_numpy()` for
  numeric kernels; `to_pandas()` only at a third-party boundary that demands it.
- **pandas -> polars map:** `groupby().agg` -> `group_by().agg`; `df[col] = ...` -> `with_columns`; `merge` -> `join`;
  `merge_asof` -> `join_asof`; `apply(axis=1)` -> an expression; `.loc` filter -> `filter`; `pd.to_datetime` -> `str.to_datetime`.
- Pin polars exactly (it is pre-1.x-stable in places); re-run the tests on upgrade.

## Other speed levers

- Hash with `blake3` (content digests) or `xxhash` (non-cryptographic); compress with `zstandard` (storage) or `lz4` (wire).
- `uvloop` is installed by `uvicorn[standard]`; keep the event loop free of blocking calls.
- Use `__slots__`/`dataclass(slots=True)` for many small objects; generators for streams; `functools.lru_cache` for pure lookups.
- Profile before tuning: `python -X importtime`, `cProfile`/`py-spy`, `scripts/bench.py`-style micro-benchmarks with medians.

## Example usage

- “Replace the pandas aggregation in this job with polars and show the speed-up.”
- “Make this Kafka consumer decode faster.” (msgspec Struct decoder, no dict round trip)
