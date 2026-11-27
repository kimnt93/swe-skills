Merged by Developer (example) at 8b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c after checks.

playbook-solo: the agent that wrote the change checked it itself. This is a self-check, not an independent review, and
no reviewer verdict was posted. #72 closed, branch deleted, changelog entry merged with the PR.

## Gate
```text
make verify
  61 passed
security_scan.py --base origin/main --head 8b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c
  exit 0, no item; no outbound path added or widened
issue_gate.py pr 74
  merge rules: allowed
gh pr checks 74 --required
  all required checks passed
```

## Residual
- no independent review: nobody but the author read this change

Created: Developer (example)
