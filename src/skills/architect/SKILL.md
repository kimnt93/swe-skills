---
name: architect
description: "Settle types, signatures and module shape before code, by sketching at least two designs and picking one, then implement against the sketch. Use for code that crosses a function boundary, a new service, endpoint, consumer, model pipeline or frontend feature, or whenever jumping to code would lock in the wrong shape."
metadata:
  group: process
  summary: "Sketch types and module shape twice, pick one, then implement against it"
---

# Architect

Sketch first, then code against the sketch.

## 1. Ground

Map what the new code touches with the **how** skill: entry points, data shapes, callers, tables,
topics, endpoints, frontend routes. If the design changes ownership or layering, read the history
with the **why** skill.

## 2. Sketch at least two shapes

Start two subagents on the `developer-senior` agent (different model families when you can), each with the grounding
and [runner-prompt](references/runner-prompt.md). Each returns a sketch in the language of the job:

| Language | The sketch |
|---|---|
| Go | the domain types, the application port interfaces, the use-case function signatures, the Fiber route table; bodies are `panic("not implemented")` |
| Python ML | the dataclasses or `msgspec.Struct`s, the pipeline stages as typed functions (`load → features → train → evaluate → export`), the artefact layout |
| Rust | the types and enums, the public functions and traits, the crate or module map; bodies are `todo!()` |
| TypeScript | the API types (from OpenAPI), the hooks and component props, the route or page tree |

**Design it twice:** two whole-shape alternatives, not two variants of one. Screen each against
[design-red-flags](references/design-red-flags.md). Prefer the one that hides more behind a smaller
public surface.

## 3. Pick and record

Pick a base, graft the best parts of the other, and write the rationale per
[rationale-template](references/rationale-template.md): the caller's usage first, then the types,
then the decision and the rejected alternative. The sketch can land as its own commit.
On request ("architect with checkpoint"), stop here for sign-off.

## 4. Implement against the sketch

Fill the bodies. A needed deviation is a signal: was the sketch wrong, a requirement missed, or the
code overreaching? Say which.

## 5. Scrap when the shape is wrong

The signal is a pattern: the same workaround in unrelated places, special cases in every handler,
escape hatches (`any`, `interface{}`, `Any`, casts, `unwrap` everywhere), a lock where the sketch said
nothing was shared. Then re-map, redesign as if the new facts were known on day one (the
**redesign-from-first-principles** principle), subtract first, and go back to step 2.
