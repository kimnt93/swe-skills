# Example run

The owner asks the CTO bot to audit a service before partners get access. The names are examples.

| # | From → to | What happens | Message |
|---|---|---|---|
| 1 | CTO bot → reviewer bot | passes the target and the limits on; ends its turn | [handoff](../assets/example/reviewer-brief.md) |
| 2 | reviewer bot → its agent | briefs an agent on the `hard` row | [agent brief](../assets/example/agent-brief.md) |
| 3 | agent → reviewer bot | scans, lists the outbound paths, proves its findings locally, writes the report | `worker_done`, the [report](../assets/example/report.md) |
| 4 | reviewer bot → CTO bot | runs each proof again, then reports | [return report](../assets/example/return-report.md) |
| 5 | CTO bot → owner | runs the proofs, reports, and stops with nothing filed | findings, outbound paths, [an issue ready to file](../assets/example/issue-order-owner.md) |

## The auditor's commands

```bash
git fetch origin main
sha=$(git rev-parse origin/main)
git worktree add --detach <check dir> "$sha"
run=/home/example/audit-evidence/orders
mkdir -p "$run"                       # proofs, captures and the report: outside every repository
python3 -I <security-review skill>/scripts/security_scan.py --tree "$sha" --repo <check dir> > "$run/scan.txt"
git worktree remove <check dir>       # at the end
```

## When the target is a pull request

The scan takes `--base origin/main --head <sha>`, the findings say whether the pull request brings them in or they were
there before, and each outbound path's permission is read with `issue_gate.py asked <issue> --repo <owner>/<repo>
--pr <n>`. The audit posts nothing on the pull request. The CTO bot does not merge it while a finding it brings in
stands.

## When the code may not be run

A fork or an outside contributor: the auditor scans `gh pr diff <n>` and reads, runs nothing from the code, and the
report says so at the top of `Scope`. A finding then needs two quoted lines that settle it; the rest are open
questions under `Not checked`.
