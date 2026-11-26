# The API and command-line test plan

A JSON file you write **before** the run ([example](../assets/example-plan.json)). The top keys are the web plan's
([plan](../../web-testing/references/plan.md)): `environment` (no default), `target` (for `http` steps), `allow_hosts`,
`functions`; plus `allow_programs`, the exact first words of the commands that may run. An unknown key is refused. A
function stops at its first step that does not pass.

## `"kind": "http"`

| Key | Meaning |
|---|---|
| `method`, `path` | the request; `path` is relative to `target` and holds no secret |
| `headers`, `json` or `body` | what is sent |
| `expect.status` | required |
| `expect.json` | values the JSON answer must hold; extra keys are fine, a list must match in full |
| `expect.contains` | a text the body must hold |

## `"kind": "cli"`

| Key | Meaning |
|---|---|
| `argv` | the command as a list; no shell, no secret |
| `stdin`, `env` | what it reads |
| `cwd` | relative to the plan file's directory, which is the default |
| `expect.exit` | required |
| `expect.stdout_contains`, `expect.stderr_contains` | texts the output must hold |
| `expect.stdout_json` | like `expect.json`, on standard output |

## Both

- `max_ms` (default 2000): over it is a FAIL (`slow`). `timeout_ms` (default 10000, or twice the budget when that is
  more): then the request is given up or the command and what it started are stopped (`missing response`).
- `expected`: a sentence for the report. `effect`: `read` (default), `write`, `spend`, `trade`, `delete`, `message`
  ([safety](../../web-testing/references/safety.md)).
- A credential is `${secret:<variable>}`, read from the environment. A header or key that names one (`Authorization`,
  `password`, `token`) is refused with a literal value, a deliberately wrong one too: give that one a variable as well.
