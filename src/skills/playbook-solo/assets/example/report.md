Orders can be cancelled (parent #71, playbook-solo): 1 of 3 issues merged, 1 left open for a person, 1 waiting.

| Order | Issue | Pull request | State |
|---|---|---|---|
| 1 | #72 cancel route | https://github.com/<owner>/<repo>/pull/74 | merged at 8b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c on my self-check; #72 closed; worktree removed |
| 2 | #73 release the held balance | https://github.com/<owner>/<repo>/pull/75 | money path: open at 2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b; worktree kept |
| 3 | #76 cancel button | none | waiting: it depends on #73 |

**Every merge rests on my own self-check. There was no independent review, and no reviewer verdict was posted.** I
started no other agent or bot.

Needs: a person reviews and merges PR #75, because it changes balances; then #76 can be built.

Test kinds left out: none.

Choices I made: a second cancel of the same order answers `409`, the same as a filled one, because the order is no
longer open.

Parent #71 stays open.

Created: Developer (example)
