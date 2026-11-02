<!-- applies: Apply when the same instruction is written a second time, or the same correction is made twice. -->
# Encode Lessons in Structure

Turn the lesson into something that fails, not more text.

Prefer, in order: a type that makes the mistake impossible; a lint rule (`.golangci.yml`, ruff `pyproject.toml`, `clippy.toml`, a small checker like `go-code/scripts/structcheck`); a test; a CI step; and only then a sentence in a skill. The **correct** skill runs this loop for a repo.
