#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["playwright==1.65.0"]
# ///
"""Test a web app as a user does: a real browser, real clicks and keystrokes, and evidence for every step.

    uv run web_test.py <plan.json> --out <empty dir outside any repository> [--approve <function>/<step> ...]
    uv run --with playwright==1.65.0 playwright install chromium     once per machine
    python3 web_test.py --self-test                                  the rules and the video tools; no browser

Each step records its input, the expected result and the observed output, with a screenshot. Each click (also press,
check and select) records a video from the action until the answer arrived, key frames named by their time, and an
analysis: timing, console errors, failed requests, a slow or missing answer. The plan: references/plan.md. How a
step is judged: references/analysis.md. The safety rules: references/safety.md. Needs ffmpeg.
Exit 0 = every function passed, 1 = something failed or did not run, 2 = usage or refused.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urljoin, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.dont_write_bytecode = True
import testkit as K  # noqa: E402  the module beside this file

CLICKS = ("click", "press", "check", "select")  # the actions a user waits on: each gets a video
ACTIONS = ("goto", "type", "fill", "expect") + CLICKS
LOCATORS = ("role", "label", "placeholder", "text", "testid", "css")
STEP_KEYS = ("action", "on", "url", "value", "secret", "env", "key", "expect", "expected", "effect", "max_ms",
             "timeout_ms", "dialog", "ignore_requests", "ignore_console")
EXPECT_KEYS = ("text", "gone", "url_contains", "value", "status", "request", "in")
CONDITIONS = ("text", "gone", "url_contains", "value", "status")
BUDGET_MS = {"goto": 5000}
DEFAULT_BUDGET_MS, DEFAULT_TIMEOUT_MS, QUIET_MS, TAIL_MS, MAX_FRAMES = 2000, 10000, 400, 500, 10
VIEWPORT = {"width": 1280, "height": 800}
OUTSIDE, GUARD = "outside the allowed hosts", "production guard"
HELD_FRAME = "production guard: a websocket message after an interaction, in a step without approval"


# ---------------------------------------------------------------------------------------------------- the plan

def check_web_plan(plan: dict) -> None:
    K.check_plan(plan)
    if not K.host_of(plan.get("target", "")):
        raise K.Refused("target is the http(s) URL of the app under test")
    for function in plan["functions"]:
        for number, step in enumerate(function["steps"], 1):
            where = f"{function['id']}/{number}"
            K.only_keys(where, step, STEP_KEYS)
            action = step.get("action")
            if action not in ACTIONS:
                raise K.Refused(f"{where}: action is one of {', '.join(ACTIONS)}")
            if action in ("click", "type", "fill", "check", "select"):
                on = step.get("on")
                if not isinstance(on, dict) or sum(k in on for k in LOCATORS) != 1:
                    raise K.Refused(f"{where}: 'on' names the control by exactly one of {', '.join(LOCATORS)}")
            if "on" in step:
                K.only_keys(f"{where} on", step["on"], LOCATORS + ("name", "exact"))
            if action == "goto" and not isinstance(step.get("url"), str):
                raise K.Refused(f"{where}: goto needs a url")
            if action == "type" and re.search(r"[\r\n]", str(step.get("value", ""))):
                raise K.Refused(f"{where}: a new line typed is the Enter key: make it a 'press' step, which is checked")
            if action == "press" and not step.get("key"):
                raise K.Refused(f"{where}: press needs a key")
            sources = [k for k in ("value", "secret", "env") if k in step]
            if action in ("type", "fill", "select") and len(sources) != 1:
                raise K.Refused(f"{where}: {action} takes exactly one of value, secret, env")
            if action == "select" and sources != ["value"]:
                raise K.Refused(f"{where}: select takes a value")
            expect = step.get("expect", {})
            K.only_keys(f"{where} expect", expect, EXPECT_KEYS)
            if action not in ("type", "fill") and not any(k in expect for k in CONDITIONS):
                raise K.Refused(f"{where}: 'expect' says what a user sees ({', '.join(CONDITIONS)}): a step with no"
                                " expected result tests nothing. Write it before you run")
            if any(not str(expect[k]) for k in CONDITIONS if k in expect):
                raise K.Refused(f"{where}: an empty expectation is always true")
            if "request" in expect and "status" not in expect:
                raise K.Refused(f"{where}: expect.request goes with expect.status")
            if step.get("dialog", "dismiss") not in ("accept", "dismiss"):
                raise K.Refused(f"{where}: dialog is accept or dismiss")
            if plan["environment"] == "production" and step.get("dialog") == "accept" and step.get("effect", "read") == "read":
                raise K.Refused(f"{where}: accepting a dialog on production is not a read: declare its effect")
            for key in ("ignore_requests", "ignore_console"):
                if not all(isinstance(x, str) and len(x) >= 4 for x in step.get(key, [])):
                    raise K.Refused(f"{where}: {key} is a list of texts of at least 4 characters")


def describe_target(on: dict) -> str:
    kind = next(k for k in LOCATORS if k in on)
    name = f' "{on["name"]}"' if on.get("name") else ""
    return f"{on[kind]}{name}" if kind == "role" else f'{kind} "{on[kind]}"'


def describe_input(step: dict) -> str:
    action = step["action"]
    where = describe_target(step["on"]) if "on" in step else ""
    if "secret" in step or "env" in step:
        shown = f"<secret:{step.get('secret') or step.get('env')}>"
    else:
        shown = json.dumps(step.get("value", ""), ensure_ascii=False)
    return {"goto": f"open {step.get('url')}", "click": f"click {where}", "check": f"tick {where}",
            "type": f"type {shown} into {where}", "fill": f"fill {where} with {shown}",
            "select": f"choose {shown} in {where}", "press": f"press {step.get('key')}" + (f" in {where}" if where else ""),
            "expect": "wait and look"}[action]


def describe_expected(step: dict) -> str:
    expect = step.get("expect", {})
    scope = f" in {expect['in']}" if "in" in expect else ""
    parts = []
    if "text" in expect:
        parts.append(f'the text "{expect["text"]}" appears{scope}')
    if "gone" in expect:
        parts.append(f'the text "{expect["gone"]}" disappears{scope}')
    if "url_contains" in expect:
        parts.append(f'the address contains "{expect["url_contains"]}"')
    if "value" in expect:
        parts.append(f'the field holds "{expect["value"]}"')
    if "status" in expect:
        parts.append(f"the request {expect.get('request', '')} answers {expect['status']}".replace("  ", " "))
    if not parts:
        parts.append("the field holds what was entered")
    text = "; ".join(parts)
    if step["action"] in CLICKS + ("goto", "expect"):
        text += f", within {step.get('max_ms', BUDGET_MS.get(step['action'], DEFAULT_BUDGET_MS))} ms"
    return f"{step['expected']} ({text})" if step.get("expected") else text


# ---------------------------------------------------------------------------------------------------- the rules

def guard_reason(url: str, method: str, resource: str, allowed: set, environment: str, effect: str,
                 approved: bool) -> str:
    """Why the browser may not send this request, or ''. Pages may load assets from elsewhere, and nothing else."""
    if urlsplit(url).scheme in ("data", "blob", "about"):
        return ""
    if K.host_of(url) not in allowed and (resource == "document" or method.upper() not in K.SAFE_METHODS):
        return OUTSIDE
    if not K.may_send(environment, method, effect, approved):
        return GUARD
    return ""


def may_send_frame(environment: str, interacted: bool, effect: str, approved: bool) -> bool:
    """On production a page may open and subscribe; once the test has clicked, a socket sends only in an approved step."""
    return environment != "production" or not interacted or (effect != "read" and approved)


def resource_of(request) -> str:
    """'document' only for the page itself going somewhere; a frame inside it is loaded like any other asset."""
    if request.resource_type != "document":
        return request.resource_type
    try:
        return "subframe" if request.frame.parent_frame else "document"
    except Exception:  # a new window's first request has no frame yet: it is a page going somewhere
        return "document"


def left_for(requests: list, page_url: str, allowed: set) -> str:
    """The address outside the allowed hosts that the page itself went to (a redirect is not asked first), or ''."""
    for url in [r["url"] for r in requests if r["type"] == "document" and not r.get("blocked")] + [page_url]:
        if urlsplit(url).scheme in ("http", "https") and K.host_of(url) not in allowed:
            return url
    return ""


def ignored(text: str, patterns: list) -> bool:
    return any(p in text for p in patterns)


def short_request(item: dict) -> str:
    parts = urlsplit(item["url"])
    return f"{item['method']} {parts.path or '/'}" + (f"?{parts.query}" if parts.query else "")


def analyze(facts: dict) -> tuple:
    """(verdict, reasons) of one step from what the browser saw. Pure: the self-test feeds it every failure."""
    step, expect = facts["step"], facts["step"].get("expect", {})
    skip_requests = step.get("ignore_requests", [])
    requests = [r for r in facts["requests"]
                if not r["url"].endswith("/favicon.ico") and not ignored(r["url"], skip_requests)]
    wanted_status, wanted_url = expect.get("status"), expect.get("request", "")

    def asked_for(item: dict) -> bool:
        return wanted_status is not None and item.get("status") == wanted_status and wanted_url in item["url"]

    def stopped(items: list) -> list:
        return list(dict.fromkeys(f"the test's own guard stopped {short_request(r)} ({r['blocked']}): this step was"
                                  " not tested" for r in items))

    held = [r for r in requests if r.get("blocked") and (r["blocked"] == GUARD or r["type"] == "document")]
    if held:
        return K.NOT_RUN, stopped(held)
    if facts.get("left_host"):
        return K.NOT_RUN, [f"the page left the allowed hosts for {facts['left_host']}: nothing there was tested. If the"
                           " request covers that host, add it to allow_hosts"]
    reasons = []
    if facts.get("error"):
        reasons.append(facts["error"])
    if facts.get("leaked"):
        reasons.append("the page showed a secret in clear text: this step's screenshot and video were deleted")
    if facts.get("already"):
        reasons.append("the expected result was there before the action, so seeing it proves nothing")
    clicked = step["action"] in CLICKS
    if not facts.get("error") and not facts.get("met"):
        if clicked and not requests and not facts.get("changed"):
            reasons.append(f"no response: the {step['action']} sent no request and changed nothing in"
                           f" {facts['timeout_ms']} ms")
        else:
            reasons.append(f"expected result not seen in {facts['timeout_ms']} ms; observed:"
                           f" {K.clip(' '.join(facts['observed'].split()), 160)}")
    for item in requests:
        if item.get("pending"):
            reasons.append(f"missing response: {short_request(item)} still unanswered after {facts['timeout_ms']} ms")
        elif (item.get("status") or 0) >= 400 and not asked_for(item):
            reasons.append(f"failed request: {short_request(item)} -> {item['status']}")
        elif item.get("failure") and "ERR_ABORTED" not in item["failure"] and not item.get("blocked"):
            reasons.append(f"failed request: {short_request(item)} -> {item['failure']}")
    expected_urls = [r["url"] for r in facts["requests"] if asked_for(r) or r.get("blocked")
                     or r["url"].endswith("/favicon.ico") or ignored(r["url"], skip_requests)]
    for entry in facts["console"]:
        if entry.get("url") in expected_urls and entry["text"].startswith("Failed to load resource"):
            continue
        if not ignored(entry["text"], step.get("ignore_console", [])):
            reasons.append(f"console error: {K.clip(' '.join(entry['text'].split()), 160)}")
    response_ms = facts.get("response_ms")
    if facts.get("met") and response_ms is not None and response_ms > facts["budget_ms"]:
        reasons.append(f"slow: answered in {response_ms} ms, the budget is {facts['budget_ms']} ms")
    other = [r for r in requests if r.get("blocked")]  # elsewhere, or a socket message: harmless if the step passed
    if reasons and other:  # a failure the guard may have caused is never reported as the app's bug
        return K.NOT_RUN, stopped(other) + reasons
    return (K.FAIL if reasons else K.PASS), reasons


def new_lines(before: str, after: str) -> str:
    seen = {}
    for line in before.splitlines():
        seen[line.strip()] = seen.get(line.strip(), 0) + 1
    fresh = []
    for line in (x.strip() for x in after.splitlines()):
        if seen.get(line, 0):
            seen[line] -= 1
        elif line:
            fresh.append(line)
    return "\n".join(fresh)


# ---------------------------------------------------------------------------------------------------- the video

def ffmpeg(*args: str) -> str:
    run = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", *args], capture_output=True, text=True, timeout=180)
    if run.returncode:
        raise ValueError(f"ffmpeg failed: {run.stderr.strip().splitlines()[-1] if run.stderr.strip() else run.returncode}")
    return run.stderr


def frame_times(path: Path, changed_only: bool = False) -> list:
    """The time in ms of every frame, decoding the whole file (so this also proves the video opens)."""
    chain = "mpdecimate,showinfo" if changed_only else "showinfo"
    log = ffmpeg("-i", str(path), "-vf", chain, "-f", "null", "-")
    return [round(float(x) * 1000) for x in re.findall(r"\[Parsed_showinfo[^\n]*pts_time:\s*([0-9.]+)", log)]


def trim(path: Path, keep_ms: int) -> None:
    """The recorder pads still frames after the stop: the video ends where the recording did."""
    short = path.with_name(f"{path.stem}.trim{path.suffix}")
    ffmpeg("-y", "-i", str(path), "-t", f"{keep_ms / 1000:.3f}", "-c", "copy", str(short))
    short.replace(path)


def pick(times: list, changed: list, wanted: list, limit: int = MAX_FRAMES) -> list:
    """Frame numbers to keep: the first, the last, the frame at each wanted time, then frames where the picture changed."""
    if not times:
        return []

    def at(ms: int) -> int:
        return next((i for i, t in enumerate(times) if t >= ms), len(times) - 1)

    must = {0, len(times) - 1, *(at(ms) for ms in wanted)}
    other = [i for i in sorted({at(ms) for ms in changed}) if i not in must]
    room = max(limit - len(must), 0)
    if len(other) > room:
        other = [other[round(k * (len(other) - 1) / max(room - 1, 1))] for k in range(room)]
    return sorted(must | set(other))


def key_frames(video: Path, folder: Path, click_ms: int, wanted: list) -> tuple:
    """(video facts, frames). A frame's file name is its time in the video; each says how long after the action it is."""
    times = frame_times(video)
    if not times:
        raise ValueError("the video has no frames")
    chosen = pick(times, frame_times(video, changed_only=True), wanted)
    folder.mkdir(exist_ok=True)
    expression = "+".join(f"eq(n\\,{i})" for i in chosen)
    ffmpeg("-i", str(video), "-vf", f"select='{expression}'", "-fps_mode", "passthrough", str(folder / "raw-%03d.png"))
    raw = sorted(folder.glob("raw-*.png"))
    if len(raw) != len(chosen):
        raise ValueError(f"extracted {len(raw)} frames, wanted {len(chosen)}")
    frames = []
    for source, index in zip(raw, chosen):
        target = folder / f"t{times[index]:06d}ms.png"
        source.rename(target)
        frames.append({"file": target.name, "video_ms": times[index], "after_action_ms": times[index] - click_ms})
    facts = {"frames": len(times), "duration_ms": times[-1], "action_at_ms": click_ms, "opens": True}
    (folder / "frames.json").write_text(json.dumps({"video": video.name, **facts, "key_frames": frames}, indent=2) + "\n")
    return facts, frames


