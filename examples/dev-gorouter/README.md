# dev-gorouter

A **developer** setup around the upstream repo `gorouter` (mode `dev`): you are the reviewer and the merger. The agent
reads or creates the issue, codes, opens the PR and stops. Built with:

```bash
swe-cli project create dev-gorouter --mode dev
swe-cli project dev-gorouter add https://github.com/kimnt93/gorouter     # a git submodule here
```

Differences from [pm-jlogger](../pm-jlogger/README.md): `mode: dev` in `config.yaml`; one workflow, `task`
(build -> checks, the fixer repairs a red check); no planner, no review node, no merge; `AGENTS.md` tells the agent to stop at an open PR.

```bash
cd ~/Documents/me/dev-gorouter
swe-cli flow run dev-gorouter task --goal "Add a .version file at the repo root with the latest release version in docs/release-notes-*.md"
```

Agents are the same as pm-jlogger (`config.yaml`); the task runs `developer-junior` (haiku, high). For a hard task add
`--input agent=developer-senior`.
