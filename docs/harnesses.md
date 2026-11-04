# Harnesses

The plugin installs into 55 agent harnesses with one command each: `make <harness>` (several at once:
`make claude codex omp`; everything found on the machine: `make install`; remove: add `REMOVE=1`).
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
| Pi | `make pi` | `~/.agents/skills` | `.agents/skills` |
| Warp | `make warp` | `~/.agents/skills` | `.agents/skills` |
| Zed | `make zed` | `~/.agents/skills` | `.agents/skills` |
| Kimi Code CLI | `make kimi-code-cli` | `~/.agents/skills` | `.agents/skills` |
| Antigravity CLI | `make antigravity-cli` | `~/.gemini/antigravity-cli/skills` | `.agents/skills` |
| IBM Bob | `make bob` | `~/.bob/skills` | `.bob/skills` |
| Cortex Code (Snowflake) | `make cortex` | `~/.snowflake/cortex/skills` | `.cortex/skills` |
| ForgeCode | `make forgecode` | `~/.forge/skills` | `.forge/skills` |
| Grok Build | `make grok` | `~/.grok/skills` | `.grok/skills` |
| Tabnine CLI | `make tabnine-cli` | `~/.tabnine/agent/skills` | `.tabnine/agent/skills` |
| Rovo Dev (Atlassian) | `make rovodev` | `~/.rovodev/skills` | `.rovodev/skills` |
| Zencoder | `make zencoder` | `~/.zencoder/skills` | `.zencoder/skills` |
| Command Code | `make command-code` | `~/.commandcode/skills` | `.commandcode/skills` |
| Lingma (Alibaba) | `make lingma` | `~/.lingma/skills` | `.lingma/skills` |
| Deep Agents | `make deepagents` | `~/.deepagents/agent/skills` | `.agents/skills` |
| Neovate | `make neovate` | `~/.neovate/skills` | `.neovate/skills` |
| Pochi | `make pochi` | `~/.pochi/skills` | `.pochi/skills` |
| Mux | `make mux` | `~/.mux/skills` | `.mux/skills` |
| AiderDesk | `make aider-desk` | `~/.aider-desk/skills` | `.aider-desk/skills` |
| Trae CN | `make trae-cn` | `~/.trae-cn/skills` | `.trae/skills` |
| Qoder CN | `make qoder-cn` | `~/.qoder-cn/skills` | `.qoder/skills` |
| Firebender | `make firebender` | `~/.firebender/skills` | `.agents/skills` |
| Kimchi | `make kimchi` | `~/.config/kimchi/harness/skills` | `.kimchi/skills` |
| AdaL | `make adal` | `~/.adal/skills` | `.adal/skills` |

Options for any target: `SCOPE=project PROJECT_DIR=~/code/app` (commit the skills with the repo),
`PREFIX=acme` (another prefix), `SKILLS="go-code py-code"` (a subset), `PLUGIN=no` (copy skills even for
Claude Code, Codex and omp), `DRY_RUN=1` (show what would happen). A harness that is not listed:
`make custom DIR=<its skills directory>`.

## Which harness does what

| Use | Harnesses |
|---|---|
| interactive coding with the skills | all of the above |
| a **delegated session** (unattended, started by `swe-cli flow` or `swe-cli delegate`) | Claude Code (`claude`), Codex (`codex`), oh-my-pi (`omp`) and opencode (`opencode`) |
| the **manager** of a project (`swe-cli orchestrate`, or the harness started in the project directory) | any of Claude Code, Codex, oh-my-pi, opencode |

The other harnesses use the same skills by hand; workflows drive the four coding CLIs above.
A new coding CLI needs a branch in `cli/bin/main` (`argv`) and an entry under `clis:` and
`agents:` in the project's `config.yaml`.

## Check an install

```bash
make status                    # what is installed, per detected harness
make claude DRY_RUN=1          # what a target would do
bash tests/harness_test.sh     # installs into all 55 harnesses in a scratch home
```
