Job: RATE-00a: review PR 64 against its issue and the accepted plan, fix what you find, pass or stop it
Issue: https://github.com/<owner>/<repo>/issues/61
Difficulty: medium
Playbook: playbook-build, stage 4 (the reviewer fix loop; never merge)
Done when: a PASS or a Stopped on PR https://github.com/<owner>/<repo>/pull/64 at its head
Limits: check the gate and that the code is safe to run first; check the code against plan v1 on issue 60 (packages, contract, owned files, verify commands), a departure is a finding; at most 3 rounds; fix only your findings in the owned files; never weaken a check; your PASS names every commit you pushed
Use only your own agents, if you need any; report only what you verified
Delegating further: one child chat per receiving bot from this chat, opened with --chat new and this chat's subject (its title without the sender's name); every later message to that bot uses --chat with the recorded id
Agents: start each one on a row of the team's agent table, with its harness, model and reasoning effort; a missing row means stop and ask
When done or blocked, send an orchestration status to the return address: a first line such as DONE, BLOCKED, PR READY or REVIEW PASSED with the job ID, then the lines Ask, Did, Result, Caveats, Needs and From (your bot name and chat id)
Return to: bot:CEO (example), chat 5d4c3b2a-1111-2222-3333-444455556666
