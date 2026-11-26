#!/usr/bin/env python3
"""Check the text and names of issues, comments, branches, commits and PRs: the one format, enforced.

    package_lint.py issue --kind epic|planning|package --title "API-03: Cancel an open order" \\
        --label enhancement --label backend --label medium --body-file issue.md
    package_lint.py comment --kind plan|epic-plan|decision|status|verdict|fix|merge|close|reply --body-file note.md
    package_lint.py branch api-03/cancel-order
    package_lint.py commit "feat(api-03): add the cancel route"
    package_lint.py pr --branch api-03/cancel-order --title "feat(api-03): add the cancel route" --body-file pr.md
    package_lint.py pr-body --body-file pr.md
    package_lint.py templates                 (where each template is read from)
    package_lint.py catalog
    package_lint.py --self-test

THE TEMPLATE IS THE RULE. The sections of an issue, a plan, a PR body and a PR comment, their order and what they must
hold come from the *.template.md files, so editing a template changes what is required. On a heading line:
  <!-- optional -->     the section may be left out
  <!-- on pass -->      PR comment: required after PASS or an acceptance      <!-- on fail -->  after FAIL or changes
  <!-- needs code -->   the section holds a command, path or symbol in backticks
  <!-- needs fence -->  the section holds a fenced block
Inside a section, a literal '**Label:**' line, a table header, a '1. **`ID` (title):**' item and a '- **<risk>:**'
bullet are required in the same shape. AGENT_TEMPLATES=<dir> makes <dir>/<name>.template.md replace the built-in one.

Every issue, comment and PR body ends with 'Created: <author>' (equal to AGENT_NAME when set) and carries no
"Generated with" tool footer. The allowed labels, priorities and kinds come from ../assets/catalog.json.
Exit 0 = clean, 1 = findings (one per line), 2 = usage. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

CATALOG = json.loads((Path(__file__).resolve().parents[1] / "assets" / "catalog.json").read_text(encoding="utf-8"))
TYPES = ("feat", "fix", "refactor", "perf", "test", "docs", "chore", "ci", "build")
TASK_TYPES = tuple(CATALOG["types"])
LANES = tuple(CATALOG["lanes"])
DIFFICULTIES = tuple(CATALOG["difficulties"])
FLAGS = tuple(CATALOG["flags"])
PRIORITIES = tuple(CATALOG["priorities"])
ISSUE_KINDS = tuple(CATALOG["issue_kinds"])
COMMENT_KINDS = tuple(CATALOG["comment_kinds"])

ID = r"[A-Z][A-Z0-9]{1,7}-\d{2,4}[a-z]?"
LOW_ID = r"[a-z][a-z0-9]{1,7}-\d{2,4}[a-z]?"
TITLE_RE = re.compile(rf"^(?P<id>{ID}): (?P<text>\S.*)$")
TITLE_TAG_RE = re.compile(r"^\[(\w+) Priority\] ")
BRANCH_RE = re.compile(rf"^(?P<id>{LOW_ID})/[a-z0-9]+(-[a-z0-9]+){{0,5}}$")
COMMIT_RE = re.compile(rf"^({'|'.join(TYPES)})\((?P<id>{LOW_ID})\)!?: (?P<subject>\S.*)$")
WAVE = {"epic": r"0 \(Epic\)", "planning": r"(?:\d+|Backlog\b.*)", "package": r"\d+"}
# template name -> the skill whose assets hold it
TEMPLATES = {"epic": "write-issue", "planning": "write-issue", "package": "write-issue", "plan": "write-comment",
             "epic-plan": "write-comment", "pr-comment": "write-comment", "pr": "work-package"}
PLAN_KINDS = ("plan", "epic-plan")
# kind -> (what the first line must match, the shape to show, lines the body must have)
FIRST_LINE = {
    "decision": (r"(Accepted|Changes required|Stopped) by (CTO|CEO) \(.+?\)[.:]", "Accepted | Changes required | Stopped by CTO (<name>). ...", ()),
    "status": (r"Status: (started|blocked|done)$", "Status: started|blocked|done", ("Card:", "Evidence:", "Next:")),
    "verdict": (r"Verdict: (PASS|FAIL) at [0-9a-f]{40}$", "Verdict: PASS|FAIL at <40-character sha>", ()),
    "fix": (r"Fixed in [0-9a-f]{7,40}:$", "Fixed in <sha>:", ("New head:",)),
    "merge": (r"Merged by .+ at [0-9a-f]{7,40} after (PASS|acceptance)\.$", "Merged by <who> at <sha> after PASS|acceptance.", ()),
    "close": (r"(Closed: \S|Replaced by #\d+)", "Closed: <outcome and proof> | Replaced by #N", ()),
    "reply": (r"\S", "any text", ()),
}
CLOSE_RE = re.compile(r"^(Closes|Refs) #\d+\s*$", re.M)
GENERATED_RE = re.compile(r"(?im)^\W*generated (?:with|by) (?:\[|claude\b|chatgpt\b|copilot\b|codex\b|gemini\b)")
MARKERS = ("optional", "on pass", "on fail", "needs code", "needs fence")
PR_HEAD_RE = re.compile(r"PR #\d+ at [0-9a-f]{40}")
MAX_ROUNDS = 3  # change requests the CTO/CEO may make on one PR in playbook-quick
ROUND_RE = re.compile(rf"PR #\d+ at [0-9a-f]{{40}}\. Round [1-{MAX_ROUNDS}] of {MAX_ROUNDS}\.\s*$")
CREATED_RE = re.compile(r"^Created: (\S.*?)\s*$", re.M)
SECRET_RE = re.compile(
    r"(?i)(ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|(?:token|password|secret)\s*[:=]\s*\S{8,})"
)


def template_path(name: str) -> Path:
    """<AGENT_TEMPLATES>/<name>.template.md when it exists, else the built-in one in its skill's assets."""
    override = os.environ.get("AGENT_TEMPLATES", "").strip()
    if override and (Path(override) / f"{name}.template.md").is_file():
        return Path(override) / f"{name}.template.md"
    own = Path(__file__).resolve().parents[1]
    # an installed copy may prefix every skill directory (<prefix>-work-package)
    return own.parent / own.name.replace("work-package", TEMPLATES[name]) / "assets" / f"{name}.template.md"


