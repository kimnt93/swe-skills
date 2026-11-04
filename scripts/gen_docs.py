#!/usr/bin/env python3
"""Generate docs/skills.md (the skill reference, from the skills' own frontmatter and references) and
docs/harnesses.md (every supported harness, from the installer's table), and check that docs/skills/*.md
has a section for every skill, router playbook and principle (and none for anything that is gone).

    python3 scripts/gen_docs.py            write both files
    python3 scripts/gen_docs.py --check    exit 1 when either is out of date (make test runs it)

The text is the default plugin name's (plugin.env); replace `swe` with your PLUGIN_NAME.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "src" / "skills"
OUT = ROOT / "docs" / "skills.md"
OUT_HARNESS = ROOT / "docs" / "harnesses.md"
INSTALLER = ROOT / "scripts" / "install.py"
DETAIL = ROOT / "docs" / "skills"
HEADING = re.compile(r"^### ([a-z0-9-]+)\s*$", re.M)
GROUPS = (
    ("start", "Start here"),
    ("process", "Process and proof"),
    ("language", "Languages"),
    ("data", "Data"),
    ("platform", "API and deployment"),
    ("observability", "Observability"),
)


def plugin_name() -> str:
    for env_file in (ROOT / "plugin.env",):
        for line in env_file.read_text(encoding="utf-8").splitlines():
            match = re.match(r"^\s*PLUGIN_NAME\s*\??=\s*(\S+)", line)
            if match:
                return match.group(1)
    return "swe"


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    block = re.match(r"^---\n(.*?)\n---\n", text, re.S).group(1)
    description = re.search(r'^description:\s*"?(.*?)"?\s*$', block, re.M).group(1).replace('\\"', '"')
    group = re.search(r"^  group:\s*(\S+)", block, re.M).group(1)
    return {"description": description, "group": group}


def detail_index() -> tuple[dict[str, Path], list[str]]:
    """name -> detail page, from the `### name` headings of docs/skills/*.md; plus duplicate names."""
    found: dict[str, Path] = {}
    duplicates = []
    for page in sorted(DETAIL.glob("*.md")):
        for name in HEADING.findall(page.read_text(encoding="utf-8")):
            if name in found:
                duplicates.append(name)
            found[name] = page
    return found, duplicates


def required_names() -> set[str]:
    """Every skill, router playbook and principle must have a section in the detail pages."""
    names = {p.parent.name for p in SKILLS.glob("*/SKILL.md")}
    names |= {p.stem for p in (SKILLS / "router" / "references").glob("*.md") if p.stem not in ("models", "harness")}
    names |= {p.stem for p in (SKILLS / "principles" / "references").glob("*.md")}
    return names


def detail_problems() -> list[str]:
    found, duplicates = detail_index()
    required = required_names()
    problems = [f"docs/skills: no section for '{n}' (add '### {n}' to a page)" for n in sorted(required - set(found))]
    problems += [f"docs/skills/{found[n].name}: '### {n}' names nothing that exists" for n in sorted(set(found) - required)]
    problems += [f"docs/skills: '### {n}' appears twice" for n in sorted(set(duplicates))]
    return problems


