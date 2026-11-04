### Feature

**You own the design. Delegate the code. Prove it live.**

1. Pick the language with the router's "Which language" table, then load its skill.
2. Map the affected code with the **how** skill (entry points, data shapes, callers).
3. Run the **architect** skill: callers' usage, types and module shape before any logic.
4. Build inside out, per the language skill:
   - Go service: domain → application port → adapter (Postgres / Redis / Kafka / S3) → Fiber handler → wiring.
   - Python ML: data loading (polars) → features → model → evaluation → artefact (S3) → serving.
   - Rust: types → pure core → I/O at the edge; benches in `benches/` for anything on a hot path.
   - Frontend: the API client from OpenAPI → data hooks → components → page or route.
5. Order the work as verifiable units (the **sequence-verifiable-units** principle); one commit each.
   Independent slices (backend endpoint, frontend page) can go to parallel subagents on the `developer`
   agent, each in its own worktree, once the shared contract (the OpenAPI shape) is settled.
6. **Prove it on the real surface:** `make verify` (e2e + live probe for services; Playwright for
   frontends; an evaluation run with the metric for ML).
7. If the design is contested, run the **interrogate** skill. Then [opening-a-pr](opening-a-pr.md).

**Reply:** what you built, the decisions and why, the proof, open questions.