def analysis_page(title: str, outcome: dict, timeline: list, video: dict, frames: list, stem: str) -> str:
    lines = [f"# {title}", "", f"Verdict: **{outcome['verdict']}**", ""]
    lines += [f"- {K.one_line(r, 300)}" for r in outcome["reasons"]] or ["- every expected result seen, in budget"]
    lines += ["", "## Timeline (ms after the action)", "", "| ms | What happened |", "|---|---|"]
    lines += [f"| {ms} | {K.one_line(text)} |" for ms, text in sorted(timeline)]
    if video:
        lines += ["", "## Video", "", f"`{stem}.webm`: opens, {video['frames']} frames, {video['duration_ms']} ms;"
                  f" the action is at {video['action_at_ms']} ms.", "", "## Key frames (open them; no video player needed)",
                  "", "| File | In the video | After the action |", "|---|---|---|"]
        lines += [f"| `{stem}-frames/{f['file']}` | {f['video_ms']} ms | {f['after_action_ms']} ms |" for f in frames]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------------------------------- the browser

class Watch:
    """Everything the browser sends and says, with the time of each, and the guard on every request."""

    def __init__(self, context, allowed: set, environment: str):
        self.allowed, self.environment = allowed, environment
        self.effect, self.approved, self.dialog = "read", False, "dismiss"
        self.requests, self.console, self.dialogs, self.seen = [], [], [], {}
        self.interacted = False
        self.touched = time.monotonic()
        context.route("**/*", self.route)
        context.route_web_socket(lambda url: True, self.socket)
        context.on("request", self.record)
        context.on("response", lambda r: self.update(r.request, status=r.status))
        context.on("requestfinished", lambda r: self.update(r, end=time.monotonic(), measured=r.timing["responseEnd"]))
        context.on("requestfailed", lambda r: self.update(r, end=time.monotonic(), failure=r.failure or "failed"))
        context.on("console", self.said)
        context.on("weberror", lambda e: self.console.append(
            {"at": time.monotonic(), "text": f"uncaught: {e.error}", "url": ""}))
        context.on("dialog", self.answer)

    def record(self, request) -> dict:
        if request not in self.seen:
            self.touched = time.monotonic()
            self.seen[request] = {"method": request.method, "url": request.url, "type": resource_of(request),
                                  "start": self.touched}
            self.requests.append(self.seen[request])
        return self.seen[request]

    def update(self, request, **facts) -> None:
        self.touched = time.monotonic()
        self.record(request).update(facts)

    def route(self, route) -> None:
        request = route.request
        why = guard_reason(request.url, request.method, resource_of(request), self.allowed, self.environment,
                           self.effect, self.approved)
        if why:
            self.record(request)["blocked"] = why
            route.abort("blockedbyclient")
        else:
            route.continue_()

    def held(self, url: str, method: str, why: str) -> None:
        self.requests.append({"method": method, "url": url, "type": "websocket", "start": time.monotonic(),
                              "blocked": why})

    def socket(self, page_side) -> None:
        if K.host_of(page_side.url) not in self.allowed:
            self.held(page_side.url, "SOCKET", OUTSIDE)
            page_side.close()
            return
        server = page_side.connect_to_server()
        if self.environment != "production":
            return

        def forward(message) -> None:
            if may_send_frame(self.environment, self.interacted, self.effect, self.approved):
                server.send(message)
            else:
                self.held(page_side.url, "SEND", HELD_FRAME)

        page_side.on_message(forward)

    def said(self, message) -> None:
        if message.type == "error":
            self.console.append({"at": time.monotonic(), "text": message.text,
                                 "url": (message.location or {}).get("url", "")})

    def answer(self, dialog) -> None:
        self.dialogs.append(f"{dialog.type} \"{dialog.message}\": {self.dialog}ed")
        dialog.accept() if self.dialog == "accept" else dialog.dismiss()


