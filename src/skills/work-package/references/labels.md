# Labels

Every package carries one lane, one difficulty and at least one area.

| Group | Values | Meaning |
|---|---|---|
| lane | `backend` `frontend` `data` `ops` `docs` `test` `research` | who does it: the kind of work and the agent that gets it |
| difficulty | `simple` `medium` `hard` | how much judgement it needs; routes the model tier |
| area | `bots`, `mobile`, `ci`, ... (any other label) | the part of the product; matches the area of the ID |

## Picking the difficulty

| Difficulty | The package is | Example |
|---|---|---|
| simple | a clear description with test vectors; one pure module or a thin wrapper; docs; tests | add a column and its test |
| medium | several files across layers with a complete rule list; the usual feature or fix | a new route with storage and tests |
| hard | open design choices, concurrency, money paths, security, a cross-repository contract | a change to the order lifecycle |

A package is promoted to `hard` only by the planner or the owner of the work, with a sentence saying why. An agent that finds
its card harder than labelled stops, comments the evidence on the issue, and asks to have it re-labelled; it does not push on.

## Routing

The orchestrator reads the project's model table (the harness, model and reasoning level for each lane and difficulty) and
starts the worker accordingly. The labels never name a model.

## Housekeeping

Create the labels once per repository (`gh label create <name> --color <hex> --description "<text>"`); a typo in a label is a
new label, so list them first (`gh label list`).
