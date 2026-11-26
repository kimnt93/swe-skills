# Repo setup

`scripts/setup_repo.sh <owner>/<repo> [--check verify-job-name] [--approvals N] [--dry-run]` applies, with `gh`:

| Setting | Value |
|---|---|
| merge methods | rebase only, so each commit keeps its agent's name on `main`; delete the branch on merge |
| `main` protection | PR required, the required status check (default `verify`), up-to-date branch, linear history, no force push, no deletion, admins included; approvals `--approvals` (default 0) |
| labels | from `assets/labels.json`: the `write-issue` catalog: types, lanes, difficulties, `risk:*`, `size:large`, `blocked` |

Then copy `assets/github/pull_request_template.md` and `assets/github/ISSUE_TEMPLATE/` into the
repo's `.github/`.

**Check after:** `gh api repos/<owner>/<repo>/branches/main/protection --jq '.required_status_checks.contexts'`
lists the check; `gh label list` shows the labels; `gh repo view --json squashMergeAllowed,mergeCommitAllowed,rebaseMergeAllowed,deleteBranchOnMerge`.

**Approvals.** Agents run as your `gh` account, and GitHub does not let an account approve its own PR,
so the default is 0 required approvals: the review by the other model family is enforced by
the playbook's check of one SHA (a PASS verdict or the CTO/CEO's acceptance), merged with `--match-head-commit` and recorded on the PR. When agents get their own
bot account (a fine-grained token with `contents`, `pull_requests` and `issues` write), rerun with
`--approvals 1` so GitHub enforces the review too.
