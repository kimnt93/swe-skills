# The docs/ layout

```
docs/
  README.md                 summary of the repo's usage + the index of the reference files
  references/
    <topic>.md              one topic each: an API, a command set, the configuration, an event, a data model
```

## docs/README.md

- Two or three lines: what the repo is for and who uses it.
- A quick start: the shortest working use, with commands that run.
- The index, one line per reference file:

  | Reference | Covers | Open it when |
  |---|---|---|
  | `<topic>` (a file in references/) | the HTTP endpoints, request and response shapes, errors | you call this service |

A dependent repo reads this file, then one reference. Keep it under one screen.

## A reference file

- Starts with what the topic is and the versions or ids it applies to.
- One section per operation: the signature or request, the response or output, the errors, one runnable example.
- Names and shapes copied from the code, never from memory.
- Written so a developer of another repo can implement against it without reading this repo's source.

## What does not go here

Plans, decisions with a "why" (an ADR in the repo), the change log (the **changelog** skill), and anything that
describes how the code is organised inside (it changes with every refactor; the code is the reference).
