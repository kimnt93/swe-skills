# Output Contract: `delegate-relay.result.v1`

Every delegation runner (`delegate.py` or agent-specific relays) produces an output JSON conforming to `delegate-relay.result.v1`.

## JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "DelegateRelayResultV1",
  "type": "object",
  "required": [
    "schema",
    "agent",
    "mode",
    "status",
    "exitCode",
    "executionTimeMs",
    "touchedFiles"
  ],
  "properties": {
    "schema": {
      "type": "string",
      "enum": ["delegate-relay.result.v1"]
    },
    "agent": {
      "type": "string",
      "description": "Identifier of the agent executed (e.g. codex, claude, omp, pi)."
    },
    "mode": {
      "type": "string",
      "enum": ["orca_session", "t3_thread", "direct_cli"]
    },
    "status": {
      "type": "string",
      "enum": ["success", "error", "timeout", "interrupted"]
    },
    "exitCode": {
      "type": "integer"
    },
    "executionTimeMs": {
      "type": "integer"
    },
    "touchedFiles": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Relative paths of files created or modified during the turn."
    },
    "diffStat": {
      "type": "string",
      "description": "Output of git diff --stat."
    },
    "verification": {
      "type": ["object", "null"],
      "properties": {
        "command": { "type": "string" },
        "passed": { "type": "boolean" },
        "output": { "type": "string" }
      }
    },
    "summary": {
      "type": "string",
      "description": "Truncated terminal output or agent final report."
    }
  }
}
```

## Example Payload

```json
{
  "schema": "delegate-relay.result.v1",
  "agent": "codex",
  "mode": "orca_session",
  "status": "success",
  "exitCode": 0,
  "executionTimeMs": 42150,
  "touchedFiles": [
    "src/components/TableView.tsx",
    "src/components/TableView.test.tsx"
  ],
  "diffStat": "2 files changed, 84 insertions(+), 3 deletions(-)",
  "verification": {
    "command": "npm test",
    "passed": true,
    "output": "PASS src/components/TableView.test.tsx"
  },
  "summary": "Implemented TableView with pagination and filter controls."
}
```
