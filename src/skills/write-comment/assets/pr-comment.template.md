<headline: Verdict: PASS at <sha> | Verdict: FAIL at <sha> (in a fix loop add: . Round <k> of 3.) | Changes required by CTO (<name>). PR #<n> at <sha>. Round <k> of 3. | Returned by CTO (<name>). PR #<n> at <sha>. Return <k> of 3. (or: Rebase after #<m>.) | Stopped by <CTO or reviewer> (<name>). PR #<n> at <sha>. | Fixed in <sha>: | Merged by <who> at <sha> after PASS. (quick: after checks.)>

<1 or 2 sentences: what was checked (PR, branch, issue) and the result>

## Blocking — <finding title> <!-- on fail, needs code -->
<what is wrong, with the file and line, the command and what it showed, and what the issue requires>

**Smallest fix:** <the smallest change that resolves it>

## Verified <!-- on pass, needs code -->
1. **Scope & Diff:** `git diff origin/main...HEAD --stat` <the files touched; only owned files>
2. **<area: code, UI, security, tests, docs>:** <what was checked and what showed it>

## Security <!-- on verdict, needs code -->
- **Scan:** `security_scan.py --base origin/main --head <40-character sha>`: exit <0 or 1>; <each item: safe because, asked for by, or a finding under Blocking>
- **Outbound data:** <none added or widened, or one line per path: asked for by #<n>: <the destination in backticks> receives <data>; or: not asked for: <what> (a FAIL, under Blocking)>
- **Risk:** <no proven finding, or the findings under Blocking>
- **Not checked:** <what, or: none>

## Gate <!-- needs fence -->
```text
<command, run on the head above>
  <the tail of its output>
```

## Residual
- <non-blocking note or open follow-up, or: none>

Created: <author>
