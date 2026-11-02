# Replay entrypoint contract

The entrypoint is a small binary or module in the service. It must exercise the same code the
Kafka consumer runs, minus the I/O.

| Requirement | Why |
|---|---|
| reads JSON Lines from stdin, one event per line, in order | the script feeds recorded or mutated streams |
| applies each event through the **application layer** (the same use case the consumer calls), with in-memory adapters for the ports | the replay tests your code, not a copy of it |
| dedups exactly as production does (the same key, the same store interface) | `--mutate duplicate` and `redeliver` test that path |
| prints one JSON object on stdout at the end, keys sorted, money as decimal strings or integer minor units | exact comparison |
| no network, no wall clock (take time from the event), no randomness | the same stream always gives the same state |
| exits non-zero on an event it cannot apply | a silent skip would hide a bug |

## Go (`cmd/replay/main.go`)

```go
func main() {
	store := memory.NewStore()          // implements the application's ports
	fills := application.NewFills(store) // the same use case the consumer calls
	scanner := bufio.NewScanner(os.Stdin)
	scanner.Buffer(make([]byte, 1<<20), 1<<20)
	for scanner.Scan() {
		var event kafkax.Event
		if err := json.Unmarshal(scanner.Bytes(), &event); err != nil {
			log.Fatalf("replay: bad event: %v", err)
		}
		if err := fills.Apply(context.Background(), event); err != nil {
			log.Fatalf("replay: apply %s: %v", event.ID, err)
		}
	}
	state := store.Snapshot() // positions, balances, P&L, order states; decimals as strings
	if err := json.NewEncoder(os.Stdout).Encode(state); err != nil {
		log.Fatal(err)
	}
}
```

## Python (`python -m service.replay`)

```python
def main() -> None:
    store = MemoryStore()
    fills = Fills(store)
    for line in sys.stdin:
        if line.strip():
            fills.apply(msgspec.json.decode(line, type=Event))
    sys.stdout.write(msgspec.json.encode(store.snapshot()).decode() + "\n")
```

## Rust (`cargo run --bin replay`)

Same shape: a `BufRead` over `stdin().lock().lines()`, the application's use case over in-memory
adapters, and `serde_json::to_writer(stdout(), &store.snapshot())` with `rust_decimal` values
serialised as strings.
