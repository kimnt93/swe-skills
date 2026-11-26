# Status report

Per project, from live state (never from memory):

```bash
gh pr list --state open --json number,title,headRefName,reviewDecision,statusCheckRollup
gh pr list --state merged --search "merged:>=$(date -d '-7 days' +%F)" --json number,title
gh issue list --state open --json number,title,labels,milestone
ORCA worktree ps                       # who is working on what
ORCA orchestration worker-list         # workers that have not settled
```

Write it per the **ketchup** skill: one line on what waits on the human, then what merged, what is in
review, what is blocked and why, and the risks. Link every PR and issue.
