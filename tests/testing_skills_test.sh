#!/usr/bin/env bash
# testing_skills_test: the two test runners, run for real against the fixture shop (tests/fixtures/web-app), which has
# functions that work, one that is broken, one that is slow and a dead button.
#
#   tests/testing_skills_test.sh                       API and command line (standard library; part of make test)
#   tests/testing_skills_test.sh --browser             also the web runner in a real browser: needs uv, ffmpeg and
#                                                      once: uv run --with playwright==1.65.0 playwright install chromium
#   tests/testing_skills_test.sh --browser --keep DIR  keep the evidence in DIR (empty, outside any repository)
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
fixture="$root/tests/fixtures/web-app"
skills="$root/src/skills"
tmp="$(mktemp -d)"
server=""
cleanup() { [ -z "$server" ] || kill "$server" 2>/dev/null || true; rm -rf "$tmp"; }
trap cleanup EXIT
pass() { echo "PASS $1"; }
fail() { echo "FAIL $1"; exit 1; }
export PYTHONDONTWRITEBYTECODE=1

browser=no
evidence="$tmp/evidence"
while [ $# -gt 0 ]; do
  case "$1" in
    --browser) browser=yes ;;
    --keep) [ $# -ge 2 ] || fail "--keep needs a directory"; evidence="$2"; shift ;;
    *) fail "unknown option $1" ;;
  esac
  shift
done
mkdir -p "$evidence"
evidence="$(cd "$evidence" && pwd)"
[ -z "$(ls -A "$evidence")" ] || fail "$evidence is not empty"

# throwaway credentials of the fixture, made for this run
export SHOP_PASSWORD="pw-$(python3 -c 'import secrets; print(secrets.token_hex(12))') &x"
export SHOP_TOKEN="tk-$(python3 -c 'import secrets; print(secrets.token_hex(12))')"
export SHOP_USER="ada.lovelace@example.com"

python3 "$fixture/app.py" --port-file "$tmp/port" --hits "$tmp/hits" >"$tmp/server.log" 2>&1 &
server=$!
python3 - "$tmp/port" <<'PY' || { cat "$tmp/server.log"; fail "the fixture shop did not start"; }
import sys, time
from pathlib import Path
for _ in range(100):
    if Path(sys.argv[1]).is_file() and Path(sys.argv[1]).read_text():
        sys.exit(0)
    time.sleep(0.1)
sys.exit(1)
PY
port="$(cat "$tmp/port")"
sed "s/PORT/$port/" "$fixture/api-cli-plan.json" >"$tmp/api-cli-plan.json"
cp "$fixture/shop_cli.py" "$tmp/"

verdicts() {  # <results.json> <id=VERDICT[:words of the reason]> ...
  python3 - "$@" <<'PY'
import json, sys
found = {f["id"]: f for f in json.load(open(sys.argv[1]))["functions"]}
wanted = {a.split("=")[0]: a.split("=", 1)[1] for a in sys.argv[2:]}
assert sorted(found) == sorted(wanted), (sorted(found), sorted(wanted))
for name, want in wanted.items():
    verdict, _, words = want.partition(":")
    item = found[name]
    why = item["reason"] + " " + " ".join(r for s in item["steps"] for r in s["reasons"])
    assert item["verdict"] == verdict and words in why, f"{name}: {item['verdict']} ({why}), wanted {want}"
PY
}

no_secret_in() {  # <dir>
  python3 - "$1" <<'PY'
import base64, os, sys
from pathlib import Path
from urllib.parse import quote, quote_plus
values = [os.environ["SHOP_PASSWORD"], os.environ["SHOP_TOKEN"]]
forms = [f.encode() for v in values for f in (v, quote(v, safe=""), quote_plus(v), base64.b64encode(v.encode()).decode())]
for path in Path(sys.argv[1]).rglob("*"):
    if path.is_file() and any(f in path.read_bytes() for f in forms):
        sys.exit(f"a secret is in {path}")
PY
}

