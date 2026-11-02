# Recommended setup and usage

What to run, in what order, and what to keep switched off until it has earned trust.

## The setup

| Layer | Recommendation |
|---|---|
| coding agents | **Claude Code on your Claude subscription** ([setup A](setup-claude.md)) **and oh-my-pi** ([setup B](setup-omp.md)): two lanes, each reviewing the other. One lane works too, with a weaker review. |
| plugin | built once, installed into both: `make claude omp` (add `codex`, `hermes` if you use them) |
| models | tiers in `fleet/models.yaml`: Opus / `gpt-6-sol` high for `top`, Sonnet / `gpt-6-sol` medium for `mid`, Haiku / Gemini Flash for `low`. Default every card to `mid`. |
| orchestration | Hermes: one root profile, one manager per project (Sonnet), shared lanes ([architecture.md](architecture.md)) |
| GitHub | `project/scripts/setup_repo.sh` per repo: squash only, protected `main`, required `verify` check, labels, PR and issue templates |
| proof | `make verify` in every repo (`/swe:verify-create`), required in CI |
| context | Claude 350k, every other model 245k (about the 272k price step), set once in `fleet/models.yaml` and applied with `fleet context apply` and `fleet sync` ([context-and-sync.md](context-and-sync.md)) |
| logins | log in on the Hermes `default` profile only; `/sync` shares the API keys and checks the rest |
| autopilot | off. Turn on `low` after 20 clean merges; never `money-path` |

## Order of work

1. **One repo, by hand.** `make claude`, then `/swe <task>` for a week on one real repo. Fix what
   the agent gets wrong by changing the repo, not the prompt: `/swe:correct`.
2. **Proof.** `/swe:verify-create`; seed three bugs and watch `make verify` fail on each; make the
   CI check required; `setup_repo.sh <owner>/<repo>`; add `ARCHITECTURE.md`.
3. **Second agent.** `make omp`; use `/skill:swe` on the same repo; compare. This is the review
   family for step 5.
4. **Enforce the rules.** Layering checks (`archcheck`, `lint-imports`), `structcheck`, ruff bans,
   `pr_lint.py` run in `make verify`; add one check for each mistake you correct twice.
5. **Fleet, one project.** Logins, `fleet models check`, `fleet bootstrap`, `fleet project add`. One
   card end to end; you merge. Then three cards across both lanes, then about ten.
6. **More projects.** `fleet project add` for each; one manager each.
7. **Autopilot.** Pin full model ids; after 20 clean merges set `autopilot.auto_merge: [low]`; sample
   merged PRs weekly; widen only after two clean weeks.

The step-by-step runbooks, with commands and exit checks, are in [runbooks.md](runbooks.md).

## Daily routine

| When | What |
|---|---|
| morning | `/swe:ketchup` (or ask the manager): what merged, what waits on you |
| a request comes | tell the root profile (or `/swe <task>` in the repo); money-path and design work get `top` |
| review | read the diff and the `Verification` section; the agents already ran `make verify` and the cross-review |
| merge | `merge <n>` to the manager (`--approved`), or autopilot for allowed risks |
| weekly | read 5–10 merged PRs; for each smell run `/swe:correct`; `/swe:reflect` after a long task |
| monthly | `make upstream` for pstack changes; `claude update`; `fleet models check && fleet models apply` |

## Choosing models and lanes

- **Claude subscription only** (setup A): simplest and cheapest to start; the reviewer shares the
  author's family, so keep autopilot off and read PRs yourself.
- **oh-my-pi only** (setup B): flexible providers; make the reviewer a different family from the author.
- **Both** (recommended): independent review for free; spread cards across lanes so both quotas are used.
- Tier policy: `top` for money-path, cross-service design, races and bugs without a repro; `mid` by default;
  `low` only for deterministic work (lint, renames, dependency bumps, docs, scouting).

## Never

- Push to `main`, merge by hand, or use an admin override (`fleet merge` is the only path).
- Auto-merge money-path code (orders, fills, positions, balances, risk limits, P&L).
- Let a manager or the root edit a repository.
- Run `bypassPermissions` or `--approval-mode yolo` outside a card's worktree.
- Put a model id in a skill: tiers only; ids live in `fleet/models.yaml`.
