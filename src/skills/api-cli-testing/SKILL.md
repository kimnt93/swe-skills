---
name: api-cli-testing
description: "Test an HTTP API or a command-line tool as its caller does: send real, realistic inputs, and record for every step the input, the expected result and the observed output (status and body, or exit code, stdout and stderr) with the time it took. Fails wrong, slow and missing answers, and writes evidence and bugs ready to file. Use when asked to test, QA or smoke-test an API, an endpoint, a service or a CLI from outside. For a web app in a browser use web-testing; for a whole test run with a report use playbook-test; for unit tests and test-first coding use tdd."
metadata:
  group: process
  summary: "Test an API or CLI as its caller: real inputs, observed outputs, pass or fail with evidence"
---

# API and command-line testing

Call it from outside, as its user does: real requests, real commands, observed outputs. Reading the code or running its
unit tests is not this.

**First read the [safety rules](../web-testing/references/safety.md).** They hold here too, and the runner enforces
what a program can: allowed hosts and programs, approvals on production, credentials from the environment, evidence
outside the repository.

## Steps

1. **Find the contract:** the API's `/docs`, the tool's `--help`, the request. List the functions in scope.
2. **Write the [plan](references/plan.md) before you run** ([example](assets/example-plan.json)). For each function: a
   normal call with realistic values, and the wrong ones a real caller sends (missing, out of range, wrong type, not
   signed in) with the answer each should get. Expected results come from the contract, not from what it answers now.
3. **Run it** (Python only, nothing to install). The evidence directory is empty and outside any repository.

   ```bash
   python3 <this skill>/scripts/io_test.py plan.json --out ~/test-evidence/<run>
   ```

4. **Read the observed output** of every step that did not pass, and check that each pass shows what you meant. A
   status alone proves little: assert the values that matter (`json`, `stdout_contains`).
5. **Sort each failure.** A mistake in the plan is fixed and run again, and you say what you changed; never loosen an
   expectation or a budget to turn a FAIL into a PASS. Run a real failure a second time and say how often it happened.
6. **Report** `report.md`: pass or fail per function, evidence paths, bugs ready to file, and what you did not test.

One report for web and API runs of the same request:

```bash
python3 <web-testing skill>/scripts/testkit.py report --out ~/test-evidence/report.md <run>/results.json <run>/results.json
```

## Evidence

`<out>/report.md`, `<out>/results.json`, and per step `<out>/<function>/01-http.json` or `01-cli.json`: the input as
planned (secrets stay names), the expected result, the whole observed output with credentials cut out, and the time.

## Limits

- Redirects are not followed: a 3xx is the answer. Bodies and outputs are cut at 64 KB.
- A command inherits your environment. A value it prints that the plan did not name as a secret is only cut when it
  looks like a common token: read the evidence before you quote it.
- It checks what comes back, not what changed behind it. To prove a write, add a step that reads it.

## One good, one bad

- **Good:** `GET /v1/orders?limit=0` expects 400 with `{"error": "limit must be 1 to 100"}`; observed 500 and a stack
  trace: FAIL, with the evidence file.
- **Bad:** calling `/healthz`, seeing 200 and reporting "the API works".

## Done

Every function in scope has `PASS`, `FAIL` or `NOT RUN` with its reason and evidence; you changed no code.
