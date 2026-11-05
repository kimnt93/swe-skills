### Bug fix

**Reproduce first, fix at the root, prove it on the real surface.**

1. **Reproduce** with the cheapest real path, and write it as a failing test (the **tdd** skill):
   - Go: a table case in `*_test.go`, or an e2e test against the local compose infra (`go test -tags e2e`).
   - Python: a `pytest` case; for ML, a fixed-seed fixture that shows the wrong output.
   - Rust: a `#[test]` or a `proptest` case.
   - Frontend: a Vitest + Testing Library test, or a Playwright test against the dev server.
   Run it and see it fail for the reported reason.
2. **Find the root cause** (the **fix-root-causes** principle): bisect hypotheses with the evidence:
   `git log -p` / `git bisect`, logs in Loki, the trace in Tempo, the error in Sentry/GlitchTip.
3. **Plan the fix.** If it crosses a function boundary, run the **architect** skill first. Delegate
   the change to a subagent on the `developer` agent with the failing test as its target.
4. **Prove it:** the test passes, `make verify` passes, and the original symptom is gone on the
   real surface (the endpoint, the consumer, the page).
5. Add a guard only if the bad state is legitimate input; otherwise fix the producer.
6. **Docs:** if the fix changes documented behaviour, update `docs/` from the diff (the **docs-sync** skill, `follow` mode).
7. Run [opening-a-pr](opening-a-pr.md).

**Reply:** the root cause in one sentence, the failing-then-passing test, the verify tail.
