#!/usr/bin/env bash
# setup_repo.sh <owner>/<repo> [--check <required check name>] [--approvals N] [--dry-run]
# --approvals defaults to 0: agents run as your own gh account, and GitHub does not let an account
# approve its own PR; the cross-family review is enforced by `swe-cli merge` instead. Use 1 once agents
# run as a separate bot account.
# Squash-only merges, delete branches on merge, a protected main with the required check, and the
# project labels (assets/labels.json). Idempotent. --self-test runs it against a fake gh.
set -euo pipefail

here="$(cd "$(dirname "$0")/.." && pwd)"
if [ "${1:-}" = "--self-test" ]; then
  tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
  printf '#!/usr/bin/env bash\necho "gh $*" >>"%s/calls"\nif [ "$1" = api ]; then cat >/dev/null; fi\n' "$tmp" >"$tmp/gh"
  chmod +x "$tmp/gh"
  PATH="$tmp:$PATH" "$0" acme/orders --check verify >/dev/null
  calls="$(cat "$tmp/calls")"
  grep -q "gh repo edit acme/orders --enable-squash-merge --enable-merge-commit=false --enable-rebase-merge=false --delete-branch-on-merge" <<<"$calls" || { echo "FAIL repo edit"; exit 1; }
  grep -q "gh api --method PUT repos/acme/orders/branches/main/protection --input -" <<<"$calls" || { echo "FAIL protection"; exit 1; }
  [ "$(grep -c '^gh label create' <<<"$calls")" = "$(python3 -c "import json;print(len(json.load(open('$here/assets/labels.json'))))")" ] || { echo "FAIL labels"; exit 1; }
  : >"$tmp/calls"; PATH="$tmp:$PATH" "$0" acme/orders --dry-run >/dev/null
  [ ! -s "$tmp/calls" ] || { echo "FAIL dry-run called gh"; exit 1; }
  echo "self-test passed: repo settings, branch protection, every label; dry-run calls nothing"
  exit 0
fi

repo="${1:?usage: setup_repo.sh <owner>/<repo> [--check <name>] [--approvals N] [--dry-run]}"
shift
check=verify; dry=no; approvals=0
while [ $# -gt 0 ]; do
  case "$1" in
    --check) check="$2"; shift 2 ;;
    --approvals) approvals="$2"; shift 2 ;;
    --dry-run) dry=yes; shift ;;
    *) echo "unknown option $1" >&2; exit 2 ;;
  esac
done
run() { if [ "$dry" = yes ]; then echo "would run: $*"; else "$@"; fi; }

run gh repo edit "$repo" --enable-squash-merge --enable-merge-commit=false --enable-rebase-merge=false --delete-branch-on-merge

protection="$(python3 - "$check" "$approvals" <<'PY'
import json, sys
print(json.dumps({
    "required_status_checks": {"strict": True, "contexts": [sys.argv[1]]},
    "enforce_admins": True,
    "required_pull_request_reviews": {"required_approving_review_count": int(sys.argv[2]), "dismiss_stale_reviews": True},
    "restrictions": None,
    "required_linear_history": True,
    "allow_force_pushes": False,
    "allow_deletions": False,
}))
PY
)"
if [ "$dry" = yes ]; then
  echo "would run: gh api --method PUT repos/$repo/branches/main/protection --input - <<< $protection"
else
  gh api --method PUT "repos/$repo/branches/main/protection" --input - <<<"$protection" >/dev/null
fi

python3 -c 'import json,sys; [print(l["name"], l["color"], l["description"], sep="\t") for l in json.load(open(sys.argv[1]))]' \
  "$here/assets/labels.json" | while IFS=$'\t' read -r name color description; do
  run gh label create "$name" --repo "$repo" --color "$color" --description "$description" --force
done
echo "done: $repo (squash only, protected main requiring '$check', labels)"
