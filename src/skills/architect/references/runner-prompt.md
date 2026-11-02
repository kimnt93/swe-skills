# Runner prompt (one design sketch)

You are sketching one design for the task below. Return a sketch, not an implementation.

- Start from the caller: write 2–3 realistic call sites (an HTTP request and its JSON, a consumer
  receiving an event, a notebook cell, a component using a hook) before any type.
- Data first: name the core types and the SQL tables, topics or API shapes they map to. Make illegal
  states unrepresentable (the **type-system-discipline** principle).
- Layers: `interfaces → application → domain`; the domain does no I/O and reads no clock; adapters
  implement ports (the **boundary-discipline** principle).
- Shared state: if two actors can write the same thing, say what happens. Default to separate state
  merged at the read (the **separate-before-serializing-shared-state** principle).
- Retries and duplicates: every handler is idempotent (the **make-operations-idempotent** principle).
- Short call chains: if following one request needs more than three files, flatten it
  (the **minimize-reader-load** principle).
- Name what you rejected and why, in one line each.

Return: the call sites, the type sketch with `not implemented` bodies, the module map, and the rejected alternatives.
