# Task Brief Templates

Use these templates when formulating self-contained briefs for delegated CLI agents.

A delegate that commits or writes on an issue or PR also needs `Your author name: <agent name>` in its brief: it commits
under that name and signs with `Created: <agent name>` (the `github` skill).

---


These are for a **one-off delegation** where you land the change yourself. An agent that a bot runs in a playbook gets
the [agent brief](../../bot-orchestration/assets/agent-brief.template.md) instead, and commits.

## 1. Feature Implementation

```markdown
# TASK BRIEF: Table View Pagination

## Objective
Implement client-side and server-side pagination for TableView component, including page size selector, jump-to-page input, and next/prev buttons.

## Target Scope Files
- Modify: `src/components/TableView.tsx`
- Modify: `src/components/TableView.test.tsx`
- Modify: `src/api/types.ts`

## Reference Files for Conventions
- `src/components/CardBase.tsx`
- `src/theme/tokens.ts`

## Guardrails & Boundaries
- **NO COMMITS**: Do NOT run git commit or git push. Leave changes uncommitted.
- Restrict modifications strictly to the files listed above.
- Preserve existing styling and TypeScript interfaces.

## Verification Gate
Run and ensure this command passes:
`npm test`
```

---

## 2. Bug Fix

```markdown
# TASK BRIEF: Fix Concurrency Race in Cache Eviction

## Objective
Fix race condition where cache entries are read after invalidation has triggered but before eviction listener confirms removal.

## Target Scope Files
- Modify: `src/services/cache_manager.py`
- Modify: `tests/test_cache_manager.py`

## Boundaries & Constraints
- **NO COMMITS**: Keep changes uncommitted in working copy.
- Do not alter public method signatures of CacheManager.
- Add regression test reproducing the concurrent access pattern.

## Verification Gate
`pytest tests/test_cache_manager.py`
```

---

## 3. Refactoring & Optimization

```markdown
# TASK BRIEF: Optimize Database Query Latency

## Objective
Refactor feed aggregation query from sequential N+1 ORM fetches into a single batch query with proper indices.

## Target Scope Files
- Modify: `src/repositories/feed_repository.py`
- Modify: `schemas/0042_add_feed_index.sql`

## Boundaries & Constraints
- **NO COMMITS**: Do not commit.
- Preserve the exact API output contract for get_feed_for_user.

## Verification Gate
`make verify`
```
