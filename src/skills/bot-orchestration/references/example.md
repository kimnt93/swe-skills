# Example: CEO bot → developer bot → agents → PR → CEO bot

Two issues from one problem, both allowed by the merge rules. `CEO (example)` and `Developer (example)` are bots; A and B are agents the
developer bot starts. Project, numbers and names are made up.

| # | From → to | What | Message |
|---|---|---|---|
| 1 | CEO bot → developer bot | delegates issue #52, ends its turn | [delegate](../assets/example/delegate.md) |
| 2 | developer bot → agent A | rates it `medium`, creates the worktree, briefs a standard-tier agent; ends its turn | [agent brief](../assets/example/agent-brief.md) |
| 3 | agent A → developer bot | reports once | [agent report](../assets/example/agent-report.md) |
| 4 | developer bot | reruns the evidence command, reads the diff, checks the PR | |
| 5 | developer bot → CEO bot | status, ends its turn | [bot report](../assets/example/bot-report.md) |
| 6 | CEO bot | continues its playbook: hands the PR to the reviewer bot (`build`, the default), or checks the mechanical merge conditions and merges (`quick`) | |

A second issue, if independent, goes to **agent B** in its own worktree at step 2. A and B never hear of each other. If B
needs something A found, the developer bot reads A's report and writes it into B's brief.

```bash
# 1. CEO bot
ORCA bot chats                                   # its own chat id for 'Return to'
python3 <this skill>/scripts/message_lint.py delegate --body-file delegate.md
ORCA orchestration send --to "bot:<developer bot>" --chat new --type handoff --subject "ORD-02: local order times" --body-file delegate.md

# 2. developer bot
python3 <github skill>/scripts/issue_gate.py issue 52 --repo <owner>/<repo>
python3 <this skill>/scripts/message_lint.py agent-brief --body-file agent-brief.md
ORCA orchestration worker-start --spec-file agent-brief.md --agent <agent> --model <model> --effort <effort> \
    --worktree new-child --repo <repo> --name ord-02

# 4. developer bot, after the report woke it
python3 <this skill>/scripts/message_lint.py agent-report --body-file report-a.md
cd web && npm run check
gh pr checks 54 --repo <owner>/<repo>

# 5. developer bot
python3 <this skill>/scripts/message_lint.py bot-report --body-file report.md
ORCA orchestration send --to "bot:<CEO bot>" --chat <return chat id> --type status --subject "PR READY ORD-02" --body-file report.md
```

**Blocked** works the same way with `PR BLOCKED` or `BLOCKED`, the evidence in `Result` and the one thing needed in
`Needs`.