# 1. API and command line
rc=0
python3 "$skills/api-cli-testing/scripts/io_test.py" "$tmp/api-cli-plan.json" --out "$evidence/api-cli" >"$tmp/io.log" 2>&1 || rc=$?
[ "$rc" = 1 ] || { cat "$tmp/io.log"; fail "io_test.py must exit 1 on the faulty fixture, got $rc"; }
verdicts "$evidence/api-cli/results.json" api-quote=PASS api-me=PASS "api-coupon=FAIL:wrong status: 500" "api-report=FAIL:slow:" \
  cli-total=PASS "cli-coupon=FAIL:price table is missing" "cli-report=FAIL:slow:" || { cat "$tmp/io.log"; fail "api/cli verdicts"; }
grep -q "## Bugs ready to file (4)" "$evidence/api-cli/report.md" || fail "api/cli report: four bugs"
no_secret_in "$evidence/api-cli" || fail "api/cli: a secret reached the evidence"
python3 "$skills/api-cli-testing/scripts/io_test.py" "$tmp/api-cli-plan.json" --out "$tmp/api-cli-2" >"$tmp/io-2.log" 2>&1 || true
python3 "$skills/web-testing/scripts/testkit.py" report --out "$tmp/twice.md" \
  "$evidence/api-cli/results.json" "$tmp/api-cli-2/results.json" >/dev/null || true
grep -q "3 passed, 4 failed, 0 not run" "$tmp/twice.md" && grep -q "## Bugs ready to file (4)" "$tmp/twice.md" \
  && grep -q "failed 2 of 2 runs" "$tmp/twice.md" || { cat "$tmp/twice.md"; fail "api/cli: two runs merge into one row and bug per function"; }
pass "api/cli: real requests and commands; the broken and slow ones fail, the working ones pass, the token stays out"

rc=0
python3 "$skills/api-cli-testing/scripts/io_test.py" "$tmp/api-cli-plan.json" --out "$root/evidence-must-not-exist" >"$tmp/in.log" 2>&1 || rc=$?
[ "$rc" = 2 ] && [ ! -e "$root/evidence-must-not-exist" ] && grep -q "outside any repository" "$tmp/in.log" \
  || { cat "$tmp/in.log"; fail "evidence inside a repository must be refused"; }
pass "safety: evidence inside a repository is refused"

sed 's/"environment": "local"/"environment": "production"/' "$tmp/api-cli-plan.json" >"$tmp/api-cli-prod.json"
: >"$tmp/hits"
python3 "$skills/api-cli-testing/scripts/io_test.py" "$tmp/api-cli-prod.json" --out "$tmp/io-prod" >"$tmp/prod.log" 2>&1 || true
verdicts "$tmp/io-prod/results.json" api-quote=PASS api-me=PASS "api-coupon=NOT RUN:explicit approval" "api-report=FAIL:slow:" \
  "cli-total=NOT RUN:runs a command" "cli-coupon=NOT RUN:runs a command" "cli-report=NOT RUN:runs a command" \
  || { cat "$tmp/prod.log"; fail "api production verdicts"; }
grep -q '^GET /api/quote' "$tmp/hits" && ! grep -qv '^GET ' "$tmp/hits" || { cat "$tmp/hits"; fail "production: a changing request reached the server"; }
pass "safety: on production no changing request reaches the server without approval (checked in the server's log)"

if [ "$browser" = no ]; then
  echo "SKIP web runner in a real browser: run with --browser"
  echo "all passed"
  exit 0
fi

