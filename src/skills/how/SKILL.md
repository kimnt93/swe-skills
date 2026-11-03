---
name: how
description: "Explain how a part of the codebase works, like a senior engineer onboarding onto it: the overview, key concepts, the request or data flow, where things live, and the gotchas, with file:line evidence. Use for 'how does X work', before changing an unfamiliar subsystem, and as the grounding step of architect and feature."
metadata:
  group: process
  summary: "Explain how a part of the codebase works, with file:line evidence"
---

# How

Read-only. Explain enough to build a working mental model, not a tour of every line.

1. **Size it.** One module or function: explain it yourself in one pass. A subsystem across files or
   services: start 2–4 read-only subagents (tier `low` or `mid`), one per angle, then merge.
2. **Follow the flow that matters for this stack:**
   - Go/Fiber API: route (the router file) → handler → use case → port → adapter → SQL / Redis / Kafka.
   - Kafka consumer: topic → decode → handler → transaction → offset commit.
   - Python ML: data source → loading (polars) → features → model → evaluation → artefact → serving.
   - Rust: public API → core types → hot loop → I/O edge; the PyO3 boundary if there is one.
   - Next.js: route segment (`app/.../page.tsx`, `layout.tsx`) → server vs client components → data
     fetching → API client; Vite + React: router → page → hooks (data, state) → components → API client.
3. **Write it** with these sections, dropping any that don't apply:
   - **Overview:** what it does and for whom, in 3–5 sentences.
   - **Key concepts:** the types and terms a reader must know.
   - **How it works:** the flow, step by step, each with `file:line`.
   - **Where things live:** a short map of directories and files.
   - **Gotchas:** surprises: hidden coupling, ordering rules, config that changes behaviour.
4. Say what you didn't trace.
