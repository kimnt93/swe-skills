Job: ORD-02: show order times in the local zone
Issue: https://github.com/<owner>/<repo>/issues/52
Difficulty: simple
Playbook: playbook-quick, steps 3, 4 and 7 (build in its own worktree, run the Done when, open the PR, keep the required checks green, send it back, clean up when told)
Done when: the PR is open with green checks and `cd web && npm run check` passes on its head
Limits: only the issue's owned files; never merge; nobody reviews the code, so the Done when passes on the head before the PR opens; keep the worktree until MERGED or STOPPED
Use only your own agents, if you need any; report only what you verified
When done or blocked, send an orchestration status to the return address: a first line such as DONE, BLOCKED, PR READY or REVIEW PASSED with the job ID, then the lines Ask, Did, Result, Caveats, Needs and From (your bot name and chat id)
Return to: bot:CTO (example), chat 3f2a9c10-1111-2222-3333-444455556666
