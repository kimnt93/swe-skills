# 06 — install-local

status: done · human: restart open sessions

## Goal

The plugin is installed for the owner: `/swe` works in Claude Code and omp, and the skills are in
Hermes.

## Steps

1. Check for an older plugin that uses the same marketplace or skill names:
   `claude plugin list`, `omp plugin list`, `ls ~/.hermes/skills`. Remove it from its own repo.
2. `make claude omp hermes`.
3. In a fresh session in any git repo: `/swe` prints the grouped skill table (Claude Code),
   `/skill:swe` (omp), `hermes skills list | grep swe` (Hermes).

## Verify

```bash
make status
claude plugin list | grep swe@swe-skills
(cd /tmp && claude -p --model haiku "/swe" | grep -c '/swe:')    # > 10
```

## Undo

`make claude codex omp hermes REMOVE=1`

## Notes

Claude Code, Codex and omp read the plugin from `dist/swe`: a `make build` updates them in place
(start a new session to see it), and a `make clean` breaks them until the next `make claude codex omp`.

## Log

- 2026-11-02: installed into Claude Code, Codex, omp (plugin `swe@swe-skills` 3.1.0) and Hermes
  (25 skills under `~/.hermes/skills/swe`). `/swe` in Claude Code lists 24 `/swe:<skill>` entries.
