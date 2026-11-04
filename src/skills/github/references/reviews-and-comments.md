# Reviews and comments

## Review a PR

1. Check out the head and record its SHA: `gh pr checkout <n> && git rev-parse HEAD`.
2. Run `make verify` yourself, then the **interrogate** skill on `git diff origin/main...HEAD`.
3. Check the submit rules (`pr_lint.py pr <n>`) and the architecture (`make verify` runs `archcheck` /
   `lint-imports`).
4. Verdict, in a body file whose first line is `Verdict: PASS at <sha>` or `Verdict: CHANGES at <sha>`,
   followed by the findings (command, output, expected) or "no verified findings":

```bash
gh pr review <n> --comment --body-file review.md
```

Agents run as the same GitHub account that opened the PR, and GitHub refuses `--approve` and
`--request-changes` on your own PR, so the verdict is a comment review; `swe-cli merge` enforces it
through the verified SHA. With a separate bot account, use `--approve` / `--request-changes` instead.
A verdict is for one SHA; a new push needs a new verdict.

## Comment

```bash
gh pr comment <n> --body-file note.md
gh issue comment <n> --body-file note.md
```

Inline comment on a line (from a JSON payload file, never interpolated text):

```bash
gh api repos/<owner>/<repo>/pulls/<n>/comments --method POST --input comment.json
# comment.json: {"body": "...", "commit_id": "<sha>", "path": "internal/orders/cancel.go", "line": 42, "side": "RIGHT"}
```

## Answer review threads

Verify each claim against the code. A real finding: fix it with a failing test first, push, then
reply with the commit. Noise: reply with the concrete reason it does not apply. Never change code
just to quiet a comment.

**Check after:** `gh pr view <n> --json reviewDecision,latestReviews` and `gh pr checks <n>`.