# 2. the web runner in a real browser
command -v uv >/dev/null || fail "--browser needs uv"
command -v ffmpeg >/dev/null || fail "--browser needs ffmpeg"
web=(uv run --no-project "$skills/web-testing/scripts/web_test.py")
sed "s/PORT/$port/" "$fixture/web-plan.json" >"$tmp/web-plan.json"
: >"$tmp/hits"
rc=0
timeout 300 "${web[@]}" "$tmp/web-plan.json" --out "$evidence/web" >"$tmp/web.log" 2>&1 || rc=$?
[ "$rc" = 1 ] || { cat "$tmp/web.log"; fail "web_test.py must exit 1 on the faulty fixture, got $rc"; }
verdicts "$evidence/web/results.json" quote=PASS signin=PASS desk=PASS "coupon=FAIL:failed request: POST /api/coupon -> 500" \
  "report=FAIL:slow:" "newsletter=FAIL:no response" || { cat "$tmp/web.log"; fail "web verdicts"; }
grep -q "console error: coupon failed with status 500" "$evidence/web/report.md" || fail "web: the console error is missing"
grep -q "## Bugs ready to file (3)" "$evidence/web/report.md" || fail "web report: three bugs"
for hit in "GET /api/quote" "POST /api/coupon" "GET /api/report" "POST /api/signin" "WS subscribe" "WS hello"; do
  grep -qx "$hit" "$tmp/hits" || fail "web: the server never received $hit"
done
pass "web: real clicks and typing; broken, slow and dead functions fail, the working ones pass"

# the evidence itself: every screenshot is a PNG with a picture in it, every video decodes, every frame is named by time
python3 - "$evidence/web" <<'PY' || fail "web evidence"
import json, re, struct, subprocess, sys
from pathlib import Path
base = Path(sys.argv[1])

def png(path):
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", f"{path} is not a PNG"
    width, height = struct.unpack(">II", data[16:24])
    assert width >= 1280 and height >= 800 and len(data) > 5000, f"{path}: {width}x{height}, {len(data)} bytes"

def picture(path):
    """A hash of the decoded pixels."""
    run = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "md5", "-"], capture_output=True, text=True, check=True)
    return run.stdout

results = json.loads((base / "results.json").read_text())
clicks = {}
for function in results["functions"]:
    for step in function["steps"]:
        for name in step["evidence"]:
            assert (base / name).exists(), name
            if name.endswith(".png"):
                png(base / name)
        if step["action"] in ("click", "press"):
            video = base / function["id"] / f"{step['n']:02d}-{step['action']}.webm"
            run = subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", str(video), "-f", "null", "-"], capture_output=True, text=True)
            assert run.returncode == 0 and not run.stderr, (video, run.stderr)
            folder = video.with_name(video.stem + "-frames")
            frames = step["key_frames"]
            assert step["video"]["opens"] and len(frames) >= 3, (video, frames)
            for frame in frames:
                assert re.fullmatch(r"t\d{6}ms\.png", frame["file"])
                png(folder / frame["file"])
            assert len({picture(folder / f["file"]) for f in frames}) >= 2, f"{video}: the frames never change"
            assert (video.with_name(video.stem + ".analysis.md")).is_file()
            clicks[function["id"]] = (step, video)
assert sorted(clicks) == ["coupon", "desk", "newsletter", "quote", "report", "signin"], sorted(clicks)
# the slow one: the video covers the whole wait, and the answer is a frame about four seconds after the click
step, video = clicks["report"]
assert step["response_ms"] >= 4000 and step["video"]["duration_ms"] >= 4000, step["response_ms"]
assert any(3800 <= f["after_action_ms"] <= 4600 for f in step["key_frames"]), step["key_frames"]
assert step["requests"][0]["took_ms"] >= 3900
assert clicks["quote"][0]["video"]["duration_ms"] < 3000, "a quick answer makes a short video"
assert clicks["newsletter"][0]["requests"] == []
PY
no_secret_in "$evidence/web" || fail "web: a secret reached the evidence"
pass "web evidence: screenshots and videos open, frames are named by time and show the change, the password stays out"

