Job: ORD-02: review PR 54, fix what you find, pass or stop it
Issue: https://github.com/<owner>/<repo>/issues/52
Difficulty: medium
Playbook: playbook-complete, step 5 (the reviewer fix loop; never merge)
Done when: a PASS or a Stopped on PR https://github.com/<owner>/<repo>/pull/54 at its head
Limits: check the gate and that the code is safe to run first; at most 3 rounds; fix only your findings in the owned files; never weaken a check; your PASS names every commit you pushed
Use only your own agents, if you need any; report only what you verified
When done or blocked, send an orchestration status to the return address: a first line such as DONE, BLOCKED, PR READY or REVIEW PASSED with the job ID, then the lines Ask, Did, Result, Caveats, Needs and From (your bot name and chat id)
Return to: bot:CTO (example), chat 3f2a9c10-1111-2222-3333-444455556666
