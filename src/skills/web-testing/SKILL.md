---
name: web-testing
description: "Test a web app as a real user does: open it in a real browser, click and type with realistic inputs, and record for every step the input, the expected result and the observed output, with screenshots, a video of each click until the answer arrived, key frames named by time, and an analysis of timing, console errors, failed requests and slow or missing answers. Fails broken, slow and dead functions. Use when asked to test, QA or check a web app or UI in a browser, or to get evidence of a UI bug. For an API or a command-line tool use api-cli-testing; for a whole test run with a report use playbook-test."
metadata:
  group: process
  summary: "Test a web app as a user: real clicks, screenshots, a video per click, pass or fail with evidence"
---

# Web testing

Test what a user sees: a real browser, real mouse and keyboard events, and evidence another agent can check.

**First read [safety](references/safety.md).** It limits what you may test and do; the runner enforces most of it.

| Need | Read |
|---|---|
| what you may touch, production, credentials, evidence | [safety](references/safety.md) |
| write the plan: actions, controls, expected results, budgets | [plan](references/plan.md), [example plan](assets/example-plan.json) |
| how a step is judged, and how to read the videos without playing them | [analysis](references/analysis.md) |

## The browser

`scripts/web_test.py` drives Playwright (pinned in the script): one script with no window, real clicks and
keystrokes, a video of exactly one click, each request's duration and the ones still unanswered, console errors with
their times, and a guard on every request. Orca's embedded browser (the `orca-cli` skill) also clicks, types, takes
screenshots, records through `exec --command "record start <file>.webm"` and lists console and network entries: use it
to **look around** before you write the plan. Its network list gives no duration and no unanswered state, so it does
not judge a run.

## Steps

1. **Look** at the app as its user would. List the functions the request covers.
2. **Write the plan before you run**: per function, the steps with realistic inputs and the expected result of each.
   Take expected results from the request, the spec or the user's goal, never from whatever the page happens to show.
3. **Run it.** Needs `uv` and `ffmpeg`; the browser installs once. The evidence directory is empty and outside any
   repository.

   ```bash
   uv run --with playwright==1.65.0 playwright install chromium
   uv run <this skill>/scripts/web_test.py plan.json --out ~/test-evidence/<run>
   ```

4. **Check the evidence yourself.** Open the screenshot and the key frames of every step that did not pass, and the
   last frame of every click that did. Each click has `<step>.analysis.md`: the timeline and the frames with their times.
5. **Sort each failure.** A mistake in your plan (a wrong control name) is fixed in the plan and run again, and you say
   what you changed. Never loosen an expected result or a time budget to turn a FAIL into a PASS. Run a real failure a
   second time: report one that happens once as flaky, still a FAIL.
6. **Report** `report.md`: pass or fail per function, evidence paths, bugs ready to file. Add what you did not test.

## Limits

State the ones that matter for your run:

- A new tab or popup is guarded, but the video shows the first page only. There is no file upload or drag action.
- The browser follows a server's redirect before the runner can hold it: the step is then `NOT RUN`, after the fact.
  A redirect that repeats a `POST` (307, 308) is not held either.
- On production, a `GET` that changes data is caught only by a risky word in its control or address.
- Frames come 25 per second; the runner's event times are within about 50 ms.

## One good, one bad

- **Good:** "Apply coupon: FAIL. `POST /api/coupon` -> 500, the page still says *No coupon applied*, seen in 2 of 2
  runs. Evidence: `coupon/03-click.analysis.md` and its frames."
- **Bad:** "I looked at the app and it works." No inputs, no expected results, nothing anyone can check.

## Done

Every function in scope has `PASS`, `FAIL` or `NOT RUN` with its reason; every click has a screenshot, a video that
opens and key frames; you opened the evidence behind each failure; you changed no code.
