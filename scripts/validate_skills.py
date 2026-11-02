#!/usr/bin/env python3
"""Validate every skill against the rules the agent harnesses enforce.

    python3 scripts/validate_skills.py            # exit 0 = all valid

Checks per skills/<name>/SKILL.md:
  * frontmatter has `name` and `description`; `name` equals the directory name and matches ^[a-z0-9]+(-[a-z0-9]+)*$
    (1-64 chars: the Agent Skills / OpenCode / Codex rule, so no colon in the file: namespacing is added at install time)
  * description is 1-1024 characters (the OpenCode and Codex limit)
  * relative markdown links in every .md file of the skill (and `../other-skill/...`) resolve
  * every `references/*.md` file is linked from the skill's SKILL.md (the router), and every `assets/...`, `scripts/...`, `references/...` path
    mentioned in backticks in SKILL.md or a reference exists
  * harness-neutral text: no Cursor- or pstack-specific terms (tool names, .cursor/ paths, model slugs) outside `upstream:` lines
  * a skill listed in UPSTREAM declares `metadata.upstream`
  * every `**name** skill` names a skill of this stack and every `**name** principle` a file in principles/references/
  * no skill sets disable-model-invocation (the router must be able to run every skill)
  * metadata.group is one of start, process, language, data, platform, observability (the router index groups by it)
  * a built stack (build.json present) has no @PLACEHOLDER@ left
Standard library only.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # falls back to a line parser (install PyYAML for the strict check)
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
PATH_RE = re.compile(r"`((?:assets|references|scripts)/[^`\s]+)`")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)#\s]+)(?:#[^)]*)?\)")
NON_PORTABLE = re.compile(
    r"\.cursor/|AskQuestion|subagent_type: ?\"(?:generalPurpose|poteto-agent)|pstack-models|poteto-mode|/setup-pstack"
    r"|\bgrok-[0-9]|claude-opus-5-5-|run_in_background|environment: \"cloud\"|cursor-team-kit|\bBugbot\b"
)
SKILL_REF = re.compile(r"\*\*([a-z0-9-]+)\*\* skill")
PRINCIPLE_REF = re.compile(r"\*\*([a-z0-9-]+)\*\* principle")
PLACEHOLDER = re.compile(r"@(?:STACK|SKILL_INDEX|MARKETPLACE|VERSION|OWNER|TITLE|HOMEPAGE|DESCRIPTION)@")
UPSTREAM = (ROOT / "UPSTREAM").read_text(encoding="utf-8") if (ROOT / "UPSTREAM").exists() else ""
BUILT = (ROOT / "build.json").exists()
GROUPS = ("start", "process", "language", "data", "platform", "observability")

def frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        return {}
    if yaml is not None:  # real YAML: catches `#` comments and `: ` that silently truncate or break a value
        try:
            loaded = yaml.safe_load(match.group(1))
        except yaml.YAMLError as exc:
            return {"_error": str(exc).splitlines()[0]}
        return {k: str(v) for k, v in loaded.items()} if isinstance(loaded, dict) else {}
    data: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if re.match(r"^[A-Za-z_][\w-]*:", line):
            key, _, value = line.partition(":")
            value = value.strip()
            if value[:1] in "\"'" and value[-1:] == value[:1]:
                value = value[1:-1]
            data[key] = value
    return data


def main() -> int:
    errors: list[str] = []
    names = []
    for skill_md in sorted(SKILLS.glob("*/SKILL.md")):
        directory = skill_md.parent
        name = directory.name
        names.append(name)
        meta = frontmatter(skill_md.read_text(encoding="utf-8"))
        where = f"skills/{name}"
        if "_error" in meta:
            errors.append(f"{where}: frontmatter is not valid YAML ({meta['_error']})")
            continue
        raw = re.search(r"^description:\s*(.*)$", skill_md.read_text(encoding="utf-8"), re.M)
        if raw and not raw.group(1).startswith(("\"", "'", ">", "|")) and (" #" in raw.group(1) or ": " in raw.group(1)):
            errors.append(f"{where}: unquoted description contains ' #' or ': ' (YAML would cut or reject it): quote it")
        if meta.get("name") != name:
            errors.append(f"{where}: frontmatter name {meta.get('name')!r} must equal the directory name")
        if not NAME_RE.match(name) or not 1 <= len(name) <= 64:
            errors.append(f"{where}: name must match {NAME_RE.pattern} and be 1-64 characters")
        description = meta.get("description", "")
        if not description:
            errors.append(f"{where}: description is required")
        elif len(description) > 1024:
            errors.append(f"{where}: description is {len(description)} characters (max 1024)")
        text = skill_md.read_text(encoding="utf-8")
        for doc in sorted(directory.rglob("*.md")):
            for target in LINK_RE.findall(doc.read_text(encoding="utf-8")):
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                if not (doc.parent / target).resolve().exists():
                    errors.append(f"{where}/{doc.relative_to(directory)}: broken link {target}")
        for ref in sorted((directory / "references").glob("*.md")) if (directory / "references").is_dir() else []:
            if f"references/{ref.name}" not in text:
                errors.append(f"{where}: references/{ref.name} is not linked from SKILL.md (the agent would never find it)")
        docs = [skill_md] + (sorted((directory / "references").glob("*.md")) if (directory / "references").is_dir() else [])
        for doc in docs:
            for path in PATH_RE.findall(doc.read_text(encoding="utf-8")):
                path = path.rstrip(".,:;")
                if any(ch in path for ch in "<{*") or "..." in path or path.startswith(("scripts/health.sh", "scripts/check_deploy")):
                    continue
                if not (directory / path).exists() and not (directory / path.rstrip("/")).exists():
                    errors.append(f"{where}: {doc.name} mentions missing path {path}")
    known = set(names)
    principles = {p.stem for p in (SKILLS / "principles" / "references").glob("*.md")} if (SKILLS / "principles").is_dir() else set()
    for skill_md in sorted(SKILLS.glob("*/SKILL.md")):
        directory = skill_md.parent
        where = f"skills/{directory.name}"
        meta_text = re.match(r"^---\n(.*?)\n---\n", skill_md.read_text(encoding="utf-8"), re.S)
        group = re.search(r"^  group:\s*(\S+)", meta_text.group(1), re.M) if meta_text else None
        if meta_text and re.search(r"^disable-model-invocation:\s*true", meta_text.group(1), re.M):
            errors.append(f"{where}: disable-model-invocation stops the router (and agents) from running this skill")
        if not group or group.group(1) not in GROUPS:
            errors.append(f"{where}: metadata.group must be one of {', '.join(GROUPS)}")
        if re.search(rf"^skills/{re.escape(directory.name)}\s", UPSTREAM, re.M) and not (meta_text and "upstream:" in meta_text.group(1)):
            errors.append(f"{where}: forked skill (listed in UPSTREAM) needs metadata.upstream")
        for doc in sorted(directory.rglob("*.md")):
            for number, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1):
                at = f"{where}/{doc.relative_to(directory)}:{number}"
                if NON_PORTABLE.search(line) and "upstream:" not in line:
                    errors.append(f"{at}: Cursor/pstack-specific term; use tiers and the router's harness reference")
                for ref in SKILL_REF.findall(line):
                    if ref not in known:
                        errors.append(f"{at}: **{ref}** skill is not in this stack")
                for ref in PRINCIPLE_REF.findall(line):
                    if principles and ref not in principles:
                        errors.append(f"{at}: **{ref}** principle has no file in principles/references/")
                if BUILT and PLACEHOLDER.search(line):
                    errors.append(f"{at}: placeholder left after the build")
    for message in errors:
        print("ERROR", message)
    print(f"{len(names)} skills checked, {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