def locate(page, on: dict):
    exact = {"exact": True} if on.get("exact") else {}
    if "role" in on:
        return page.get_by_role(on["role"], **({"name": on["name"]} if "name" in on else {}), **exact)
    if "css" in on:
        return page.locator(on["css"])
    if "testid" in on:
        return page.get_by_test_id(on["testid"])
    kind = next(k for k in ("label", "placeholder", "text") if k in on)
    return getattr(page, f"get_by_{kind}")(on[kind], **exact)


def control_words(page, step: dict, control) -> str:
    """What the control says it does: the words the production gate reads before anything is clicked."""
    words = [step.get("url", ""), (step.get("on") or {}).get("name", ""), (step.get("on") or {}).get("text", "")]
    script = ("e => [e.innerText, e.value, e.getAttribute('aria-label'), e.title, e.id, e.name, e.getAttribute('class'),"
              " e.getAttribute('href'), e.form && e.form.getAttribute('action'),"
              " e.form && Array.from(e.form.querySelectorAll('[type=submit],button')).map(b => b.innerText).join(' ')]"
              ".filter(x => typeof x === 'string' && x !== '').join(' ')")
    if step["action"] in ("click", "check", "select") and control is not None:
        words.append(control.evaluate(script))
    if step["action"] == "press":
        target = control if control is not None else page.locator("*:focus")
        if target.count():
            words.append(target.first.evaluate(script))
    return " ".join(words)


