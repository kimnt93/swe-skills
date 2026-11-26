Job: AUDIT-ORDERS: security audit of the orders service at main
Issue: none (the owner asked in chat: "check the orders service for leaks and holes before we open it to partners")
Difficulty: hard
Playbook: playbook-security, steps 2 to 5 (clean checkout, scan and outbound inventory, topics and proofs, report)
Done when: a report outside every repository with each finding proven by a command, every outbound path listed with the issue that asks for it, issues ready to file and what was not checked
Limits: audit https://github.com/<owner>/<repo> at its current main head; change no code; post and file nothing; proofs on your machine only with made-up data; no deployed host, real account or key
Use only your own agents, if you need any; report only what you verified
Delegating further: one child chat per receiving bot from this chat, opened with --chat new and this chat's subject (its title without the sender's name); every later message to that bot uses --chat with the recorded id
Agents: start each one on a row of the team's agent table, with its harness, model and reasoning effort; a missing row means stop and ask
When done or blocked, send an orchestration status to the return address: a first line such as DONE, BLOCKED, PR READY or REVIEW PASSED with the job ID, then the lines Ask, Did, Result, Caveats, Needs and From (your bot name and chat id)
Return to: bot:CTO (example), chat 3f2a9c10-1111-2222-3333-444455556666
