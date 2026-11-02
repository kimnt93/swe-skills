### Refactoring

**Behaviour stays identical. Pin it first.**

1. Pin the behaviour: characterization tests through the public surface (handler responses, use-case
   results, rows written, rendered output). They must pass before you move anything.
2. Delete first (the **subtract-before-you-add** principle): dead code, unused flags, one-caller wrappers.
3. Name the target shape; if it crosses a function boundary, run the **architect** skill.
4. Move in small steps, each green. For an internal API change, migrate every caller and delete the
   old API in the same wave (the **migrate-callers-then-delete-legacy-apis** principle). Use a codemod
   for many call sites (`gofmt -r`, `ast-grep`, `libcst`, `ts-morph`).
5. Keep the change only if it lowers reader load (the **minimize-reader-load** principle).
6. If you find a bug, stop: fix it in its own [bug-fix](bug-fix.md) PR first.

**Reply:** the pin, the steps, what got simpler.
