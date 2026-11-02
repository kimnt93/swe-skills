#!/usr/bin/env bash
# publish: release the built plugin into a publish repository, a git repo holding only dist/<name>/,
# so teammates install it with two commands and never need this source repo.
#
#   scripts/publish.sh            build, validate, sync, commit "release: <name> <version>", tag v<version>
#   scripts/publish.sh --push     also push main and the tag to the publish repo's origin
#   PUBLISH_DIR=~/src/swe-plugin scripts/publish.sh     (default: ~/src/<name>-plugin)
#
# Refuses when the publish repo has uncommitted changes, or when v<version> already exists with
# different content (bump PLUGIN_VERSION in plugin.env and add a CHANGELOG.md entry first).
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
push=no
[ "${1:-}" = "--push" ] && push=yes
name="$(cd "$root" && python3 -c 'import sys; sys.path.insert(0, "scripts"); import build; print(build.settings()["PLUGIN_NAME"])')"
python3 "$root/scripts/build.py" >/dev/null
python3 "$root/dist/$name/scripts/validate_skills.py" >/dev/null || { echo "publish: the build does not validate"; exit 1; }
version="$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["version"])' "$root/dist/$name/build.json")"
grep -q "^## $version" "$root/CHANGELOG.md" || { echo "publish: CHANGELOG.md has no '## $version' entry"; exit 1; }

dest="${PUBLISH_DIR:-$HOME/src/$name-plugin}"
if [ ! -d "$dest/.git" ]; then
  mkdir -p "$dest"
  git -C "$dest" init -q -b main
fi
[ -z "$(git -C "$dest" status --porcelain)" ] || { echo "publish: $dest has uncommitted changes"; exit 1; }

rsync -a --delete --exclude .git "$root/dist/$name/" "$dest/"
git -C "$dest" add -A
if git -C "$dest" diff --cached --quiet; then
  echo "publish: no change since the last release"
else
  if git -C "$dest" rev-parse -q --verify "refs/tags/v$version" >/dev/null; then
    git -C "$dest" reset -q --hard
    echo "publish: v$version is already released with different content: bump PLUGIN_VERSION in plugin.env"
    exit 1
  fi
  git -C "$dest" -c user.name="${GIT_AUTHOR_NAME:-$(git config user.name || echo release)}" \
    -c user.email="${GIT_AUTHOR_EMAIL:-$(git config user.email || echo release@localhost)}" \
    commit -q -m "release: $name $version"
fi
if ! git -C "$dest" rev-parse -q --verify "refs/tags/v$version" >/dev/null; then
  git -C "$dest" -c user.name="${GIT_AUTHOR_NAME:-$(git config user.name || echo release)}" \
    -c user.email="${GIT_AUTHOR_EMAIL:-$(git config user.email || echo release@localhost)}" \
    tag -a "v$version" -m "$name $version"
fi
echo "publish: $dest at v$version ($(git -C "$dest" rev-parse --short HEAD))"
echo "install: claude plugin marketplace add <owner>/<publish repo> && claude plugin install $name@$name-skills"
if [ "$push" = yes ]; then
  git -C "$dest" push -q origin main --follow-tags
  echo "publish: pushed main and v$version"
fi
