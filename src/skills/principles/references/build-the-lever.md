<!-- applies: Apply to any non-trivial work: edits across many files, migrations, data fixes, checks. Build the tool that does it or proves it instead of working by hand. -->
# Build the Lever

If you will do it more than once, or a reviewer needs to trust it, write the tool.

- A codemod (`gofmt -r`, `go/ast`, `libcst`, `ast-grep`, `comby`) instead of 40 hand edits.
- A script that proves a data migration (row counts before and after, a checksum per batch).
- A `make verify` target instead of a list of commands in a PR body.
- The tool is the artifact: commit it (or attach it), so a reviewer can rerun it.
