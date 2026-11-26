Job: RATE-00a: answer 429 over an API key's limit
Issue: https://github.com/<owner>/<repo>/issues/61
Difficulty: medium
Playbook: playbook-build, stage 3 (build in its own worktree as the accepted plan says, open the PR, hand it over)
Done when: the PR is open with green required checks, `make verify` passes on its head, and the handover check allows removing the worktree
Limits: only the issue's owned files; follow the accepted plan on issue 60; never merge; after the handover report, remove your worktree
Use only your own agents, if you need any; report only what you verified
When done or blocked, send an orchestration status to the return address: a first line such as DONE, BLOCKED, PR READY or REVIEW PASSED with the job ID, then the lines Ask, Did, Result, Caveats, Needs and From (your bot name and chat id)
Return to: bot:CEO (example), chat 5d4c3b2a-1111-2222-3333-444455556666
