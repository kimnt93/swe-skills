# The web test plan

A JSON file you write **before** the run. A full one: [example plan](../assets/example-plan.json). An unknown key is
refused, so a typo cannot silently drop an expectation.

| Key | Meaning |
|---|---|
| `environment` | `local`, `staging` or `production`. No default |
| `target` | the app's URL; a step's `url` is relative to it |
| `allow_hosts` | other hosts the app needs, as `host:port`, such as its separate API |
| `functions` | each: `id` (lower case, `-`), `name` (what the user does), `steps` |

One function is one thing a user wants done. Each starts in a fresh browser, so it starts with a `goto` and signs in
itself if it must. It stops at its first step that does not pass.

## Steps

| `action` | Needs | What happens |
|---|---|---|
| `goto` | `url`, `expect` | the address is opened |
| `type` | `on`, one input | clicked, cleared and typed key by key |
| `fill` | `on`, one input | the value is set at once; for long text |
| `click` | `on`, `expect` | a real mouse click |
| `press` | `key`, `expect`, maybe `on` | a key, such as `Enter` |
| `check` | `on`, `expect` | a box is ticked |
| `select` | `on`, `value`, `expect` | an option is chosen |
| `expect` | `expect` | nothing is done; something must appear |

`click`, `press`, `check` and `select` each record a video.

**One input:** `value` (the text itself), `secret` (a variable's name; password fields only) or `env` (a variable's
name, for an account name). Use realistic values: a plausible name, address and amount, and for a validation function
the wrong ones a real user would type. A new line in `type` is refused: it is the Enter key, so write a `press`.

**`on`** names a control as a user finds it: `{"role": "button", "name": "Get quote"}`, `{"label": "Quantity"}`,
`{"placeholder": "..."}`, `{"text": "..."}`; `{"testid": "..."}` or `{"css": "..."}` only when nothing else does. Two
matches fail the step; `"exact": true` narrows a name.

## Expected results

All that are given must hold. A step with none is refused, except `type` and `fill`, which then expect the field to
hold the input.

| `expect` key | Holds when |
|---|---|
| `text` | the page shows the text |
| `gone` | the page no longer shows it |
| `in` | a CSS selector: `text` and `gone` look only there; its content is the observed output |
| `url_contains` | the address contains it |
| `value` | the field (or `in`) holds it |
| `status` | a request of this step answered with it; `request` names the address by a part of it |

Prefer the exact result a user cares about (`Total: 29.97` in the quote box) over a word that is always on the page: an
expectation already true before a click fails the step. A 4xx the function is meant to answer is expected with `status`.

`expected` adds a sentence for the report: what the user should get.

## Time

- `max_ms`: the budget from the action until the result is there and its requests have answered. Over it is a FAIL
  (`slow`). Default 2000, for `goto` 5000. Take it from the requirement; say so when you used the default.
- `timeout_ms`: when the runner gives up. Default: 10000, or twice the budget when that is more.

## Other keys

- `effect`: `read` (default), `write`, `spend`, `trade`, `delete` or `message` ([safety](safety.md)).
- `dialog`: `accept` or `dismiss` (default) for a confirm or alert the step opens.
- `ignore_requests`, `ignore_console`: parts of an address or message to leave out of the judgment, for noise that is
  not this app's. Name each one you used in your report, with why.
