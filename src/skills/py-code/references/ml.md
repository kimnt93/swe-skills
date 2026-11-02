# ML

Python is the ML language of the stack. ML code is ordinary engineering: a package, tests, a review,
and proof by a number.

## Layout

```
src/<package>/ml/
  data.py       load and validate raw data (polars), one function per source
  features.py   pure functions: frame in, frame out; no I/O, no clock
  split.py      train / validation / test splits
  train.py      fit a model from a config; returns the model and its training report
  evaluate.py   metrics on a split; returns a typed report
  artefact.py   save / load the model + its model card (S3)
  serve.py      inference: load once, predict on validated input
```

Notebooks are for exploration only: anything that will run twice moves into the package with a test.

## Rules

- **Data with polars** (lazy frames for large data), numpy for arrays; no pandas (ruff bans it).
- **No leakage, no look-ahead.** Market and order data split **by time**, never at random: train on
  the past, validate on the next window, test on a later one. Features at time t use only data
  available before t (shift, then roll). Watch survivorship bias in symbol lists.
- **Reproducible:** a config (a `msgspec.Struct`) holds every hyperparameter and the data snapshot id;
  set every seed (`random`, `numpy`, the framework's); dependencies locked with `uv lock`.
- **The model card** saved next to the model: code commit, config, data snapshot id and row counts,
  split boundaries, metrics per split, library versions.
- **Evaluate like a benchmark** (the **explain-the-number** principle and the `benchmark-checklist`
  skill): a fixed split, a baseline (last value, moving average, the current model), the metric with
  several seeds or a confidence interval. A model ships only when it beats the current one on the
  test window.
- **Serving:** batch predictions written to PostgreSQL or a Kafka topic by a worker; or online
  inference from a small Litestar service called by the Go API; or export to ONNX and run it in the
  Go or Rust service when latency matters. Validate inputs at the boundary exactly like training did.
- **Train/serve skew:** one feature function used by both training and serving, tested once.

## Tests

| What | Test |
|---|---|
| feature functions | pytest on small hand-built frames, including NaN, empty, and one-row inputs |
| no look-ahead | a test that shifting future rows does not change past features |
| the pipeline runs | train + evaluate on a tiny fixture dataset in CI (seconds) |
| quality does not regress | a golden test: metric on a frozen small dataset within a tolerance |
| serving matches training | the same rows through `serve.predict` and the training path give equal outputs |

## Performance

Vectorise with polars expressions first; profile with `py-spy`; move a measured hot loop to Rust
(`rust-code` pyrust references) and keep the Python API unchanged.
