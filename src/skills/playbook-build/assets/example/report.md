RATE-00 (#60): built under playbook-build.

| Package | Issue | Builder | Pull request | State |
|---|---|---|---|---|
| RATE-00a | #61 | developer bot | https://github.com/<owner>/<repo>/pull/64 | merged at 5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b after the reviewer's PASS; #61 closed |
| RATE-00c | #63 | developer bot | https://github.com/<owner>/<repo>/pull/66 | merged at 0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c after the reviewer's PASS; #63 closed |
| RATE-00b | #62 | devops bot | none | blocked |

Checked only by the reviewer who pushed them: 5a6b7c8 (PR #64).

Blocked, RATE-00b: `docker compose -f deploy/compose.yaml config --quiet` needs deploy/staging.env, which is git-ignored and kept by you. Needs: a way to run the check without that file (for example a deploy/staging.env.example the issue owns), or a different Done when. The devops bot keeps its worktree.

#60 stays open until RATE-00b is merged; then its Done when runs on main and it is closed.