sed 's/"environment": "local"/"environment": "production"/' "$tmp/web-plan.json" >"$tmp/web-prod.json"
: >"$tmp/hits"
timeout 300 "${web[@]}" "$tmp/web-prod.json" --out "$tmp/web-prod" >"$tmp/web-prod.log" 2>&1 || true
verdicts "$tmp/web-prod/results.json" quote=PASS "signin=NOT RUN:the test's own guard stopped POST /api/signin" \
  "coupon=NOT RUN:the test's own guard stopped POST /api/coupon" "report=FAIL:slow:" "newsletter=NOT RUN:uses 'Subscribe'" \
  "desk=NOT RUN:websocket message after an interaction" || { cat "$tmp/web-prod.log"; fail "web production verdicts"; }
grep -qx 'WS subscribe' "$tmp/hits" && grep -q '^GET /api/quote' "$tmp/hits" && ! grep -vx 'WS subscribe' "$tmp/hits" | grep -qv '^GET ' \
  || { cat "$tmp/hits"; fail "production: the browser sent a changing request or socket message"; }
pass "safety: in a real browser on production, the POST and the socket message are held and risky controls not clicked"

# a page that shows the password loses its evidence; a redirect off the allowed hosts is not tested
cat >"$tmp/edge-plan.json" <<EOF
{"environment": "local", "target": "http://127.0.0.1:$port/", "functions": [
  {"id": "reveal", "name": "Show the password", "steps": [
    {"action": "goto", "url": "/", "expect": {"text": "Signed out"}},
    {"action": "type", "on": {"label": "Password"}, "secret": "SHOP_PASSWORD"},
    {"action": "click", "on": {"role": "button", "name": "Show password"}, "expect": {"gone": "no such text"}}]},
  {"id": "away", "name": "A redirect elsewhere", "steps": [
    {"action": "goto", "url": "/away", "expect": {"text": "anything"}, "timeout_ms": 3000}]}]}
EOF
timeout 200 "${web[@]}" "$tmp/edge-plan.json" --out "$tmp/web-edge" >"$tmp/web-edge.log" 2>&1 || true
verdicts "$tmp/web-edge/results.json" "reveal=FAIL:showed a secret" "away=NOT RUN:left the allowed hosts" \
  || { cat "$tmp/web-edge.log"; fail "web edge verdicts"; }
[ -z "$(find "$tmp/web-edge/reveal" -name '03-click.png' -o -name '03-click.webm' -o -name '03-click-frames')" ] \
  || fail "evidence of a step that showed a secret must be deleted"
no_secret_in "$tmp/web-edge" || fail "web edge: a secret reached the evidence"
pass "safety: a step that shows the password keeps no screenshot or video; a redirect elsewhere is not a result"

# as playbook-test does it: run every failure again, then one report from all runs, one row and one bug per function
python3 - "$tmp/web-plan.json" "$tmp/web-failed.json" <<'PY'
import json, sys
plan = json.load(open(sys.argv[1]))
plan["functions"] = [f for f in plan["functions"] if f["id"] in ("coupon", "report", "newsletter")]
json.dump(plan, open(sys.argv[2], "w"))
PY
timeout 300 "${web[@]}" "$tmp/web-failed.json" --out "$evidence/web-2" >"$tmp/web-2.log" 2>&1 || true
verdicts "$evidence/web-2/results.json" coupon=FAIL report=FAIL newsletter=FAIL || { cat "$tmp/web-2.log"; fail "web second run"; }
python3 "$skills/web-testing/scripts/testkit.py" report --out "$evidence/report.md" \
  "$evidence/web/results.json" "$evidence/web-2/results.json" "$evidence/api-cli/results.json" >/dev/null || true
grep -q "6 passed, 7 failed, 0 not run" "$evidence/report.md" && grep -q "## Bugs ready to file (7)" "$evidence/report.md" \
  && [ "$(grep -c "^How often: failed 2 of 2 runs" "$evidence/report.md")" = 3 ] || { cat "$evidence/report.md"; fail "the combined report"; }
pass "report: failures run again; one short report with one row and one bug per function"
[ "$evidence" = "$tmp/evidence" ] || echo "evidence kept in $evidence"
echo "all passed"
