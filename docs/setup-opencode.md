# Setup D: opencode as the coding agent

opencode runs any provider you logged in to (`opencode providers login`); models are written `provider/model`
(`opencode models` lists them). It can be a coding agent in a workflow, a reviewer, or the project's manager.

## 1. Install the skills

```bash
make opencode          # skills copied to ~/.config/opencode/skills as swe (the entry) and swe-<skill>
```

opencode loads them with its skill tool: ask for the `swe` skill, or `swe-how`, `swe-why`, ... by name.

## 2. Pick the agents

```bash
cp cli/examples/config.opencode-only.yaml config.yaml      # every agent on opencode; edit the models
swe-cli models set developer --cli opencode --model anthropic/claude-sonnet-5 --reasoning medium
swe-cli models check                                       # every opencode model must be in `opencode models`
```

Reasoning is the model's **variant** (`high`, `max`, `minimal`, ...; provider-specific). Headless runs use
`opencode run --variant`; an interactive session sets the variant of opencode's `build` agent through
`OPENCODE_CONFIG_CONTENT`, which `swe-cli` sets for you. Leave `reasoning` empty for a model without variants.

## 3. How a session is started

`swe-cli flow` / `swe-cli delegate` start `opencode --model <provider/model> --auto` in a tmux session (or an Orca
terminal) inside the card's worktree, wait for the footer (`clis.opencode.ready`, `ctrl+p commands`), wait
`clis.opencode.settle` seconds, then type the brief. `--auto` approves every permission that is not denied: only the
worktree is at risk, so never point a session at a checkout with uncommitted work. `busy` is `esc interrupt`.
Headless one-shots (`swe-cli lane`) use `opencode run --model <id> --auto`.

## 4. Reviews

Reviews are a role, not another vendor: `reviewer-junior` and `reviewer-senior` in `config.yaml` run on whatever harness you set.

