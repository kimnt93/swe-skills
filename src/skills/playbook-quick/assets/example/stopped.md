Stopped by CTO (example). PR #54 at 4f2c9a1d8b7e6c5a4f3e2d1c0b9a8f7e6d5c4b3a.

Not merged: the merge rules refuse it. Nobody judged the code; this stop is about the issue, not the change.

## Blocking — issue #52 was closed as not planned while it was built
`issue_gate.py pr 54` refuses it: `#52 is refused: it is closed (not planned)`.

**Smallest fix:** none here; a person decides whether the work is wanted under a new issue.

## Gate
```text
python3 issue_gate.py pr 54 --repo <owner>/<repo>
  merge rules: NOT allowed
```

## Residual
- A person decides: reopen #52, replace it, or leave the PR. This PR stays open and its branch stays on GitHub.

Created: CTO (example)