def body_text(page) -> str:
    try:
        return page.evaluate("() => document.body ? document.body.innerText : ''")
    except Exception:  # the page is between two documents
        return ""


def scope_text(page, expect: dict) -> str:
    if "in" not in expect:
        return body_text(page)
    try:
        found = page.locator(expect["in"])
        return "\n".join(found.all_inner_texts()) if found.count() else ""
    except Exception:
        return ""


def empty_scope(page, selector: str) -> str:
    try:
        found = page.locator(selector).count()
    except Exception:
        found = 0
    return f"({selector} is {'empty' if found else 'not on the page'})"


def field_value(control) -> str:
    try:
        return control.input_value(timeout=500)
    except Exception:
        return ""


def conditions_met(page, step: dict, control, requests: list) -> bool:
    expect = step.get("expect", {})
    checks = []
    if "text" in expect:
        checks.append(str(expect["text"]) in scope_text(page, expect))
    if "gone" in expect:
        checks.append(bool(body_text(page)) and str(expect["gone"]) not in scope_text(page, expect))
    if "url_contains" in expect:
        checks.append(str(expect["url_contains"]) in page.url)
    if "value" in expect:
        target = page.locator(expect["in"]).first if "in" in expect else control
        checks.append(target is not None and field_value(target) == str(expect["value"]))
    if "status" in expect:
        checks.append(any(r.get("status") == expect["status"] and expect.get("request", "") in r["url"]
                          for r in requests))
    return all(checks)


