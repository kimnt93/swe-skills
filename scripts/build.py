#!/usr/bin/env python3
"""Render the plugin into dist/<PLUGIN_NAME>/, ready to install or publish.

    python3 scripts/build.py                  # settings: env > plugin.local.env > plugin.env (name default: swe)
    PLUGIN_NAME=acme python3 scripts/build.py

What the build does:
  * copies src/skills into dist/<name>/skills and renames the router skill `router` to <name>, so the
    entry command is /<name> (Claude Code), $<name>:<name> (Codex), /skill:<name> (omp), <name> (Hermes, ...)
  * fills @PLUGIN@, @DOMAIN@, @OWNER@ and @HOMEPAGE@ in every text file of the skills and the agents,
    and @SKILL_INDEX@ (grouped by metadata.group) in the router
  * sets each Claude Code subagent's `model:` from the config.yaml template (`swe-cli models subagent <name>`)
  * renders the plugin manifests from src/manifests, dropping fields left empty
  * copies the installer, the validator and CHANGELOG.md, and writes build.json,
    LICENSE and README.md
  * fails when a placeholder is left, or the name is not a valid skill name or collides with a skill
"""

from __future__ import annotations

import json
import os
import subprocess
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ROUTER = "router"
GROUPS = (
    ("start", "Start here"),
    ("process", "Process and proof"),
    ("language", "Languages"),
    ("data", "Data"),
    ("platform", "API and deployment"),
    ("observability", "Observability"),
)
KEYS = ("PLUGIN_NAME", "PLUGIN_TITLE", "PLUGIN_OWNER", "PLUGIN_VERSION", "PLUGIN_HOMEPAGE", "PLUGIN_DESCRIPTION", "PLUGIN_DOMAIN")
PLACEHOLDER = re.compile(r"@(?:PLUGIN|DOMAIN|OWNER|HOMEPAGE|SKILL_INDEX|MARKETPLACE|VERSION|TITLE|DESCRIPTION)@")
IGNORED = shutil.ignore_patterns("__pycache__", "*.pyc", "target", ".pytest_cache", ".ruff_cache", ".venv", "node_modules")


def settings() -> dict[str, str]:
    values: dict[str, str] = {}
    for env_file in (ROOT / "plugin.env", ROOT / "plugin.local.env"):
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                match = re.match(r"^\s*([A-Z_]+)\s*\??=\s*(.*?)\s*$", line)
                if match and not line.lstrip().startswith("#"):
                    values[match.group(1)] = match.group(2)
    for key in KEYS:
        if os.environ.get(key):
            values[key] = os.environ[key]
    values.setdefault("PLUGIN_NAME", "swe")
    values.setdefault("PLUGIN_TITLE", values["PLUGIN_NAME"].replace("-", " ").title())
    values.setdefault("PLUGIN_DOMAIN", "example.com")
    values.setdefault("PLUGIN_OWNER", values["PLUGIN_NAME"])
    if not values.get("PLUGIN_HOMEPAGE"):
        values["PLUGIN_HOMEPAGE"] = f"https://{values['PLUGIN_DOMAIN']}/{values['PLUGIN_NAME']}"
    return values


def drop_empty(value):
    if isinstance(value, dict):
        return {k: drop_empty(v) for k, v in value.items() if v not in ("", None)}
    if isinstance(value, list):
        return [drop_empty(v) for v in value]
    return value


