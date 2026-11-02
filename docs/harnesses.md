# Harnesses

The plugin installs into 31 agent harnesses with one command each: `make <harness>` (several at once:
`make claude codex omp hermes`; everything found on the machine: `make install`; remove: add `REMOVE=1`).
Generated from the installer's table by `scripts/gen_docs.py`: do not edit by hand.

## Plugin harnesses

Claude Code, Codex and oh-my-pi install the plugin from `dist/swe` through their marketplace, so skills are
namespaced and the plugin updates in place on rebuild.

| Harness | Install | Router | Another skill | Extras |
|---|---|---|---|---|
| Claude Code | `make claude` | `/swe <task>` | `/swe:<skill>` | subagents `swe:worker`, `swe:adversary` |
| Codex | `make codex` | `$swe:swe <task>` | `$swe:<skill>` | |
| oh-my-pi | `make omp` | `/skill:swe <task>` | `/skill:<skill>` | omp's own subagent roles |

## Skill-directory harnesses

Every other harness reads a directory of `<skill>/SKILL.md` folders. The installer copies each skill as
`swe-<skill>` (the router keeps the name `swe`) and rewrites `name:` and the links between skills,
because the Agent Skills format needs `name` to equal the directory, with no colon. Agents load a skill by
its description, so a plain request finds the right one; name `swe` to start the router explicitly.

| Harness | Install | User skills directory | Project skills directory (`SCOPE=project`) |
|---|---|---|---|
| Devin for Terminal | `make devin` | `~/.config/devin/skills` | `.devin/skills` |
| OpenCode | `make opencode` | `~/.config/opencode/skills` | `.opencode/skills` |
| Hermes Agent | `make hermes` | `~/.hermes/skills/swe` | `.hermes/skills` |
| Universal (.agents: Amp, Cline, Warp, Zed, Pi, Replit, ...) | `make universal` | `~/.agents/skills` | `.agents/skills` |
| Amp | `make amp` | `~/.config/agents/skills` | `.agents/skills` |
| Gemini CLI | `make gemini-cli` | `~/.gemini/skills` | `.agents/skills` |
| Cursor | `make cursor` | `~/.cursor/skills` | `.agents/skills` |
| GitHub Copilot | `make github-copilot` | `~/.copilot/skills` | `.agents/skills` |
| Windsurf | `make windsurf` | `~/.codeium/windsurf/skills` | `.windsurf/skills` |
| Goose | `make goose` | `~/.config/goose/skills` | `.goose/skills` |
| Cline | `make cline` | `~/.agents/skills` | `.agents/skills` |
| Roo Code | `make roo` | `~/.roo/skills` | `.roo/skills` |
| Kilo Code | `make kilo` | `~/.kilo/skills` | `.agents/skills` |
| Droid (Factory) | `make droid` | `~/.factory/skills` | `.agents/skills` |
| Qwen Code | `make qwen-code` | `~/.qwen/skills` | `.qwen/skills` |
| Trae | `make trae` | `~/.trae/skills` | `.trae/skills` |
| Continue | `make continue` | `~/.continue/skills` | `.continue/skills` |
| Augment | `make augment` | `~/.augment/skills` | `.augment/skills` |
| Crush | `make crush` | `~/.config/crush/skills` | `.crush/skills` |
| Junie | `make junie` | `~/.junie/skills` | `.junie/skills` |
| Kiro CLI | `make kiro-cli` | `~/.kiro/skills` | `.kiro/skills` |
| OpenHands | `make openhands` | `~/.openhands/skills` | `.openhands/skills` |
| Mistral Vibe | `make mistral-vibe` | `~/.vibe/skills` | `.vibe/skills` |
| Antigravity | `make antigravity` | `~/.gemini/antigravity/skills` | `.agents/skills` |
| Qoder | `make qoder` | `~/.qoder/skills` | `.qoder/skills` |
| CodeBuddy | `make codebuddy` | `~/.codebuddy/skills` | `.codebuddy/skills` |
| iFlow CLI | `make iflow-cli` | `~/.iflow/skills` | `.iflow/skills` |
| OpenClaw | `make openclaw` | `~/.openclaw/skills` | `skills` |

Options for any target: `SCOPE=project PROJECT_DIR=~/code/app` (commit the skills with the repo),
`PREFIX=acme` (another prefix), `SKILLS="go-code py-code"` (a subset), `PLUGIN=no` (copy skills even for
Claude Code, Codex and omp), `DRY_RUN=1` (show what would happen). A harness that is not listed:
`make custom DIR=<its skills directory>`.

## Which harness does what

| Use | Harnesses |
|---|---|
| interactive coding with the skills | all of the above |
| a **fleet lane** (unattended, started by Hermes with `fleet lane`) | Claude Code (`claude`) and oh-my-pi (`omp`) |
| the **fleet's own agents** (root, project managers) | Hermes Agent (`make hermes` also copies the skills for its profiles) |

Codex and the other harnesses use the same skills by hand; the fleet drives only the two lane CLIs.
A new lane needs a `cli` branch in `fleet/bin/fleet` (`argv`) and an entry under `lanes:` and
`workers:` in `fleet/models.yaml`.

## Check an install

```bash
make status                    # what is installed, per detected harness
make claude DRY_RUN=1          # what a target would do
bash tests/harness_test.sh     # installs into all 31 harnesses in a scratch home
```