def secret_on_screen(page, secrets: K.Secrets) -> bool:
    if not secrets.hidden:
        return False
    try:
        shown = page.evaluate("() => [document.body ? document.body.innerText : '', ...Array.from("
                              "document.querySelectorAll('input:not([type=password]),textarea'), e => e.value)].join('\\n')")
    except Exception:
        return False
    return secrets.shows(shown, hidden_only=True) or secrets.shows(page.url, hidden_only=True)


class Runner:
    def __init__(self, browser, plan: dict, out: Path, approved: set, secrets: K.Secrets):
        self.browser, self.plan, self.out, self.approved, self.secrets = browser, plan, out, approved, secrets
        self.allowed = K.allowed_hosts(plan)

    def function(self, function: dict) -> dict:
        context = self.browser.new_context(viewport=VIEWPORT, service_workers="block", accept_downloads=False)
        watch = Watch(context, self.allowed, self.plan["environment"])
        page = context.new_page()
        (self.out / function["id"]).mkdir()
        results = []
        try:
            for number, step in enumerate(function["steps"], 1):
                if results and results[-1]["verdict"] != K.PASS:
                    results.append(K.skipped_step(number, describe_input(step), describe_expected(step),
                                                  f"step {results[-1]['n']} did not pass"))
                    continue
                try:
                    results.append(self.step(page, watch, function["id"], number, step))
                except K.Refused as why:
                    results.append(K.skipped_step(number, describe_input(step), describe_expected(step), str(why)))
        finally:
            context.close()
        return K.function_result(function, results)

    def step(self, page, watch: Watch, function: str, number: int, step: dict) -> dict:
        action, expect = step["action"], step.get("expect", {})
        ref, effect = f"{function}/{number}", step.get("effect", "read")
        budget = step.get("max_ms", BUDGET_MS.get(action, DEFAULT_BUDGET_MS))
        timeout = step.get("timeout_ms", max(DEFAULT_TIMEOUT_MS, budget * 2))
        stem = f"{number:02d}-{action}"
        folder = self.out / function
        control, error = None, ""
        if "on" in step:
            control = locate(page, step["on"])
            try:
                control.wait_for(state="visible", timeout=5000)
                control.scroll_into_view_if_needed(timeout=2000)
            except Exception as problem:
                many = "strict mode violation" in str(problem)
                error = ("ambiguous: more than one control matches " if many else "control not found or not visible: ") \
                    + describe_target(step["on"])
                control = None
        refusal = K.production_gate(self.plan["environment"], ref, effect, self.approved,
                                    control_words(page, step, control)) if not error else ""
        if refusal:
            raise K.Refused(refusal)

        value = step.get("value", "")
        if not error and action in ("type", "fill"):
            is_password = control.evaluate("e => (e.getAttribute('type') || '').toLowerCase() === 'password'")
            if is_password and "secret" not in step:
                raise K.Refused(f"{ref}: a password comes from the environment: use \"secret\": \"<variable name>\"")
            if "secret" in step and not is_password:
                raise K.Refused(f"{ref}: a secret is typed only into a password field, or it would show in the video;"
                                " for an account name use \"env\"")
            if "secret" in step or "env" in step:
                value = self.secrets.get(step.get("secret") or step.get("env"), hidden="secret" in step)

        before = body_text(page)
        already = (not error and action in CLICKS and "status" not in expect
                   and conditions_met(page, step, control, []))
        recording = action in CLICKS and not error
        video_path = folder / f"{stem}.webm"
        watch.effect, watch.approved, watch.dialog = effect, ref in self.approved, step.get("dialog", "dismiss")
        watch.interacted = watch.interacted or action in CLICKS
        first_request, first_console, first_dialog = len(watch.requests), len(watch.console), len(watch.dialogs)
        if recording:
            page.screencast.start(path=str(video_path), size=VIEWPORT)
        recording_since = time.monotonic()
        if recording:
            page.wait_for_timeout(300)  # a first picture of the page as it was before the action
        started = time.monotonic()
        met_at, leaked, changed = None, False, False

        if not error:
            try:
                self.act(page, step, control, value, timeout)
            except Exception as problem:
                error = f"the {action} could not be done: {str(problem).splitlines()[0]}"
        acted = time.monotonic()  # the time limit starts here: typing a long value is not waiting
        if not error:
            wait_for_answer = action not in ("type", "fill")
            while True:
                page.wait_for_timeout(50)
                moment = time.monotonic()
                mine = watch.requests[first_request:]
                leaked = leaked or secret_on_screen(page, self.secrets)
                changed = changed or (bool(body_text(page)) and body_text(page) != before)
                if action in ("type", "fill") and "expect" not in step:
                    met = field_value(control) == value
                else:
                    met = conditions_met(page, step, control, mine)
                met_at = (met_at or moment) if met else None
                waiting = [r for r in mine if "end" not in r and not r.get("blocked")
                           and r["type"] not in ("websocket", "eventsource")
                           and not ignored(r["url"], step.get("ignore_requests", []))]
                quiet = (moment - watch.touched) * 1000 >= QUIET_MS or not wait_for_answer
                settled = met_at and (moment - met_at) * 1000 >= (QUIET_MS if wait_for_answer else 0)
                if (settled and quiet and not waiting) or (moment - acted) * 1000 >= timeout:
                    break
        finished = time.monotonic()
        if recording:
            page.wait_for_timeout(TAIL_MS)
            leaked = leaked or secret_on_screen(page, self.secrets)
            recorded_ms = round((time.monotonic() - recording_since) * 1000)
            page.screencast.stop()
        watch.effect, watch.approved, watch.dialog = "read", False, "dismiss"

        def after(moment: float) -> int:
            return max(round((moment - started) * 1000), 0)

        requests, timeline = [], [(0, describe_input(step))]
        for item in watch.requests[first_request:]:
            entry = {k: item.get(k) for k in ("method", "url", "type", "status", "failure", "blocked")}
            entry["sent_ms"] = after(item["start"])
            measured = item.get("measured", -1)  # the browser's own time; the runner's when it has none
            entry["took_ms"] = None if "end" not in item else round(
                measured if measured >= 0 else (item["end"] - item["start"]) * 1000)
            entry["pending"] = ("end" not in item and not item.get("blocked")
                                and item["type"] not in ("websocket", "eventsource"))
            requests.append(entry)
            timeline.append((entry["sent_ms"], f"request {short_request(item)}"))
            if "end" in item:
                outcome = item.get("blocked") or item.get("failure") or item.get("status")
                timeline.append((after(item["end"]), f"answer {outcome} to {short_request(item)} ({entry['took_ms']} ms)"))
            elif entry["pending"]:
                timeline.append((after(finished), f"still no answer to {short_request(item)}"))
        console = [{"at_ms": after(c["at"]), "text": self.secrets.redact(c["text"]), "url": c["url"]}
                   for c in watch.console[first_console:]]
        timeline += [(c["at_ms"], f"console error: {c['text']}") for c in console]
        timeline += [(after(finished), f"dialog {d}") for d in watch.dialogs[first_dialog:]]

        response_ms = None
        if met_at:
            ends = [r["end"] for r in watch.requests[first_request:]
                    if "end" in r and not ignored(r["url"], step.get("ignore_requests", []))
                    and not r["url"].endswith("/favicon.ico") and r["start"] <= met_at]
            if action not in ("type", "fill"):
                response_ms = after(max([met_at, *ends]))
            timeline.append((after(met_at), "the expected result is there"))
        elif not error:
            timeline.append((after(finished), "gave up: the expected result never came"))

        if "in" in expect:
            observed = scope_text(page, expect) or empty_scope(page, expect["in"])
        elif action in ("type", "fill") and control is not None:
            observed = f"the field holds \"{field_value(control)}\""
        elif action == "goto" and not error:
            observed = f"page \"{page.title()}\" at {page.url}: {body_text(page)}"
        else:
            observed = new_lines(before, body_text(page)) or "(no new text on the page)"
        if watch.dialogs[first_dialog:]:
            observed += "\ndialog " + "; ".join(watch.dialogs[first_dialog:])
        observed = K.clip(self.secrets.redact(observed.strip()))  # redact first: a cut could split a secret
        left = left_for(requests, page.url, self.allowed)

        verdict, reasons = analyze({
            "step": step, "met": bool(met_at), "already": already, "changed": changed, "requests": requests,
            "console": console, "observed": observed, "response_ms": response_ms, "budget_ms": budget,
            "timeout_ms": timeout, "leaked": leaked, "error": error, "left_host": left})

        evidence, video, frames = [], {}, []
        if leaked:
            video_path.unlink(missing_ok=True)
        else:
            shot = folder / f"{stem}.png"
            try:
                page.screenshot(path=str(shot), full_page=verdict != K.PASS)
                evidence.append(f"{function}/{shot.name}")
            except Exception as problem:
                reasons.append(f"evidence: no screenshot ({str(problem).splitlines()[0]})")
                verdict = K.NOT_RUN if verdict == K.PASS else verdict
        if recording and not leaked:
            try:
                trim(video_path, recorded_ms)
                action_at = round((started - recording_since) * 1000)
                video, frames = key_frames(video_path, folder / f"{stem}-frames", action_at,
                                           [action_at + (response_ms if response_ms is not None else after(finished))])
                evidence += [f"{function}/{video_path.name}", f"{function}/{stem}-frames"]
            except (ValueError, OSError, subprocess.TimeoutExpired) as problem:
                reasons.append(f"evidence: the video could not be checked ({problem})")
                verdict = K.NOT_RUN if verdict == K.PASS else verdict

        result = {"n": number, "action": action, "input": describe_input(step), "expected": describe_expected(step),
                  "observed": observed, "verdict": verdict, "reasons": reasons, "budget_ms": budget,
                  "response_ms": response_ms, "requests": requests, "console_errors": console, "video": video,
                  "key_frames": frames}
        if action in CLICKS:
            page_text = analysis_page(f"{ref}: {describe_input(step)}", self.secrets.redact(result),
                                      self.secrets.redact([list(t) for t in timeline]), video, frames, stem)
            (folder / f"{stem}.analysis.md").write_text(self.secrets.redact(page_text), encoding="utf-8")
            evidence.append(f"{function}/{stem}.analysis.md")
        result["evidence"] = evidence
        return result

    def act(self, page, step: dict, control, value: str, timeout: int) -> None:
        action = step["action"]
        if action == "goto":
            url = urljoin(self.plan["target"], step["url"])
            if K.host_of(url) not in self.allowed:
                raise ValueError(f"{url} is outside the allowed hosts")
            page.goto(url, wait_until="commit", timeout=timeout)
        elif action == "click":
            control.click(timeout=5000)
        elif action == "check":
            control.check(timeout=5000)
        elif action == "select":
            control.select_option(value, timeout=5000)
        elif action == "press":
            if control is not None:
                control.press(step["key"], timeout=5000)
            else:
                page.keyboard.press(step["key"])
        elif action == "fill":
            control.fill(value, timeout=5000)
        elif action == "type":  # real keystrokes, one at a time, as a person types
            control.click(timeout=5000)
            control.press("ControlOrMeta+a")
            control.press("Delete")
            control.press_sequentially(value, delay=40, timeout=max(timeout, 60 * len(value) + 5000))


