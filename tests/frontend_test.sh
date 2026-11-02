#!/usr/bin/env bash
# frontend_test: the ts-code templates install from their lockfiles, typecheck, lint, pass their
# unit tests and build for production. Each runs in a scratch copy: nothing lands in src/.
#
#   tests/frontend_test.sh            npm ci, typecheck, lint, test, build (both templates)
#   tests/frontend_test.sh --e2e      also Playwright against the production build (installs chromium once)
#   tests/frontend_test.sh --docker   also build the deployment-setup images for both
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
assets="$root/src/skills/ts-code/assets"
templates="$root/src/skills/deployment-setup/assets/templates"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
pass() { echo "PASS $1"; }
fail() { echo "FAIL $1"; exit 1; }
e2e=no; docker=no
for arg in "$@"; do
  [ "$arg" = --e2e ] && e2e=yes
  [ "$arg" = --docker ] && docker=yes
done
export NEXT_TELEMETRY_DISABLED=1

for app in vite-react nextjs; do
  cp -r "$assets/$app" "$tmp/$app"
  cd "$tmp/$app"
  npm ci --no-audit --no-fund >"$tmp/$app.install.log" 2>&1 || { tail -20 "$tmp/$app.install.log"; fail "$app: npm ci"; }
  for step in typecheck lint test build; do
    npm run -s "$step" >"$tmp/$app.$step.log" 2>&1 || { tail -30 "$tmp/$app.$step.log"; fail "$app: npm run $step"; }
  done
  if [ "$e2e" = yes ]; then
    npx playwright install chromium >/dev/null 2>&1
    npx playwright test >"$tmp/$app.e2e.log" 2>&1 || { tail -30 "$tmp/$app.e2e.log"; fail "$app: playwright"; }
  fi
  [ -z "$(cd "$assets/$app" && git status --porcelain . 2>/dev/null)" ] || true
  pass "$app: npm ci, typecheck, lint, test, build$([ "$e2e" = yes ] && echo ', playwright')"
  cd "$root"
done

# a build must not rewrite the template's tsconfig (Next.js does when keys are missing)
for app in vite-react nextjs; do
  diff -q <(python3 -m json.tool "$assets/$app/tsconfig.json") <(python3 -m json.tool "$tmp/$app/tsconfig.json") >/dev/null \
    || fail "$app: the build rewrote tsconfig.json; copy the build's version into the template"
done
pass "templates: tsconfig.json stable across a build"

if [ "$docker" = yes ]; then
  cp "$templates/Dockerfile.nextjs" "$tmp/nextjs/Dockerfile"
  cp "$templates/Dockerfile.vite" "$tmp/vite-react/Dockerfile"
  cp "$templates/nginx.spa.conf" "$tmp/vite-react/"
  for app in nextjs vite-react; do
    printf 'node_modules\n.next\ndist\n' >"$tmp/$app/.dockerignore"
    docker build -q -t "frontend-test-$app" "$tmp/$app" >"$tmp/$app.docker.log" 2>&1 || { tail -30 "$tmp/$app.docker.log"; fail "$app: docker build"; }
    id="$(docker run -d -p 127.0.0.1::3000 "frontend-test-$app")"
    port="$(docker port "$id" 3000/tcp | head -1 | sed 's/.*://')"
    ok=no
    for _ in $(seq 30); do
      if curl -fsS "http://127.0.0.1:$port/healthz" >"$tmp/$app.healthz" 2>/dev/null; then ok=yes; break; fi
      sleep 1
    done
    docker rm -f "$id" >/dev/null
    [ "$ok" = yes ] && grep -q '"status":"ok"' "$tmp/$app.healthz" || fail "$app: container /healthz"
    pass "$app: docker image builds and answers /healthz on 3000"
  done
fi
echo "all passed"