def title(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            return line.lstrip("# ").strip()
    return path.stem


def summary(skill: str) -> str:
    text = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
    match = re.search(r'^  summary:\s*"(.*)"\s*$', text, re.M)
    if not match:
        sys.exit(f"gen_docs: {skill} has no metadata.summary")
    return match.group(1)


def group_tables(link, level: int = 3) -> str:
    """The skills by group, each group a heading and a `Skill | Description` table; the name links to `link(skill)`."""
    name = plugin_name()
    skills = {p.parent.name: frontmatter(p) for p in sorted(SKILLS.glob("*/SKILL.md"))}
    hashes = "#" * level
    out = [f"{len(skills)} skills in {len(GROUPS)} groups. Click a skill for its detail.", ""]
    for key, label in GROUPS:
        names = [s for s in skills if skills[s]["group"] == key]
        out += [f"{hashes} {label}", "", "| Skill | Description |", "|---|---|"]
        for skill in names:
            shown = name if skill == "router" else skill
            out.append(f"| [{shown}]({link(skill)}) | {summary(skill)} |")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def inject(path: Path, block: str) -> str:
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(r"(<!-- skills:start -->\n).*?(<!-- skills:end -->)", re.S)
    if not pattern.search(text):
        sys.exit(f"gen_docs: {path.relative_to(ROOT)} has no <!-- skills:start --> ... <!-- skills:end --> markers")
    return pattern.sub(lambda m: m.group(1) + block + m.group(2), text)


def detail_link(base: str):
    def link(skill: str) -> str:
        page = detail_index()[0].get(skill)
        return f"{base}{page.name}#{skill}" if page else f"{base}README.md"
    return link


def render() -> str:
    name = plugin_name()
    skills = {p.parent.name: p.parent for p in sorted(SKILLS.glob("*/SKILL.md"))}
    info = {skill: frontmatter(path / "SKILL.md") for skill, path in skills.items()}
    out = [
        "# Skill reference",
        "",
        f"Every skill of the plugin, from its own `SKILL.md`. Invocation, with the default plugin name `{name}`"
        f" (replace it with your `PLUGIN_NAME`):",
        "",
        f"| Harness | Router | Another skill |",
        "|---|---|---|",
        f"| Claude Code | `/{name} <task>` | `/{name}:<skill> <task>` |",
        f"| oh-my-pi | `/skill:{name} <task>` | `/skill:<skill> <task>` (`/skill:{name}/<skill>` on a name clash) |",
        f"| Codex | `${name}:{name} <task>` | `${name}:<skill>` |",
        f"| Hermes and others | skill `{name}` | skill `{name}-<skill>` |",
        "",
        "Agents load skills by their descriptions, so a plain request usually finds the right one; name a",
        "skill when you want a specific one. What each skill does, step by step, is in [skills/](skills/README.md).",
        "Generated by `scripts/gen_docs.py`: do not edit by hand.",
        "",
        "## Index",
        "",
        "@@INDEX@@",
    ]
    for key, label in GROUPS:
        names = [s for s in skills if info[s]["group"] == key]
        out += [f"## {label}", ""]
        for skill in names:
            shown = name if skill == "router" else skill
            out += [f"### {'router' if skill == 'router' else skill}", ""]
            out.append(info[skill]["description"].replace("@PLUGIN@", name))
            out.append("")
            out.append(f"- **Invoke:** `/{name}`" if skill == "router" else f"- **Invoke:** `/{name}:{shown}`")
            page = detail_index()[0].get(skill)
            if page:
                out.append(f"- **Detail:** [{page.name}](skills/{page.name}#{skill}) · **Source:** [SKILL.md](../src/skills/{skill}/SKILL.md)")
            refs = sorted((skills[skill] / "references").glob("*.md")) if (skills[skill] / "references").is_dir() else []
            if refs:
                out.append("- **References:**")
                for ref in refs:
                    label_ref = title(ref).replace("@PLUGIN@", name)
                    out.append(f"  - `references/{ref.name}`: {label_ref}")
            for sub in ("scripts", "assets"):
                folder = skills[skill] / sub
                if folder.is_dir():
                    entries = sorted(e.name for e in folder.iterdir() if not e.name.startswith((".", "__")))
                    out.append(f"- **{sub.capitalize()}:** " + ", ".join(f"`{e}`" for e in entries))
            out.append("")
    text = "\n".join(out).rstrip() + "\n"
    return text.replace("@@INDEX@@", group_tables(lambda skill: "#" + skill, level=3).rstrip())


def harnesses() -> list[dict]:
    """The installer's AGENTS table, read from its source (it needs a built stack to import)."""
    tree = ast.parse(INSTALLER.read_text(encoding="utf-8"))
    table = next(n.value for n in ast.walk(tree) if isinstance(n, ast.AnnAssign)
                 and getattr(n.target, "id", "") == "AGENTS")
    rows = []
    for key, call in zip(table.keys, table.values):
        args = [ast.literal_eval(a) if not isinstance(a, ast.Name) else "" for a in call.args]
        kwargs = {k.arg: (ast.literal_eval(k.value) if not isinstance(k.value, ast.Name) else "<plugin>") for k in call.keywords}
        rows.append({"key": ast.literal_eval(key), "label": args[0], "user": args[1], "project": args[2],
                     "plugin": kwargs.get("plugin", ""), "subdir": kwargs.get("subdir", "")})
    return rows


def render_harnesses() -> str:
    name = plugin_name()
    rows = harnesses()
    out = [
        "# Harnesses",
        "",
        f"The plugin installs into {len(rows)} agent harnesses with one command each: `make <harness>` (several at once:",
        "`make claude codex omp hermes`; everything found on the machine: `make install`; remove: add `REMOVE=1`).",
        "Generated from the installer's table by `scripts/gen_docs.py`: do not edit by hand.",
        "",
        "## Plugin harnesses",
        "",
        f"Claude Code, Codex and oh-my-pi install the plugin from `dist/{name}` through their marketplace, so skills are",
        f"namespaced and the plugin updates in place on rebuild.",
        "",
        "| Harness | Install | Router | Another skill | Extras |",
        "|---|---|---|---|---|",
        f"| Claude Code | `make claude` | `/{name} <task>` | `/{name}:<skill>` | subagents `{name}:worker`, `{name}:adversary` |",
        f"| Codex | `make codex` | `${name}:{name} <task>` | `${name}:<skill>` | |",
        f"| oh-my-pi | `make omp` | `/skill:{name} <task>` | `/skill:<skill>` | omp's own subagent roles |",
        "",
        "## Skill-directory harnesses",
        "",
        f"Every other harness reads a directory of `<skill>/SKILL.md` folders. The installer copies each skill as",
        f"`{name}-<skill>` (the router keeps the name `{name}`) and rewrites `name:` and the links between skills,",
        "because the Agent Skills format needs `name` to equal the directory, with no colon. Agents load a skill by",
        f"its description, so a plain request finds the right one; name `{name}` to start the router explicitly.",
        "",
        "| Harness | Install | User skills directory | Project skills directory (`SCOPE=project`) |",
        "|---|---|---|---|",
    ]
    for row in rows:
        if row["plugin"]:
            continue
        subdir = f"/{name}" if row["subdir"] else ""
        out.append(f"| {row['label']} | `make {row['key']}` | `{row['user']}{subdir}` | `{row['project']}` |")
    out += [
        "",
        "Options for any target: `SCOPE=project PROJECT_DIR=~/code/app` (commit the skills with the repo),",
        "`PREFIX=acme` (another prefix), `SKILLS=\"go-code py-code\"` (a subset), `PLUGIN=no` (copy skills even for",
        "Claude Code, Codex and omp), `DRY_RUN=1` (show what would happen). A harness that is not listed:",
        "`make custom DIR=<its skills directory>`.",
        "",
        "## Which harness does what",
        "",
        "| Use | Harnesses |",
        "|---|---|",
        "| interactive coding with the skills | all of the above |",
        f"| a **delegated session** (unattended, started by a project manager with `swe-cli delegate`) | Claude Code (`claude`) and oh-my-pi (`omp`) |",
        "| the **project's own agents** (root, project managers) | Hermes Agent (`make hermes` also copies the skills for its profiles) |",
        "",
        "Codex and the other harnesses use the same skills by hand; workflows drive only the coding CLIs.",
        "A new coding CLI needs a branch in `cli/bin/main` (`argv`) and an entry under `clis:` and",
        "`workers:` in `cli/models.yaml`.",
        "",
        "## Check an install",
        "",
        "```bash",
        "make status                    # what is installed, per detected harness",
        "make claude DRY_RUN=1          # what a target would do",
        f"bash tests/harness_test.sh     # installs into all {len(rows)} harnesses in a scratch home",
        "```",
    ]
    return "\n".join(out) + "\n"


def main() -> int:
    problems = detail_problems()
    for problem in problems:
        print("PROBLEM", problem)
    if problems:
        return 1
    outputs = {
        OUT: render(),
        OUT_HARNESS: render_harnesses(),
        ROOT / "README.md": inject(ROOT / "README.md", group_tables(detail_link("docs/skills/"), level=3)),
        DETAIL / "README.md": inject(DETAIL / "README.md", group_tables(detail_link(""), level=3)),
    }
    if "--check" in sys.argv[1:]:
        stale = [path for path, text in outputs.items() if not path.exists() or path.read_text(encoding="utf-8") != text]
        for path in stale:
            print(f"{path.relative_to(ROOT)} is out of date: run python3 scripts/gen_docs.py")
        if not stale:
            print("docs/skills.md and docs/harnesses.md are up to date")
        return 1 if stale else 0
    for path, text in outputs.items():
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)} ({text.count(chr(10))} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
