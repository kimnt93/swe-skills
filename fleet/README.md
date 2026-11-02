# fleet

Runs the plugin's agents on Hermes Kanban. **Every agent, at every level, and the model it uses
is set in one file, `models.yaml`.** The `fleet` command reads it.

| Level | Agents | Writes code? | Default model |
|---|---|---|---|
| board | `root` (the `default` profile: fleet admin, router), one `pm-<project>` manager per project (`board.manager` template × `projects.yaml`) | no | root: Gemini 3.8 Flash; managers: Sonnet 5.5 |
| lanes | `claude`, `omp`: Hermes profiles that drive one coding CLI each, shared by every project | through the CLI | Gemini 3.8 Flash (it only runs `fleet lane`) |
| workers | the model a lane's CLI runs, per tier `top` / `mid` / `low` | yes | claude: opus / sonnet / haiku; omp: gpt-6-sol high / medium, Gemini 3.8 Flash |
| reviewers | who reviews work written in each lane, at which tier | no | Claude work → omp top; omp work → claude mid |
| subagents | `<plugin>:worker`, `<plugin>:adversary` shipped in the Claude Code plugin | yes / no | the claude lane's mid / top worker |
| omp roles | omp's own internal subagents | — | Gemini 3.8 Flash, gpt-6-sol |

`models.yaml` also holds the board settings (`kanban:`) and the autopilot switch
(`autopilot.auto_merge`, empty until you trust a risk class).

## The command

```bash
fleet models show                 # every agent, its level and its model
fleet models check                # each model exists where it runs, each provider is logged in
fleet models apply [--dry-run]    # push models.yaml to the Hermes profiles and to omp
fleet project add|list|sync         # one manager profile, board and Hermes project per project
fleet bootstrap                   # root, managers, lanes: tools, skills, board settings; then apply
fleet lane run <lane> <tier> <card> | fleet lane review <author-lane> <card>
fleet merge <pr> --risk <r> --sha <verified sha> [--approved]   # the merge gate
fleet name                        # the plugin name
```

`fleet merge` merges only when the PR is open, its head is the SHA the reviewer verified, and every
required check passed, and either the card's risk class is in `autopilot.auto_merge` (never
money-path) or the human approved (`--approved`, run by the project's manager). It refuses a PR with
no required checks. The design is in `docs/architecture.md`; the per-agent skills in
`docs/agents-and-skills.md`.

## Setup

```bash
ln -sf "$PWD"/fleet/bin/fleet ~/.local/bin/fleet
bash fleet/tests/selftest.sh --hermes   # fakes and a scratch Hermes home: nothing live is touched
omp login openai-codex                  # omp lane: GPT models through your Codex login
hermes auth add anthropic               # project managers
hermes auth add gemini                  # root + lane brains (or change their provider in models.yaml)
fleet models check                      # pick exact ids with `hermes model` and `omp models ls` if it complains
fleet bootstrap                         # root, lanes, board settings
fleet project add orders --repo ~/code/orders --github acme/orders --description "Orders API and dashboard"
fleet models check                      # 0 problems
hermes gateway restart
```

## A new model (say Opus 6)

```bash
claude update                                     # aliases opus/sonnet/haiku now mean the newest
$EDITOR fleet/models.yaml                         # only where you pin ids, or to move an agent
fleet models check && fleet models apply          # Hermes profiles and omp updated
make claude                                       # rebuild the plugin so its subagents follow
fleet models show
```

Workers and reviewers need no apply: `fleet lane` reads `models.yaml` on every card run.
