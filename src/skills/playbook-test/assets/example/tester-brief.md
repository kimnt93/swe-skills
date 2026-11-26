Job: SHOP-TEST: test the shop on staging before the release
Issue: none (the owner asked in chat: "check that a customer can get a price, use a code and download the report")
Difficulty: medium
Playbook: playbook-test, steps 2 to 5 (plan with expected results first, run, confirm each failure, short report)
Done when: every function has PASS, FAIL or NOT RUN with evidence, each failure was run twice, and the merged report.md is written outside every repository
Limits: test only https://shop.stg.example.test (staging) with the account in SHOP_TEST_USER and SHOP_TEST_PASSWORD; change no code; file no issue; nothing on production
Use only your own agents, if you need any; report only what you verified
Delegating further: one child chat per receiving bot from this chat, opened with --chat new and this chat's subject (its title without the sender's name); every later message to that bot uses --chat with the recorded id
Agents: start each one on a row of the team's agent table, with its harness, model and reasoning effort; a missing row means stop and ask
When done or blocked, send an orchestration status to the return address: a first line such as DONE, BLOCKED, PR READY or REVIEW PASSED with the job ID, then the lines Ask, Did, Result, Caveats, Needs and From (your bot name and chat id)
Return to: bot:CTO (example), chat 3f2a9c10-1111-2222-3333-444455556666
