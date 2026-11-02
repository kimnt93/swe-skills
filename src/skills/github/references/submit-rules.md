# Submit rules

A good submission is small, does one thing, and fits the architecture.

1. **One feature function per PR.** A PR delivers one behaviour a caller can observe ("cancel an
   open order"), not a theme ("orders improvements"). Split anything bigger with the router's
   multi-phase playbook.
2. **Small.** At most about 400 changed lines (`pr_lint.py` enforces it; the `size:large` label
   needs a reason). Generated code (OpenAPI types, mocks) goes in its own commit.
3. **Simple first.** No abstraction, option, or layer the change does not need now (the
   **laziness-protocol** principle). A plain function beats a framework; a table beats a strategy pattern.
4. **Follow the architecture, never breach it.** Read the project's `ARCHITECTURE.md` before
   changing structure. Layers stay as the language skill defines them (interfaces → application →
   domain; adapters implement ports); `make verify` runs the enforcers (Go `archcheck`, Python
   `lint-imports`, the TypeScript lint). A change that needs a new boundary is a design change:
   run the **architect** skill and update `ARCHITECTURE.md` (or add an ADR) in the same PR, reviewed.
5. **Stay in scope.** Change only the files the card or issue allows (`pr_lint.py --allow`). A bug
   found on the way gets its own issue and PR.
6. **Tests with the change**, at the level that shows the behaviour (the **tdd** skill).
7. **Proven:** `make verify` green on the committed head, its result in `## Verification`.
8. **Clean:** the **deslop** skill over the diff before you open the PR.