def split_sections(body: str, level: int) -> tuple[str, list[tuple[str, str, str]]]:
    """(preamble, [(name, heading line, content)]) at one heading level. Headings inside fences do not count."""
    mark = "#" * level + " "
    preamble: list[str] = []
    found: list[tuple[str, str, list[str]]] = []
    fenced = False
    for line in body.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
        if not fenced and line.startswith(mark):
            name = re.sub(r"<!--.*?-->", "", line[len(mark):]).split(" (")[0].split(" — ")[0].strip()
            found.append((name, line, []))
        elif found:
            found[-1][2].append(line)
        else:
            preamble.append(line)
    return "\n".join(preamble), [(n, h, CREATED_RE.sub("", "\n".join(c)).strip()) for n, h, c in found]


def read_template(name: str) -> tuple[int, str, list[dict]]:
    """(heading level, preamble, sections) of a template. Each section: name, markers, content."""
    text = template_path(name).read_text(encoding="utf-8")
    level = 3 if name in PLAN_KINDS else 2
    preamble, sections = split_sections(text, level)
    parsed = []
    for section, heading, content in sections:
        comment = re.search(r"<!--(.*?)-->", heading)
        markers = [m.strip() for m in comment.group(1).split(",")] if comment else []
        unknown = [m for m in markers if m not in MARKERS]
        if unknown:
            raise SystemExit(f"{name}.template.md: unknown marker {unknown} (use {', '.join(MARKERS)})")
        parsed.append({"name": section, "markers": markers, "content": content})
    return level, preamble, parsed