def run(plan_path: str, out: str, approve: list) -> int:
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    check_web_plan(plan)
    approved = K.check_approvals(plan, approve)
    secrets = K.Secrets()
    for function in plan["functions"]:  # a missing credential stops the run before a browser opens
        for step in function["steps"]:
            if "secret" in step or "env" in step:
                secrets.get(step.get("secret") or step.get("env"), hidden="secret" in step)
    if not shutil.which("ffmpeg"):
        raise K.Refused("ffmpeg is not on the PATH: without it no video can be checked")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise K.Refused("Playwright is not installed: run this script with 'uv run', which reads its dependency")
    folder = K.evidence_dir(out)
    results = {"kind": "web", "target": plan["target"], "environment": plan["environment"], "started": K.now(),
               "approved": sorted(approved), "functions": []}
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch()
        except Exception as problem:
            raise K.Refused(f"the browser did not start ({str(problem).splitlines()[0]}); install it once with:"
                            " uv run --with playwright==1.65.0 playwright install chromium")
        results["browser"] = f"chromium {browser.version}"
        runner = Runner(browser, plan, folder, approved, secrets)
        for function in plan["functions"]:
            try:
                results["functions"].append(runner.function(function))
            except Exception as problem:  # a crash of the run is never a pass, and the other functions still run
                crash = K.skipped_step(1, "the run", "no crash", f"the run broke: {str(problem).splitlines()[0]}")
                results["functions"].append(K.function_result(function, [crash]))
        browser.close()
    code = K.write_results(folder, results, secrets)
    K.print_summary(folder, folder / "results.json")
    return code


