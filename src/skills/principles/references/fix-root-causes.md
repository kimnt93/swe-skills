<!-- applies: Apply when debugging. -->
# Fix Root Causes

Trace the symptom back to the first place the system went wrong, and fix it there.

- A `nil` / `None` check is a fix only if the value can legitimately be missing. If it can't, find who produced it.
- A retry is a fix only for a transient failure. Retrying a deterministic error hides it.
- A `recover()`, a bare `except Exception`, an `.unwrap_or_default()` that swallows the error is a symptom guard. Remove it with the real fix.
- Name the root cause in one sentence in the PR, with the evidence (the log line, the trace, the failing test).
