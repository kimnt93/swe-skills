# Example: a pipeline on Claude Code and oh-my-pi

A project of agents with two harnesses: **Claude Code** plans and writes, **oh-my-pi (omp)** reviews, so the
reviewer is never the author's family. Everything is set in the project's `models.yaml` (the file here):

| Agent | cli | model | reasoning |
|---|---|---|---|
| manager, developer | claude | sonnet | high / medium |
| planner, developer-strong | claude | opus | high / xhigh |
| documenter, scribe, verifier | claude | haiku | – |
| reviewer (for Claude work) | omp | google-antigravity/gemini-3.8-flash | medium |

## Run it

```bash
make cli                                        # once: link swe-cli
bash examples/claude-omp-pipeline/run.sh ~/Documents/me https://github.com/kimnt93/swe-skills demo
```

The script is the whole pipeline in order:

```text
swe-cli project create demo                 # ./demo/ with AGENTS.md, workflows/, roles.yaml, models.yaml, project.yaml
swe-cli project demo add <git url>          # clone the repo into ./demo/<repo>; repeat for more repos
cp models.yaml demo/models.yaml             # claude builds, omp reviews
swe-cli models check                        # models exist, logins work
swe-cli flow validate demo                  # workflows are sound
swe-cli flow graph docs demo                # plan -> cards (write -> check -> review) -> report
swe-cli flow run demo docs --goal "..."     # one agent per node, each in its own worktree
```

## Talk to the manager instead

```bash
cd ~/Documents/me/demo && swe-cli orchestrate demo
```

Ask in plain words. A question ("how does X work", `/swe:how`) is answered by the manager itself with the skills.
A request to change code makes it pick a workflow (`docs`, `feature`, `bugfix`, ...) and start it with
`swe-cli flow run`, watch it, merge the PRs the report lists as ready, and clean up.

## Change an agent

```bash
swe-cli models set reviewer --cli omp --model google-antigravity/gemini-3.8-flash --reasoning high
swe-cli models show
```