def subagent_model(name: str) -> str:
    fleet = ROOT / "cli" / "bin" / "main"
    if not fleet.exists():
        return "inherit"
    result = subprocess.run([sys.executable, str(fleet), "models", "subagent", name], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else "inherit"


def description(skill_md: Path) -> str:
    """The skill's one-line summary (metadata.summary), for the index tables."""
    match = re.search(r'^  summary:\s*"(.*)"\s*$', skill_md.read_text(encoding="utf-8"), re.M)
    if not match:
        sys.exit(f"build: {skill_md.parent.name} has no metadata.summary")
    return match.group(1).replace("|", "/")


def group(skill_md: Path) -> str:
    match = re.search(r"^  group:\s*(\S+)", skill_md.read_text(encoding="utf-8"), re.M)
    return match.group(1) if match else ""


def skill_index(skills: Path, name: str) -> str:
    known = [key for key, _ in GROUPS]
    by_group: dict[str, list[Path]] = {key: [] for key in known}
    for skill_md in sorted(skills.glob("*/SKILL.md")):
        key = group(skill_md)
        if key not in by_group:
            sys.exit(f"build: {skill_md.parent.name} has metadata.group {key!r}; use one of {', '.join(known)}")
        by_group[key].append(skill_md)
    lines = []
    for key, title in GROUPS:
        if not by_group[key]:
            continue
        lines += [f"**{title}**", "", "| Skill | Claude Code | Codex | omp, Hermes, others | What it is for |",
                  "|---|---|---|---|---|"]
        for skill_md in by_group[key]:
            skill = skill_md.parent.name
            claude = f"`/{name}`" if skill == name else f"`/{name}:{skill}`"
            codex = f"`${name}:{skill}`"
            other = f"`{name}`" if skill == name else f"`{name}-{skill}`"
            text = description(skill_md).replace("@PLUGIN@", name)
            lines.append(f"| `{skill}` | {claude} | {codex} | {other} | {text} |")
        lines.append("")
    return "\n".join(lines).rstrip()


def read_text(path: Path) -> str | None:
    """The file's text, or None for a binary file (any file that is not NUL-free UTF-8)."""
    data = path.read_bytes()
    if b"\0" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def substitute(path: Path, mapping: dict[str, str], json_escape: bool = False) -> None:
    text = read_text(path)
    if text is None:
        return
    for key, value in mapping.items():
        text = text.replace(key, json.dumps(value)[1:-1] if json_escape else value)
    path.write_text(text, encoding="utf-8")


LICENSE = """MIT License

Copyright (c) 2026 {owner}

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

README = """# {title} plugin (`{name}`)

{description}

This directory is a built plugin. Do not edit it: change `src/` in {source} and run `make build`.

## Use

Start every non-trivial task with the router. Called with no request, it prints the stack.

| Harness | Entry | Any other skill |
|---|---|---|
| Claude Code | `/{name} <task>` | `/{name}:<skill>` |
| Codex | `${name}:{name} <task>` | `${name}:<skill>` |
| oh-my-pi (omp) | `/skill:{name} <task>` | `/skill:<skill>` |
| Hermes, OpenCode, Gemini CLI, others | skill `{name}` | skill `{name}-<skill>` |

Claude Code subagents shipped with the plugin: {agents}.

## Install

```bash
# plugin harnesses, from this directory
claude plugin marketplace add "$PWD" && claude plugin install {name}@{marketplace}
codex plugin marketplace add "$PWD" && codex plugin add {name}@{marketplace}
omp plugin marketplace add "$PWD" && omp plugin install {name}@{marketplace}
# any harness, plugin or copied skills (see: python3 scripts/install.py agents)
python3 scripts/install.py install --agent claude --agent hermes
python3 scripts/install.py uninstall --agent hermes
# try without installing (Claude Code)
claude --plugin-dir "$PWD"
```

## Skills ({count})

{index}
"""


def main() -> int:
    cfg = settings()
    name = cfg["PLUGIN_NAME"]
    if not NAME_RE.match(name) or len(name) > 64:
        sys.exit(f"build: PLUGIN_NAME {name!r} must match {NAME_RE.pattern} (it becomes the plugin and the entry skill)")
    sources = sorted(p.parent.name for p in (SRC / "skills").glob("*/SKILL.md"))
    if name in sources and name != ROUTER:
        sys.exit(f"build: PLUGIN_NAME {name!r} collides with the skill src/skills/{name}")
    if ROUTER not in sources:
        sys.exit(f"build: the router src/skills/{ROUTER}/SKILL.md is missing")

    dist = ROOT / "dist" / name
    if dist.exists():
        shutil.rmtree(dist)
    skills = dist / "skills"
    shutil.copytree(SRC / "skills", skills, ignore=IGNORED)
    (skills / ROUTER).rename(skills / name)

    mapping = {
        "@PLUGIN@": name,
        "@DOMAIN@": cfg["PLUGIN_DOMAIN"],
        "@OWNER@": cfg["PLUGIN_OWNER"],
        "@HOMEPAGE@": cfg["PLUGIN_HOMEPAGE"],
    }
    for path in skills.rglob("*"):
        if path.is_file():
            substitute(path, mapping)
    router = skills / name / "SKILL.md"
    text = router.read_text(encoding="utf-8")
    text = re.sub(r"^name:\s*.*$", f"name: {name}", text, count=1, flags=re.M)
    text = text.replace("@SKILL_INDEX@", skill_index(skills, name))
    router.write_text(text, encoding="utf-8")

    manifest_map = {
        "@PLUGIN@": name,
        "@MARKETPLACE@": f"{name}-skills",
        "@VERSION@": cfg.get("PLUGIN_VERSION", "0.0.0"),
        "@OWNER@": cfg.get("PLUGIN_OWNER", ""),
        "@TITLE@": cfg["PLUGIN_TITLE"],
        "@HOMEPAGE@": cfg.get("PLUGIN_HOMEPAGE", ""),
        "@DESCRIPTION@": cfg.get("PLUGIN_DESCRIPTION", ""),
    }
    for template in (SRC / "manifests").rglob("*.json"):
        target = dist / template.relative_to(SRC / "manifests")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(template, target)
        substitute(target, manifest_map, json_escape=True)
        data = drop_empty(json.loads(target.read_text(encoding="utf-8")))
        target.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    agents = SRC / "agents"
    if agents.is_dir():
        shutil.copytree(agents, dist / "agents", ignore=IGNORED)
        for path in (dist / "agents").glob("*.md"):
            substitute(path, mapping)
            text = path.read_text(encoding="utf-8")
            model = subagent_model(path.stem)
            text = re.sub(r"^model:.*\n", "", text, flags=re.M)
            text = re.sub(r"^(name:.*\n)", rf"\1model: {model}\n", text, count=1, flags=re.M)
            path.write_text(text, encoding="utf-8")

    (dist / "scripts").mkdir()
    for script in ("install.py", "validate_skills.py"):
        shutil.copy2(ROOT / "scripts" / script, dist / "scripts" / script)
    for extra in ("CHANGELOG.md",):
        source = ROOT / extra
        if source.is_dir():
            shutil.copytree(source, dist / extra)
        elif source.exists():
            shutil.copy2(source, dist / extra)

    stack = {
        "name": name,
        "title": cfg["PLUGIN_TITLE"],
        "marketplace": f"{name}-skills",
        "marker": f".{name}-install",
        "router": name,
        "version": cfg.get("PLUGIN_VERSION", "0.0.0"),
        "domain": cfg["PLUGIN_DOMAIN"],
        "agents": sorted(p.stem for p in (dist / "agents").glob("*.md")) if (dist / "agents").is_dir() else [],
        "skills": sorted(p.parent.name for p in skills.glob("*/SKILL.md")),
    }
    (dist / "build.json").write_text(json.dumps(stack, indent=2) + "\n", encoding="utf-8")
    owner = cfg.get("PLUGIN_OWNER", "")
    (dist / "LICENSE").write_text(LICENSE.format(owner=owner or name), encoding="utf-8")
    agent_names = sorted(p.stem for p in (dist / "agents").glob("*.md")) if (dist / "agents").is_dir() else []
    (dist / "README.md").write_text(README.format(
        title=cfg["PLUGIN_TITLE"], name=name, marketplace=f"{name}-skills", source=ROOT.name,
        description=cfg.get("PLUGIN_DESCRIPTION", ""), count=len(list(skills.glob("*/SKILL.md"))),
        agents=", ".join(f"`{name}:{a}`" for a in agent_names) or "none",
        index=skill_index(skills, name),
    ), encoding="utf-8")

    left = [str(p.relative_to(dist)) for p in dist.rglob("*")
            if p.is_file() and PLACEHOLDER.search(read_text(p) or "")]
    left = [p for p in left if not p.startswith("scripts/")]
    if left:
        sys.exit("build: placeholders left in " + ", ".join(left))
    print(f"built dist/{name}: {len(stack['skills'])} skills, entry /{name}, marketplace {stack['marketplace']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
