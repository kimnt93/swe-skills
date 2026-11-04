# Recommended setup and usage

What to run, in what order, and what to keep switched off until it has earned trust.

## The setup

| Layer | Recommendation |
|---|---|
| coding agents | any of **Claude Code** ([setup A](setup-claude.md)), **oh-my-pi** ([setup B](setup-omp.md)) and **Codex** ([setup C](setup-codex.md)): a default CLI per project, another family reviewing on request. One CLI works too, with a weaker review. |
| plugin | built once, installed into every CLI you use: `make claude codex omp` |
| models | agents in the project's `models.yaml` (cli, model, reasoning): Opus / `gpt-6-sol` high for `developer-strong`, Sonnet / `gpt-6-sol` medium for `developer`, Haiku / Gemini Flash for `documenter`. Default every card to `developer`. |
| orchestration | one manager per project, any CLI agent started by `swe-cli orchestrate`; a project is a directory with its repo clones, and the manager starts the coding CLIs in worktrees (tmux, or Orca terminals) ([delegation.md](delegation.md), [architecture.md](architecture.md)). Hermes managers on a cheap non-Claude model are optional. |
| GitHub | `project/scripts/setup_repo.sh` per repo: squash only, protected `main`, required `verify` check, labels, PR and issue templates |
| proof | `make verify` in every repo (`/swe:verify-create`), required in CI |
| context | Claude 350k, every other model 245k (about the 272k price step), set once in the project's `models.yaml` and applied with `swe-cli context apply` and `swe-cli sync` ([context.md](context.md)) |
| logins | log in to each CLI once (`claude auth login`, `codex login`, `omp login`) and `gh auth login` |
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
5. **One project of agents.** Logins, `swe-cli models check`, `swe-cli project create <name>` then `swe-cli project <name> add <git url>`, `swe-cli orchestrate`. One
   card end to end; you merge. Then three cards with disjoint files, then about five.
6. **More projects.** `swe-cli project add` for each; one manager each.
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
| monthly | `claude update`; `swe-cli models check && swe-cli models apply` |

## Choosing models and CLIs

- **Claude subscription only** (setup A): simplest and cheapest to start; the reviewer shares the
  author's family, so keep autopilot off and read PRs yourself.
- **oh-my-pi only** (setup B): flexible providers; make the reviewer a different family from the author.
- **Both** (recommended): independent review for free; spread projects across the two CLIs so both quotas are used.
- Agent policy: `developer-strong` for money-path, cross-service design, races and bugs without a repro; `developer` by
  default; `documenter` only for deterministic work (lint, renames, dependency bumps, docs, scouting).

## Never

- Push to `main`, merge by hand, or use an admin override (`swe-cli merge` is the only path).
- Auto-merge money-path code (orders, fills, positions, balances, risk limits, P&L).
- Let a manager or the root edit a repository, or edit the central clone: agents work in worktrees.
- Run parallel cards on the same files: the manager refuses it for a reason.
- Run `bypassPermissions` or `--approval-mode yolo` outside a card's worktree.
- Put a model id in a skill: agent names only; ids live in the project's `models.yaml`.
