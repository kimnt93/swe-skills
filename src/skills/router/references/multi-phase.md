### Multi-phase change

**A change too big for one PR becomes an ordered list of PRs, each landable and green on its own.**

1. If it fits in one or two reviewable PRs, skip this playbook.
2. Settle open questions first with [prototype](prototype.md) runs; keep the evidence.
3. Write the phase list as a checklist in the first PR (or a tracking issue). Per phase: the goal,
   the files or services it touches, the evidence that proves it (a command and its output), and
   what it must not break. Typical order:
   1. deletions and cleanup;
   2. types, ports, migrations (expand);
   3. behaviour behind the new shape;
   4. callers moved (backend, then frontend);
   5. the old path removed (contract).
4. Each phase is one PR through [opening-a-pr](opening-a-pr.md). A phase never depends on a later one.
5. In a `swe-cli` run, each phase is a card whose body carries the decisions every phase shares.

**Reply:** the phase list with the PR or card per phase and its state.
