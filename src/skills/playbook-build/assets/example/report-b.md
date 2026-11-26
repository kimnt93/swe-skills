PR BLOCKED: RATE-00b, no PR
Ask: build issue 62 and open its PR
Did: one agent on the simple row changed deploy/compose.yaml; the issue's Done when fails, so I opened no PR and kept the worktree
Result: `docker compose -f deploy/compose.yaml config --quiet` exits 1: env file deploy/staging.env not found; the file is git-ignored and kept by the owner, so no worktree has it
Caveats: nothing was pushed or deployed
Needs: the owner gives a way to run the check without that file (for example a deploy/staging.env.example the issue owns), or changes the issue's Done when
From: bot:Devops (example), chat 9a8b7c6d-aaaa-bbbb-cccc-ddddeeeeffff