def table_header(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("|"):
            return re.sub(r"\s*\|\s*", "|", line.strip())
    return ""


def lint_shape(section: dict, content: str) -> list[str]:
    """What one filled section must hold, read from the same section of the template."""
    name, wanted, problems = section["name"], section["content"], []
    if not content:
        return [f"'{name}' is empty"]
    if "needs code" in section["markers"] and "`" not in content:
        problems.append(f"'{name}' needs a command, path or symbol in backticks")
    if "needs fence" in section["markers"] and "```" not in content:
        problems.append(f"'{name}' needs a fenced block")
    for label in re.findall(r"^(?:\d+\. |- )?\*\*([^*<`]+):\*\*", wanted, re.M):
        if not re.search(rf"(?:\*\*)?\b{re.escape(label)}:(?:\*\*)? \S", content):
            problems.append(f"'{name}' has no '**{label}:** ...' line")
    for label in re.findall(r"^(?:\d+\. |- )?\*\*([^*<`]+):\*\*[^\n]*`", wanted, re.M):
        line = re.search(rf"(?:\*\*)?\b{re.escape(label)}:[^\n]*", content)
        if line and "`" not in line.group(0):
            problems.append(f"the '**{label}:**' line needs a command or path in backticks")
    header = table_header(wanted)
    if header:
        rows = [x for x in content.splitlines() if x.startswith("|")]
        if not rows or re.sub(r"\s*\|\s*", "|", rows[0].strip()) != header:
            problems.append(f"'{name}' needs the table columns {header}")
        elif not re.search(rf"^\|.*`{ID}`", content, re.M):
            problems.append(f"'{name}' has no table row with a package ID")
    if re.search(r"^1\. \*\*`", wanted, re.M) and not re.search(rf"^\d+\. \*\*`{ID}` \([^)]+\):\*\* \S", content, re.M):
        problems.append(f"'{name}' has no item like 1. **`ID` (title):** what it does")
    if re.search(r"^- \*\*<", wanted, re.M) and not re.search(r"^- \*\*[^*]+:\*\* \S", content, re.M):
        problems.append(f"'{name}' writes each point as - **<name>:** <text>")
    return problems


def lint_sections(template: str, body: str, outcome: str | None = None) -> list[str]:
    """The body against a template: required sections, their order, and each one's shape."""
    level, _, wanted = read_template(template)
    _, found = split_sections(body, level)
    problems: list[str] = []
    ranks = []
    matched: dict[int, list[str]] = {}
    for name, _, content in found:
        for rank, section in enumerate(wanted):
            if name == section["name"] or name.startswith(section["name"] + " "):
                ranks.append(rank)
                matched.setdefault(rank, []).append(content)
                break
    for rank, section in enumerate(wanted):
        markers = section["markers"]
        conditional = [m for m in markers if m in ("on pass", "on fail")]
        required = "optional" not in markers and (not conditional or f"on {outcome}" in conditional)
        if rank not in matched:
            if required:
                problems.append(f"body has no '{'#' * level} {section['name']}' section ({template} template)")
            continue
        if conditional == ["on fail"] and outcome == "pass":
            problems.append(f"a passing comment has no '{section['name']}' section")
        for content in matched[rank]:
            problems += lint_shape(section, content)
    if ranks != sorted(ranks):
        problems.append("sections are out of order (" + ", ".join(s["name"] for s in wanted) + ")")
    return problems


def lint_pr_body(body: str) -> list[str]:
    """Every pull request, whatever its branch, has this one body."""
    problems = lint_sections("pr", body)
    if not CLOSE_RE.search(body):
        problems.append("body has no closing line 'Closes #N' (or 'Refs #N' for partial work)")
    return problems + lint_signature(body)


def lint_signature(body: str) -> list[str]:
    """Every text an agent publishes is signed on its last line, and carries no secret."""
    problems: list[str] = []
    lines = [x for x in body.rstrip().splitlines() if x.strip()]
    signed = CREATED_RE.findall(body)
    if len(signed) != 1 or not lines or not CREATED_RE.match(lines[-1]):
        problems.append("the last line must be exactly one 'Created: <author>' line")
    else:
        name = signed[0]
        if "<" in name:
            problems.append(f"'Created: {name}' still holds a placeholder: write your agent name")
        expected = os.environ.get("AGENT_NAME", "").strip()
        if expected and name != expected:
            problems.append(f"'Created: {name}' is not your agent name {expected!r} (AGENT_NAME)")
    if GENERATED_RE.search(body):
        problems.append("remove the 'Generated with' tool footer: 'Created: <author>' is the only signature")
    if SECRET_RE.search(body):
        problems.append("body looks like it contains a secret")
    return problems


def lint_labels(labels: list[str]) -> tuple[list[str], list[str], list[str]]:
    """Return (problems, lane labels, difficulty labels). Any other plain label is an area."""
    problems: list[str] = []
    groups = {}
    for group, allowed in (("type", TASK_TYPES), ("lane", LANES), ("difficulty", DIFFICULTIES)):
        groups[group] = [x for x in labels if x in allowed]
        if len(groups[group]) != 1:
            problems.append(f"labels need exactly one {group} of {', '.join(allowed)} (got {groups[group] or 'none'})")
    known = set(TASK_TYPES + LANES + DIFFICULTIES + FLAGS)
    for label in labels:
        if label in known:
            continue
        if ":" in label or label.lower() in PRIORITIES or "priority" in label.lower():
            problems.append(f"label {label!r} is not in the catalog (priority is the 'Priority:' line, not a label)")
    return problems, groups["lane"], groups["difficulty"]


def lint_issue(kind: str, title: str, labels: list[str], body: str) -> list[str]:
    problems, lanes, diffs = lint_labels(labels)
    priority = re.search(rf"^Priority: ({'|'.join(PRIORITIES)})\b", body, re.M)
    match = TITLE_RE.match(title)
    if not match:
        problems.append(f"title {title!r} is not 'ID: title' with an ID like API-03 (area in capitals, hyphen, 2+ digits)")
    else:
        text = match.group("text")
        tag = TITLE_TAG_RE.match(text)
        if tag and priority and tag.group(1).lower() != priority.group(1):
            problems.append(f"title says {tag.group(1)} priority but the body says {priority.group(1)}")
        if not 4 <= len(text) <= 90:
            problems.append(f"title text is {len(text)} chars (4 to 90)")
        if text.endswith("."):
            problems.append("title ends with a period")
        if re.match(rf"^({'|'.join(TYPES)})(\(|:)", text):
            problems.append("title carries a commit type prefix; an issue title is 'ID: outcome'")
        if kind == "epic" and not (match.group("id").endswith("-00") and text.startswith("Epic — ")):
            problems.append("an epic title is '<AREA>-00: Epic — <outcome>'")
    headers = {
        "Lane": r"^Lane: (\S+)\s*$",
        "Wave": rf"^Wave: ({WAVE[kind]})\s*$",
        "Difficulty": rf"^Difficulty: ({'|'.join(DIFFICULTIES)})\b",
        "Priority": rf"^Priority: ({'|'.join(PRIORITIES)})\b",
    }
    wanted_headers = re.findall(r"^([A-Z][\w-]*): ", read_template(kind)[1], re.M)
    for key in wanted_headers:
        pattern = headers.get(key, rf"^{re.escape(key)}: \S.*$")
        found = re.search(pattern, body, re.M)
        if not found:
            problems.append(f"body has no valid '{key}: ...' header line for a {kind} issue")
        elif key == "Lane" and lanes and found.group(1) != lanes[0]:
            problems.append(f"body Lane is {found.group(1)!r} but the lane label is {lanes[0]!r}")
        elif key == "Difficulty" and diffs and found.group(1) != diffs[0]:
            problems.append(f"body Difficulty is {found.group(1)!r} but the difficulty label is {diffs[0]!r}")
    return problems + lint_sections(kind, body) + lint_signature(body)


def lint_plan(kind: str, body: str) -> list[str]:
    problems: list[str] = []
    priority = rf" — Priority: ({'|'.join(p.capitalize() for p in PRIORITIES)})"
    suffix = priority if kind == "plan" else rf"({priority})?"
    first = body.lstrip().splitlines()[0] if body.strip() else ""
    if not re.match(rf"^## Architecture & Planning \(`{ID}`{suffix}( — Plan v\d+)?\)\s*$", first):
        shape = "(`ID` — Priority: Low)" if kind == "plan" else "(`ID`)"
        problems.append(f"first line is not '## Architecture & Planning {shape}'")
    return problems + lint_sections(kind, body)


def pr_comment_outcome(kind: str, first: str) -> str | None:
    """For a comment on a pull request: 'pass', 'fail' or 'note'. None: not a PR comment."""
    if kind == "verdict":
        return "fail" if first.startswith("Verdict: FAIL") else "pass"
    if kind == "decision" and PR_HEAD_RE.search(first):
        return "pass" if first.startswith("Accepted") else "fail"
    return "note" if kind in ("fix", "merge") else None


def lint_comment(kind: str, body: str) -> list[str]:
    if kind in PLAN_KINDS:
        return lint_plan(kind, body) + lint_signature(body)
    pattern, shape, lines = FIRST_LINE[kind]
    problems: list[str] = []
    first = body.lstrip().splitlines()[0] if body.strip() else ""
    if not re.match(pattern, first) or first.startswith("Created:"):
        problems.append(f"a {kind} comment starts with: {shape}")
    for line in lines:
        if not re.search(rf"^{re.escape(line)} \S", body, re.M):
            problems.append(f"a {kind} comment needs a '{line} ...' line")
    if kind == "decision" and first.startswith("Stopped") and not PR_HEAD_RE.search(first):
        problems.append("'Stopped by' is a decision on a pull request: name 'PR #<n> at <40-character sha>.'")
    if kind == "decision" and first.startswith("Changes required") and PR_HEAD_RE.search(first) and not ROUND_RE.search(first):
        problems.append(f"a change request on a PR ends its first line with 'Round K of {MAX_ROUNDS}.' (K from 1 to {MAX_ROUNDS})")
    outcome = pr_comment_outcome(kind, first)
    if outcome:
        problems += lint_sections("pr-comment", body, outcome)
    return problems + lint_signature(body)


def lint_branch(branch: str) -> list[str]:
    if BRANCH_RE.match(branch):
        return []
    return [f"branch {branch!r} is not <id>/<slug>, e.g. api-03/cancel-order (id lowercase, slug of 1 to 6 words)"]


def lint_commit(line: str) -> list[str]:
    match = COMMIT_RE.match(line)
    if not match:
        return [f"{line!r} is not '<type>(<id>): <summary>', e.g. feat(api-03): add the cancel route"]
    problems: list[str] = []
    subject = match.group("subject")
    if len(subject) > 72:
        problems.append(f"summary is {len(subject)} chars (max 72)")
    if subject.endswith("."):
        problems.append("summary ends with a period")
    return problems


def lint_pr(branch: str, title: str, body: str) -> list[str]:
    problems = lint_branch(branch) + lint_commit(title)
    branch_id = BRANCH_RE.match(branch)
    title_id = COMMIT_RE.match(title)
    if branch_id and title_id and branch_id.group("id") != title_id.group("id"):
        problems.append(f"branch id {branch_id.group('id')!r} differs from the title scope {title_id.group('id')!r}")
    return problems + lint_pr_body(body)


FIXTURES = {
    "epic": "Lane: x\nWave: 0 (Epic)\nDifficulty: hard\nPriority: low\n\n## Goal\ng\n\n## Reference Architecture <!-- optional -->\nr\n\n## Done when <!-- needs code -->\n`c`\n",
    "planning": "Lane: x\nWave: 1\nDifficulty: hard\nPriority: low\n\n## Goal\ng\n\n## Read first <!-- needs code -->\n`f`\n\n## Scope (high-level)\ns\n\n## Depends on\nd\n\n## Done when <!-- needs code -->\n`c`\n\n## Notes <!-- optional -->\nn\n",
    "package": "Lane: x\nWave: 1\nDifficulty: hard\nPriority: low\n\n## Goal\ng\n\n## Read first <!-- needs code -->\n`f`\n\n## Owned files <!-- needs code -->\n`f`\n\n## Forbidden\nf\n\n## Depends on <!-- optional -->\nd\n\n## Done when <!-- needs code -->\n`c`\n\n## Branch and PR\nb\n",
    "plan": "## Architecture & Planning (`<ID>` — Priority: Low)\n\n### Code analysis <!-- needs code -->\n`f`\n\n### Core design decision\nd\n\n**Stack:** <s>\n**Rejected:** <r>\n\n### Planned Packages\n1. **`<ID>a` (<t>):** <w>\n\n### Risks & Gates <!-- needs code -->\n- **<risk>:** <r>\n- **Gates:** `<c>`\n",
    "epic-plan": "## Architecture & Planning (`<ID>`)\n\n### Code analysis <!-- needs code -->\n`f`\n\n### Core design decision\n**Stack:** <s>\n**Rejected:** <r>\n\n### Packages & Wave Order\n| Wave | Issue | Scope | Key Owned Files | Gate |\n|---|---|---|---|---|\n\n### Shared-File Sequencing Rules\nnone\n\n### Risks & Mitigations\n- **<risk>:** <r>\n",
    "pr": "Closes #<n>\n\n## Why\nw\n\n## What changed\nc\n\n## Review fix <!-- optional -->\nr\n\n## Scope\ns\n\n## Blast radius\nb\n\n## Verification <!-- needs code -->\n`c`\n",
    "pr-comment": "<headline>\n\n## Blocking — <t> <!-- on fail, needs code -->\n**Smallest fix:** <f>\n\n## Verified <!-- on pass, needs code -->\n1. **Scope & Diff:** <d>\n\n## Gate <!-- needs fence -->\n```\nc\n```\n\n## Residual\n- none\n",
}
SHA = "a1b2c3d4" * 5
GATE = "\n\n## Gate\n```text\nmake verify\n  12 passed\n```\n\n## Residual\n- none"
VERIFIED = "\n\n## Verified\n1. **Scope & Diff:** only `src/orders.py`."
BLOCKING = "\n\n## Blocking — double cancel\n`src/orders.py:9` cancels twice.\n\n**Smallest fix:** check the status first."
SIGN = "\nCreated: Builder (Developer)\n"
GOOD_ISSUE = """Lane: backend
Wave: 1
Difficulty: medium (a route with storage)
Priority: medium

## Goal
Cancel an open order.

## Read first
- `AGENTS.md`

## Owned files (create or change only these)
- `src/orders/cancel.py` (new)

## Forbidden
- every file not listed above

## Depends on
- nothing; start now

## Done when (run from the repository root)
- `pytest -q tests/test_cancel.py`

## Branch and PR
- Branch `api-03/cancel-order` from `main`; do not merge it.
""" + SIGN
GOOD_PLANNING = """Lane: backend
Wave: Backlog (Priority: Low — queued after API-01)
Difficulty: medium
Priority: low

## Goal
Orders can be cancelled.

## Read first
- `src/orders.py`

## Scope (high-level)
- cancel an open order

## Depends on
- nothing

## Done when
```bash
make verify
```

## Notes
See the planning comment.
""" + SIGN
GOOD_EPIC = """Lane: backend
Wave: 0 (Epic)
Difficulty: hard
Priority: high

## Goal
Orders have a full lifecycle.

## Reference Architecture
One state machine.

## Done when
All children merged and `make verify` passes.
""" + SIGN
GOOD_PLAN = """## Architecture & Planning (`API-04` — Priority: Low)

### Code analysis
- `src/orders.py:3`: no cancel path.

### Core design decision
A status change, so history stays.

**Stack:** no new dependency.
**Rejected:** deleting the row loses history.

### Planned Packages (split into child cards when promoted)
1. **`API-04a` (Backend cancel route):** add the route in `src/orders.py`.

### Risks & Gates
- **Double cancel:** the second call is a no-op.
- **Gates:** `make verify`
""" + SIGN
GOOD_EPIC_PLAN = """## Architecture & Planning (`API-00`)

### Code analysis
- `src/orders.py:3`: no cancel path.

### Core design decision (one state machine)
One state machine.

**Stack:** no new dependency.
**Rejected:** a flag per state.

### Packages & Wave Order

| Wave | Issue | Scope | Key Owned Files | Gate |
|---|---|---|---|---|
| **Wave 1** | `#2` (`API-01`) | cancel | `src/orders.py` | `make verify` |

### Shared-File Sequencing Rules
- `src/orders.py`: one package at a time.

### Risks & Mitigations
- **Lost update:** lock the row.
""" + SIGN
GOOD_COMMENTS = {
    "plan": GOOD_PLAN,
    "epic-plan": GOOD_EPIC_PLAN,
    "decision": "Accepted by CTO (Boss). Plan v1; the packages stay in the backlog." + SIGN,
    "status": "Status: blocked\nCard: API-03\nEvidence: a log line\nNext: ask the owner" + SIGN,
    "verdict": f"Verdict: PASS at {SHA}\n\nReview of PR #3." + VERIFIED + GATE + SIGN,
    "fix": "Fixed in a1b2c3d4:\n- x: y\n\nNew head: a1b2c3d4. Please re-review." + GATE + SIGN,
    "merge": "Merged by the gate at a1b2c3d4 after PASS." + GATE + SIGN,
    "close": "Replaced by #9" + SIGN,
    "reply": "The retry limit is three." + SIGN,
}
GOOD_PR = """Closes #12

## Why
Orders could not be cancelled.

## What changed
- the cancel route

## Scope
Cancel only.

## Blast radius
Open orders.

## Verification
- `pytest -q tests/test_cancel.py`: 1 passed
""" + SIGN
TITLE = "feat(api-03): add the cancel route"
BRANCH = "api-03/cancel-order"
ISSUE_TITLE = "API-03: Cancel an open order"


def self_test() -> int:
    os.environ.pop("AGENT_NAME", None)
    with tempfile.TemporaryDirectory() as folder:
        for name, text in FIXTURES.items():
            Path(folder, f"{name}.template.md").write_text(text, encoding="utf-8")
        previous = os.environ.get("AGENT_TEMPLATES")
        os.environ["AGENT_TEMPLATES"] = folder
        try:
            return run_cases(Path(folder))
        finally:
            os.environ.pop("AGENT_TEMPLATES") if previous is None else os.environ.update(AGENT_TEMPLATES=previous)


def run_cases(folder: Path) -> int:
    failures: list[str] = []

    def expect(name: str, got: list[str], needle: str = "") -> None:
        if not needle and got:
            failures.append(f"{name}: expected clean, got {got}")
        if needle and not any(needle in g for g in got):
            failures.append(f"{name}: expected a finding with {needle!r}, got {got}")

    def package(title=ISSUE_TITLE, labels=None, body=GOOD_ISSUE):
        return lint_issue("package", title, labels or good, body)

    good = ["enhancement", "backend", "medium", "orders"]
    low = ["enhancement", "backend", "medium"]
    expect("good package", package())
    expect("area is optional", package(labels=low))
    expect("bad id", package(title="api3: Cancel"), "not 'ID: title'")
    expect("type prefix", package(title="API-03: feat: cancel it"), "commit type prefix")
    expect("no type", package(labels=["backend", "medium"]), "exactly one type")
    expect("no lane", package(labels=["enhancement", "medium"]), "exactly one lane")
    expect("two difficulties", package(labels=good + ["hard"]), "exactly one difficulty")
    expect("invented label", package(labels=good + ["type:feat"]), "not in the catalog")
    expect("priority label", package(labels=good + ["high"]), "not in the catalog")
    expect("flag label", package(labels=good + ["risk:money-path"]))
    expect("lane mismatch", package(labels=["enhancement", "frontend", "medium"]), "Lane is")
    expect("no priority", package(body=GOOD_ISSUE.replace("Priority: medium\n", "")), "'Priority:")
    expect("missing section", package(body=GOOD_ISSUE.replace("## Forbidden\n- every file not listed above\n\n", "")), "no '## Forbidden'")
    expect("unrunnable done", package(body=GOOD_ISSUE.replace("`pytest -q tests/test_cancel.py`", "it works")), "'Done when' needs")
    shuffled = GOOD_ISSUE.replace("## Goal\nCancel an open order.\n\n", "").replace(SIGN, "\n## Goal\nlate\n" + SIGN)
    expect("order", package(body=shuffled), "out of order")
    expect("secret", package(body=GOOD_ISSUE.replace(SIGN, "token = abcdefgh12345678\n" + SIGN)), "secret")
    expect("unsigned", package(body=GOOD_ISSUE.replace(SIGN, "")), "Created:")
    expect("signature not last", package(body=GOOD_ISSUE + "\nmore\n"), "Created:")
    expect("placeholder signature", package(body=GOOD_ISSUE.replace("Builder (Developer)", "<your name>")), "placeholder")
    os.environ["AGENT_NAME"] = "Someone Else"
    expect("wrong author", package(), "not your agent name")
    os.environ.pop("AGENT_NAME")
    expect("good planning", lint_issue("planning", "API-04: [Low Priority] Cancel orders", low, GOOD_PLANNING))
    expect("planning tag", lint_issue("planning", "API-04: [High Priority] Cancel orders", low, GOOD_PLANNING), "title says")
    expect("planning scope", lint_issue("planning", "API-04: Cancel orders", low, GOOD_PLANNING.replace("## Scope", "## Idea")), "no '## Scope'")
    expect("planning is not a package", package(body=GOOD_PLANNING), "no '## Owned files'")
    hard = ["enhancement", "backend", "hard"]
    expect("good epic", lint_issue("epic", "API-00: Epic — Order lifecycle", hard, GOOD_EPIC))
    expect("epic title", lint_issue("epic", "API-04: Order lifecycle", hard, GOOD_EPIC), "an epic title")
    expect("every comment kind has a good example", [k for k in COMMENT_KINDS if k not in GOOD_COMMENTS])
    for kind, text in GOOD_COMMENTS.items():
        expect(f"good {kind}", lint_comment(kind, text))
        expect(f"unsigned {kind}", lint_comment(kind, text.replace(SIGN, "")), "Created:")

    def plan(old: str, new: str, kind: str = "plan") -> list[str]:
        return lint_comment(kind, GOOD_COMMENTS[kind].replace(old, new))

    expect("plan heading", plan(" — Priority: Low", ""), "first line")
    expect("plan version", plan("Priority: Low)", "Priority: Low — Plan v2)"))
    expect("plan analysis", plan("`src/orders.py:3`", "the code"), "'Code analysis' needs")
    expect("plan stack", plan("**Stack:** no new dependency.\n", ""), "**Stack:**")
    expect("plan rejected", plan("**Rejected:** deleting the row loses history.\n", ""), "**Rejected:**")
    expect("plan package", plan("1. **`API-04a` (Backend cancel route):**", "1. later:"), "no item like")
    expect("plan gate", plan("- **Gates:** `make verify`", "- **Gates:** tests"), "'Risks & Gates' needs")
    expect("gates line itself", plan("- **Gates:** `make verify`", "- **Gates:** tests\n- **Other:** `x`"), "line needs a command")
    expect("plan section", plan("### Risks & Gates", "### Notes"), "'### Risks & Gates'")
    expect("epic table", plan("| Wave | Issue |", "| Step | Issue |", "epic-plan"), "needs the table columns")
    expect("epic sequencing", plan("### Shared-File Sequencing Rules", "### Other", "epic-plan"), "Shared-File")
    expect("short sha", lint_comment("verdict", "Verdict: PASS at a1b2c3d4" + VERIFIED + GATE + SIGN), "40-character")
    expect("good fail", lint_comment("verdict", f"Verdict: FAIL at {SHA}" + BLOCKING + GATE + SIGN))
    expect("fail needs blocking", lint_comment("verdict", f"Verdict: FAIL at {SHA}" + GATE + SIGN), "no '## Blocking'")
    expect("fail needs a fix", lint_comment("verdict", f"Verdict: FAIL at {SHA}" + BLOCKING.replace("**Smallest fix:**", "Fix:") + GATE + SIGN), "Smallest fix")
    expect("a label may be plain", lint_comment("verdict", f"Verdict: FAIL at {SHA}" + BLOCKING.replace("**Smallest fix:**", "Smallest fix:") + GATE + SIGN))
    expect("pass with blocking", lint_comment("verdict", f"Verdict: PASS at {SHA}" + BLOCKING + VERIFIED + GATE + SIGN), "passing comment")
    expect("pass needs verified", lint_comment("verdict", f"Verdict: PASS at {SHA}" + GATE + SIGN), "no '## Verified'")
    expect("gate needs output", plan("```text\nmake verify\n  12 passed\n```", "it passed", "verdict"), "fenced block")
    expect("residual", plan("\n\n## Residual\n- none", "", "merge"), "no '## Residual'")
    expect("a heading in a fence is not a section", plan("  12 passed", "## Residual\n  12 passed", "merge"))
    expect("long names match", plan("## Verified\n", "## Verified on `a1b2c3d4`\n", "verdict"))
    accepted = f"Accepted by CTO (Boss (CTO)). PR #3 at {SHA}."
    expect("acceptance on a PR", lint_comment("decision", accepted + VERIFIED + GATE + SIGN))
    expect("acceptance on a PR needs the template", lint_comment("decision", accepted + SIGN), "no '## Gate'")
    changes = f"Changes required by CTO (Boss). PR #3 at {SHA}."
    expect("changes on a PR", lint_comment("decision", changes + " Round 2 of 3." + BLOCKING + GATE + SIGN))
    expect("changes need a round", lint_comment("decision", changes + BLOCKING + GATE + SIGN), "Round K of 3")
    expect("no fourth round", lint_comment("decision", changes + " Round 4 of 3." + BLOCKING + GATE + SIGN), "Round K of 3")
    halt = f"Stopped by CTO (Boss). PR #3 at {SHA}."
    expect("stopped", lint_comment("decision", halt + BLOCKING + GATE + SIGN))
    expect("stopped gives feedback", lint_comment("decision", halt + GATE + SIGN), "no '## Blocking'")
    expect("stopped names the PR", lint_comment("decision", "Stopped by CTO (Boss). Plan v1." + SIGN), "name 'PR #")
    expect("decision on a plan stays short", lint_comment("decision", "Accepted by CTO (Boss (CTO)). Plan v1." + SIGN))
    expect("decision shape", lint_comment("decision", "Looks good" + SIGN), "starts with")
    expect("only a signature", lint_comment("reply", SIGN), "starts with")
    for footer in ("🤖 Generated with [Claude Code](https://example.com)", "Generated with Claude Code", "Generated by [Tool](u)"):
        expect(f"footer {footer[:14]}", lint_pr_body(GOOD_PR.replace(SIGN, footer + "\n" + SIGN)), "tool footer")
    expect("ordinary prose is not a footer", lint_pr_body(GOOD_PR.replace("Cancel only.", "The client is generated by the build.")))
    # the template is the rule: edit it and the requirement follows
    pr_template = folder / "pr.template.md"
    pr_template.write_text(FIXTURES["pr"].replace("## Why", "## Problem").replace("## Blast radius", "## Blast radius <!-- optional -->"), encoding="utf-8")
    expect("renamed section is required", lint_pr_body(GOOD_PR), "no '## Problem'")
    expect("new style passes", lint_pr_body(GOOD_PR.replace("## Why", "## Problem").replace("## Blast radius\nOpen orders.\n\n", "")))
    pr_template.write_text(FIXTURES["pr"], encoding="utf-8")
    expect("good branch", lint_branch(BRANCH))
    expect("child suffix branch", lint_branch("cdat-04a/spread-query"))
    expect("child suffix commit", lint_commit("feat(cdat-04a): add the query"))
    expect("type branch", lint_branch("feat/cancel-order"), "not <id>/<slug>")
    expect("upper branch", lint_branch("API-03/cancel-order"), "not <id>/<slug>")
    expect("good commit", lint_commit(TITLE))
    expect("commit no scope", lint_commit("feat: add the cancel route"), "not '<type>(<id>)")
    expect("commit period", lint_commit(TITLE + "."), "period")
    expect("good pr", lint_pr(BRANCH, TITLE, GOOD_PR))
    expect("unsigned pr", lint_pr(BRANCH, TITLE, GOOD_PR.replace(SIGN, "")), "Created:")
    expect("pr id mismatch", lint_pr("api-04/cancel-order", TITLE, GOOD_PR), "differs")
    expect("pr no close", lint_pr(BRANCH, TITLE, GOOD_PR.replace("Closes #12\n", "")), "closing line")
    expect("pr no evidence", lint_pr(BRANCH, TITLE, GOOD_PR.replace("`pytest -q tests/test_cancel.py`", "tests")), "backticks")
    expect("pr no summary", lint_pr(BRANCH, TITLE, GOOD_PR.replace("## Why", "## Summary")), "no '## Why'")
    if failures:
        print("\n".join(failures))
        return 1
    print("package_lint self-test: ok")
    return 0


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--self-test":
        return self_test()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    issue = sub.add_parser("issue")
    issue.add_argument("--kind", choices=ISSUE_KINDS, required=True)
    issue.add_argument("--title", required=True)
    issue.add_argument("--label", action="append", default=[])
    issue.add_argument("--body-file", required=True)
    comment = sub.add_parser("comment")
    comment.add_argument("--kind", choices=COMMENT_KINDS, required=True)
    comment.add_argument("--body-file", required=True)
    sub.add_parser("catalog")
    sub.add_parser("templates")
    pr_body = sub.add_parser("pr-body")
    pr_body.add_argument("--body-file", required=True)
    branch = sub.add_parser("branch")
    branch.add_argument("name")
    commit = sub.add_parser("commit")
    commit.add_argument("line")
    pr = sub.add_parser("pr")
    pr.add_argument("--branch", required=True)
    pr.add_argument("--title", required=True)
    pr.add_argument("--body-file", required=True)
    try:
        args = parser.parse_args(argv)
    except SystemExit as stop:
        return 2 if stop.code else 0
    if args.cmd == "catalog":
        print(json.dumps(CATALOG, indent=2))
        return 0
    if args.cmd == "templates":
        for name in TEMPLATES:
            print(f"{name:<11} {template_path(name)}")
        return 0
    if args.cmd == "pr-body":
        problems = lint_pr_body(Path(args.body_file).read_text(encoding="utf-8"))
    elif args.cmd == "issue":
        problems = lint_issue(args.kind, args.title, args.label, Path(args.body_file).read_text(encoding="utf-8"))
    elif args.cmd == "comment":
        problems = lint_comment(args.kind, Path(args.body_file).read_text(encoding="utf-8"))
    elif args.cmd == "branch":
        problems = lint_branch(args.name)
    elif args.cmd == "commit":
        problems = lint_commit(args.line)
    else:
        problems = lint_pr(args.branch, args.title, Path(args.body_file).read_text(encoding="utf-8"))
    for problem in problems:
        print(problem)
    if not problems:
        print("package_lint: clean")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
