# Agent table

Held by the CTO/CEO. This file is the empty template: each team copies it **outside any public repository**
(`agent_table.py init`), fills every cell and keeps that copy as the **only** place that sets harness, model and
reasoning effort. Every brief and handoff takes them from it.

- **Harness:** the Orca agent id (`orca orchestration worker-start --help` says what `--agent` takes).
- **Model:** the model id that harness takes, as `--model`.
- **Reasoning effort:** the value for `--effort`, or `none` when the team sets none for that harness.

Rows may name the same harness and model. A row that is missing or not filled means **stop and ask**.

| Role or difficulty | Harness | Model | Reasoning effort |
|---|---|---|---|
| simple | <harness> | <model> | <effort> |
| medium | <harness> | <model> | <effort> |
| hard | <harness> | <model> | <effort> |
| planner/architect | <harness> | <model> | <effort> |
