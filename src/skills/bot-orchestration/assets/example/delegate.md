Job: ORD-02: show order times in the local zone
Issue: https://github.com/<owner>/<repo>/issues/52
Difficulty: medium
Playbook: playbook-quick, step 3 (build, open the PR, send it back)
Done when: the PR is open with green checks and `cd web && npm run check` passes on its head
Limits: only the issue's owned files; do not merge
Use only your own agents, if you need any; report only what you verified
Delegating further: one child chat per receiving bot from this chat, opened with --chat new and this chat's subject (its title without the sender's name); every later message to that bot uses --chat with the recorded id
Agents: start each one on a row of the team's agent table, with its harness, model and reasoning effort; a missing row means stop and ask
When done or blocked, send an orchestration status to the return address: a first line such as DONE, BLOCKED, PR READY or REVIEW PASSED with the job ID, then the lines Ask, Did, Result, Caveats, Needs and From (your bot name and chat id)
Return to: bot:CEO (example), chat 3f2a9c10-1111-2222-3333-444455556666
