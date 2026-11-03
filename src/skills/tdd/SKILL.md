---
name: tdd
description: "Write the failing test first, then the smallest fix or feature that makes it pass, in Go, Python, Rust or TypeScript. Use for a bug with a cheap local test path, when the user asks for TDD or a regression test, and in every bug-fix."
metadata:
  group: process
  summary: "Failing test first, then the smallest change that makes it pass"
---

# TDD

Red, then green, then clean. The test is the proof the bug existed and is gone.

## Steps

1. **Pick the cheapest real level** that shows the behaviour:

   | Language | Unit | Integration (real infra from the local compose) |
   |---|---|---|
   | Go | table test in `*_test.go`, `go test ./...` | `go test -tags e2e ./internal/e2e/...` |
   | Python | `pytest` (`parametrize` for cases) | `pytest -m integration` against the compose PostgreSQL / Redis / Kafka |
   | Rust | `#[test]`, `proptest` for properties | `cargo test --features live` (the template's live tests) |
   | TypeScript | Vitest + Testing Library | Playwright against the dev server |

2. **Write the test from the caller's view** (the **test-behavior-not-implementation** principle):
   the HTTP response, the use case's result, the row written, the rendered text. No mocks of your own
   adapters.
3. **Run it and watch it fail for the right reason.** A test that fails on a typo or setup error is
   not red yet. Paste the failure.
4. **Make the smallest change** that turns it green. No extra features.
5. **Run the whole suite** (`go test -race ./...`, `pytest`, `cargo test`, `vitest run`), then clean
   up with the suite green.
6. If you could not show red first (the bug needs production data, a race you can't trigger), say
   why and name the closest check you used instead (a replay, a property test, a log query).