# ---------------------------------------------------------------------------------------------------- self-test

def self_test() -> int:
    plan = {"environment": "local", "target": "http://127.0.0.1:1/", "functions": [{"id": "a", "name": "A", "steps": [
        {"action": "click", "on": {"role": "button", "name": "Go"}, "expect": {"text": "Done"}}]}]}
    check_web_plan(plan)
    shipped = (Path(__file__).resolve().parents[1] / "assets/example-plan.json").read_text()
    # In the source tree the host is still the build's placeholder.
    check_web_plan(json.loads(re.sub(r"@[A-Z]+@", "example.test", shipped)))
    base = plan["functions"][0]["steps"][0]

    def with_step(**change):
        step = {k: v for k, v in {**base, **change}.items() if v is not None}
        return {**plan, "functions": [{"id": "a", "name": "A", "steps": [step]}]}

    for words, change in (("tests nothing", {"expect": None}), ("unknown key", {"expects": {"text": "x"}}),
                          ("always true", {"expect": {"text": ""}}), ("exactly one of", {"on": None}),
                          ("action is one of", {"action": "evaluate"}),
                          ("exactly one of value", {"action": "type", "expect": None}),
                          ("at least 4", {"ignore_requests": [""]}),
                          ("Enter key", {"action": "type", "value": "delete all\n", "expect": None})):
        assert words in K.refused(lambda: check_web_plan(with_step(**change))), words
    assert "not a read" in K.refused(lambda: check_web_plan(
        {**with_step(dialog="accept"), "environment": "production"}))

    allowed = {"127.0.0.1:1"}
    own, other = "http://127.0.0.1:1/api", "https://elsewhere.test/api"
    assert guard_reason(own, "POST", "fetch", allowed, "local", "read", False) == ""
    assert guard_reason(other, "GET", "image", allowed, "local", "read", False) == ""
    assert guard_reason(other, "GET", "document", allowed, "local", "read", False) == OUTSIDE
    assert guard_reason(other, "POST", "fetch", allowed, "local", "write", True) == OUTSIDE
    assert guard_reason(own, "GET", "fetch", allowed, "production", "read", False) == ""
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        assert guard_reason(own, method, "fetch", allowed, "production", "read", True) == GUARD
        assert guard_reason(own, method, "fetch", allowed, "production", "delete", False) == GUARD
        assert guard_reason(own, method, "fetch", allowed, "production", "delete", True) == ""

    assert guard_reason(other, "GET", "subframe", allowed, "local", "read", False) == ""
    assert guard_reason(other, "POST", "subframe", allowed, "local", "read", False) == OUTSIDE
    went = [{"type": "document", "url": own}, {"type": "document", "url": other}]
    assert left_for(went, "chrome-error://chromewebdata/", allowed) == other
    assert left_for(went[:1], "chrome-error://chromewebdata/", allowed) == "", "a server that is down is a failure"
    assert left_for([{"type": "subframe", "url": other}], own, allowed) == ""
    assert may_send_frame("local", True, "read", False) and may_send_frame("production", False, "read", False)
    assert not may_send_frame("production", True, "read", True) and not may_send_frame("production", True, "trade", False)
    assert may_send_frame("production", True, "trade", True)

    def request(path, status=200, **extra):
        return {"method": "GET", "url": f"http://127.0.0.1:1{path}", "type": "fetch", "status": status, **extra}

    def judge(step=None, **facts):
        seen = {"step": step or base, "met": True, "changed": True, "requests": [request("/api/q")], "console": [],
                "observed": "Done", "response_ms": 120, "budget_ms": 2000, "timeout_ms": 8000, **facts}
        return analyze(seen)

    assert judge() == (K.PASS, [])
    verdict, why = judge(met=False, requests=[request("/api/coupon", 500)],
                         console=[{"text": "coupon failed: 500", "url": ""}], response_ms=None)
    assert verdict == K.FAIL and "expected result not seen" in why[0] and "-> 500" in why[1] and "console" in why[2]
    verdict, why = judge(response_ms=4100)
    assert verdict == K.FAIL and why == ["slow: answered in 4100 ms, the budget is 2000 ms"]
    verdict, why = judge(met=False, changed=False, requests=[], response_ms=None)
    assert verdict == K.FAIL and why[0].startswith("no response:")
    verdict, why = judge(met=False, requests=[request("/api/hang", None, pending=True)], response_ms=None)
    assert verdict == K.FAIL and any(r.startswith("missing response: GET /api/hang") for r in why)
    assert judge(requests=[request("/api/x", None, failure="net::ERR_CONNECTION_REFUSED")])[0] == K.FAIL
    assert judge(already=True)[0] == K.FAIL and judge(leaked=True)[0] == K.FAIL
    assert judge(left_host="https://elsewhere.test/")[0] == K.NOT_RUN
    outside = request("/api/pay", None, method="POST", blocked=OUTSIDE)
    assert judge(requests=[outside]) == (K.PASS, []), "a beacon elsewhere does not spoil a step that passed"
    verdict, why = judge(requests=[outside], met=False, response_ms=None)
    assert verdict == K.NOT_RUN and "own guard" in why[0], "the guard's failure is not the app's bug"
    frame = {"method": "SEND", "url": "ws://127.0.0.1:1/ws", "type": "websocket", "blocked": HELD_FRAME}
    assert judge(requests=[frame], met=False, response_ms=None)[0] == K.NOT_RUN
    assert judge(requests=[request("/favicon.ico", 404)], console=[
        {"text": "Failed to load resource: 404", "url": "http://127.0.0.1:1/favicon.ico"}]) == (K.PASS, [])
    denied = {**base, "expect": {"status": 401, "request": "/api/login"}}
    noise = [{"text": "Failed to load resource: 401", "url": "http://127.0.0.1:1/api/login"}]
    assert judge(denied, requests=[request("/api/login", 401)], console=noise) == (K.PASS, [])
    assert judge(requests=[request("/api/login", 401)], console=noise)[0] == K.FAIL
    verdict, why = judge(requests=[request("/api/q", None, blocked=GUARD)], met=False, response_ms=None)
    assert verdict == K.NOT_RUN and "not tested" in why[0]
    assert new_lines("a\nb", "a\nb\nc\na") == "c\na"
    assert pick(list(range(0, 4000, 40)), list(range(0, 4000, 80)), [2000], 6).count(50) == 1
    assert len(pick(list(range(0, 4000, 40)), list(range(0, 4000, 80)), [2000], 6)) == 6
    typed = {"action": "type", "on": {"label": "Password"}, "secret": "PW"}
    assert describe_input(typed) == 'type <secret:PW> into label "Password"'

    if not shutil.which("ffmpeg"):
        print("self-test passed: plan, guard and verdict rules (ffmpeg missing: the video tools were NOT checked)")
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        video = Path(tmp) / "v.webm"
        ffmpeg("-f", "lavfi", "-i", "color=c=white:s=320x200:r=25:d=2", "-f", "lavfi", "-i",
               "color=c=red:s=320x200:r=25:d=2", "-filter_complex", "[0:v][1:v]concat=n=2:v=1", "-c:v", "libvpx", str(video))
        trim(video, 3000)
        facts, frames = key_frames(video, Path(tmp) / "v-frames", 500, [2000])
        assert 2800 <= facts["duration_ms"] <= 3100 and facts["opens"], facts
        assert any(f["video_ms"] == 2000 and f["after_action_ms"] == 1500 for f in frames), frames
        assert all((Path(tmp) / "v-frames" / f["file"]).read_bytes()[:8] == b"\x89PNG\r\n\x1a\n" for f in frames)
        broken = Path(tmp) / "broken.webm"
        broken.write_bytes(b"not a video")
        try:
            frame_times(broken)
        except ValueError:
            pass
        else:
            raise AssertionError("a file that is no video must not pass")
    print("self-test passed: plan, guard and verdict rules, and key frames from a real video")
    return 0


def main(argv: list) -> int:
    if argv[:1] == ["--self-test"]:
        return self_test()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("plan")
    parser.add_argument("--out", required=True, help="an empty directory outside any repository")
    parser.add_argument("--approve", action="append", default=[], metavar="FUNCTION/STEP",
                        help="production only: a step the owner approved by name")
    args = parser.parse_args(argv)
    try:
        return run(args.plan, args.out, args.approve)
    except (K.Refused, OSError, ValueError) as why:
        print(f"REFUSED {why}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
