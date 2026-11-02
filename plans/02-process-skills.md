# 02 — process-skills

status: done

## Goal

The process half of the plugin, forked from pstack@ae5650f into our format and adapted to our
harnesses, plus our own money-path proof.

## What exists

| Ours | From pstack | How |
|---|---|---|
| router (`/<plugin>`) + `models`, `harness`, the language table | `poteto-mode` | rewritten |
| router playbooks: investigation, bug-fix, feature, refactoring, multi-phase, perf-issue, profiling, hillclimb, incident, prototype, babysit, opening-a-pr, autonomous-run, session-pickup, pause-safely, figure-it-out, eval | playbooks of the same names (`multi-phase` from `multi-phase-plan`, `profiling` from `trace-forensics`, `incident` from `runtime-forensics`), `figure-it-out` | rewritten |
| router playbook `migration` | — | ours |
| `principles` (21) + `money-path` | `principle-*` | rewritten with Go/Python/Rust/TS forms, one skill with an index; `money-path` ours |
| `tdd`, `benchmark-checklist`, `correct`, `how`, `why` | same | rewritten |
| `deslop` | `no-comments` + `unslop` + `technical-writing` | merged, rewritten |
| `blast-radius`, `verify-create` (+ tested `verify.mk`), `verify-maintain`, `ketchup`, `architect` | same / `create-` and `maintain-verification-skill` | rewritten |
| `interrogate`, `reflect` | same | rewritten (no arena, no Cursor tools) |
| `formal-verify` (create + maintain references) | `create-` and `maintain-formal-verification-skill` | merged, rewritten |
| `replay-test` (+ `scripts/replay.py`, self-tested) | — | ours |
| subagents `worker`, `adversary` | the idea of `poteto-agent` | ours |

Not taken, on purpose:

| pstack | Why not |
|---|---|
| setup-pstack, poteto-help, automate-me | `fleet/models.yaml` and the router (with no request it prints the plugin) replace them |
| arena, swarm | the cross-lane review, Hermes swarm cards, and the fan-out inside `architect` and `interrogate` |
| autopilot-full, autopilot-stack, orchestrate, shipping | `fleet-manager`, `fleet-worker` and `fleet merge` |
| worktree-cleanup | `hermes worktree` and `git worktree prune` |
| authoring-a-skill | `AGENTS.md` + the `eval` playbook |
| visual-parity, make-bot-ui, ketchup-video, typescript-best-practices | UI-pixel and bot-specific; `ts-code` covers our TypeScript |
| recall, teach, sharpen, bro, show-me-your-work | conversational helpers; the decision trail lives in the harness reference |
| statechart | `formal-verify` keeps a Mermaid statechart next to a TLA+ model |
| principles experience-first, exhaust-the-design-space, outcome-oriented-execution | UI-product; "design it twice" is in `architect`; expand → contract is in `migration` |

## Verify

```bash
make validate
python3 src/skills/replay-test/scripts/replay.py --self-test
make upstream        # what changed upstream since the pin, for these files only
```

## Log

- 2026-11-02: waves 1–3 forked and adapted; validator extended so the adaptation rules hold.
