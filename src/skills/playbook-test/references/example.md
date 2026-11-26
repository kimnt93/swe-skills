# Example run

The owner asks the CTO bot to test a shop on staging before a release. The names are examples.

| # | From → to | What happens | Message |
|---|---|---|---|
| 1 | CTO bot → tester bot | passes the target, functions, accounts and limits on; ends its turn | [handoff](../assets/example/tester-brief.md) |
| 2 | tester bot → its agent | briefs an agent on the `medium` row | [agent brief](../assets/example/agent-brief.md) |
| 3 | agent → tester bot | writes the plans, runs them, runs the failures again, merges the report | `worker_done` |
| 4 | tester bot → CTO bot | opens the report and the evidence of each failure, then reports | [return report](../assets/example/return-report.md) |
| 5 | CTO bot → owner | opens the evidence, reports and stops | pass or fail per function, bugs ready to file |

## The tester's commands

```bash
run=/home/example/test-evidence/shop-stg
mkdir -p "$run/plans"                      # write web.json and api.json here, before anything runs
uv run <web-testing skill>/scripts/web_test.py "$run/plans/web.json" --out "$run/web-1"
python3 <api-cli-testing skill>/scripts/io_test.py "$run/plans/api.json" --out "$run/api-1"
# the second run of what failed, from a plan that holds only those functions
uv run <web-testing skill>/scripts/web_test.py "$run/plans/web-failed.json" --out "$run/web-2"
python3 <web-testing skill>/scripts/testkit.py report --out "$run/report.md" \
    "$run/web-1/results.json" "$run/web-2/results.json" "$run/api-1/results.json"
```

The merged report has one row per function. One that failed twice reads `failed 2 of 2 runs`; one that failed once
and passed once is still `FAIL`, marked `flaky`; one bug is listed for it, with the evidence of both.

## The report

```text
| Function | Result | Why | Evidence |
|---|---|---|---|
| A customer asks the price of three items | PASS | every expected output seen; slowest answer 240 ms | web-1/quote/ |
| A customer applies a discount code | FAIL | failed 2 of 2 runs; step 3: failed request: POST /api/coupon -> 500 | web-1/coupon/, web-2/coupon/ |
```

Each bug under **Bugs ready to file** has a title, the steps with their inputs, the expected result, the observed
output and its evidence files. The report ends: no code was changed, no issue was filed.

## When production is the only target

The CTO bot asks the owner about each action that would spend, trade, delete or message, by name. Without a clear yes,
the brief says not to run it, and the report lists it as `NOT RUN` with that reason. An approval for one step covers
that step only, once.
