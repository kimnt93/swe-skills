#!/usr/bin/env python3
"""Install, update and remove the skill stack in any agent harness. Run it from a built stack (dist/<name>/).

    python3 scripts/install.py install   --agent claude --agent codex --agent omp    # plugins: /<name>:go-code, $<name>:go-code
    python3 scripts/install.py install   --agent opencode,hermes           # skills copied with the prefix: <name>-go-code
    python3 scripts/install.py install   --detected                        # every harness found on this machine
    python3 scripts/install.py install   --all --scope project --project-dir ~/code/app
    python3 scripts/install.py install   --dir ~/some/harness/skills      # any harness that reads a skills directory
    python3 scripts/install.py status | agents | uninstall --agent codex

How the `<name>:` name is produced
  * Claude Code, Codex and oh-my-pi (omp) support plugins, and a plugin's skills are namespaced `<plugin>:<skill>`: the repo is a plugin
    named `<name>`, so the skills appear as `/<name>:go-code` (Claude Code) and `$<name>:go-code` (Codex); omp loads them from
    the same marketplace (`omp plugin install <name>@<name>-skills`).
  * Harnesses without plugin namespaces (OpenCode, Hermes, Gemini CLI, Cursor, ...) require skill names of lower-case letters, digits and
    hyphens that equal the directory name, so a colon is impossible. The installer copies each skill as `<prefix>-<skill>` (default
    `<name>-go-code`), rewriting the `name:` field and the links between skills.
  * The router skill `<name>` keeps its own name everywhere, so the entry command is `/<name>` (Claude Code accepts a
    plugin skill named like its plugin as `/<name>`), `$<name>:<name>` (Codex), `/skill:<name>` (omp) and `<name>` elsewhere.
Every installed directory carries a `.<name>-install` marker; uninstall and updates touch only directories that have it.
Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILLS = REPO / "skills"
_STACK_FILE = REPO / "build.json"
if not _STACK_FILE.exists():
    sys.exit("install.py runs from a built stack: make build (or python3 scripts/build.py), then use dist/<name>/scripts/install.py")
STACK = json.loads(_STACK_FILE.read_text(encoding="utf-8"))
PLUGIN = STACK["name"]
MARKETPLACE = STACK["marketplace"]
MARKER = STACK["marker"]
ROUTER = STACK["router"]
IGNORED = shutil.ignore_patterns("__pycache__", "*.pyc", "target", ".pytest_cache", ".ruff_cache", ".venv", "node_modules", ".git")


@dataclass(frozen=True)
class Agent:
    label: str
    user: str  # global skills directory ("~" expanded)
    project: str  # project-relative skills directory
    commands: tuple[str, ...] = ()  # executables whose presence means "installed"
    home_dirs: tuple[str, ...] = ()  # directories whose presence means "installed"
    plugin: str = ""  # "claude" | "codex" | "omp": supports plugin install with a namespace
    subdir: str = ""  # extra category directory inside the skills directory (Hermes)


# Skill directories per harness. Sources: each harness's documentation, the directories present on a real machine
# (claude, codex, opencode, hermes) and the agent table of github.com/vercel-labs/skills for the others.
AGENTS: dict[str, Agent] = {
    "claude": Agent("Claude Code", "~/.claude/skills", ".claude/skills", ("claude",), ("~/.claude",), plugin="claude"),
    "codex": Agent("Codex", "~/.agents/skills", ".agents/skills", ("codex",), ("~/.codex",), plugin="codex"),
    "omp": Agent("oh-my-pi (omp)", "~/.omp/agent/skills", ".omp/skills", ("omp",), ("~/.omp",), plugin="omp"),
    "devin": Agent("Devin for Terminal", "~/.config/devin/skills", ".devin/skills", ("devin",), ("~/.config/devin",)),
    "opencode": Agent("OpenCode", "~/.config/opencode/skills", ".opencode/skills", ("opencode",), ("~/.config/opencode", "~/.opencode")),
    "hermes": Agent("Hermes Agent", "~/.hermes/skills", ".hermes/skills", ("hermes",), ("~/.hermes",), subdir=PLUGIN),
    "universal": Agent("Universal (.agents: Amp, Cline, Warp, Zed, Pi, Replit, ...)", "~/.agents/skills", ".agents/skills"),
    "amp": Agent("Amp", "~/.config/agents/skills", ".agents/skills", ("amp",), ("~/.config/amp",)),
    "gemini-cli": Agent("Gemini CLI", "~/.gemini/skills", ".agents/skills", ("gemini",), ("~/.gemini",)),
    "cursor": Agent("Cursor", "~/.cursor/skills", ".agents/skills", ("cursor-agent", "cursor"), ("~/.cursor",)),
    "github-copilot": Agent("GitHub Copilot", "~/.copilot/skills", ".agents/skills", ("copilot",), ("~/.copilot",)),
    "windsurf": Agent("Windsurf", "~/.codeium/windsurf/skills", ".windsurf/skills", ("windsurf",), ("~/.codeium/windsurf",)),
    "goose": Agent("Goose", "~/.config/goose/skills", ".goose/skills", ("goose",), ("~/.config/goose",)),
    "cline": Agent("Cline", "~/.agents/skills", ".agents/skills", ("cline",), ("~/.cline",)),
    "roo": Agent("Roo Code", "~/.roo/skills", ".roo/skills", (), ("~/.roo",)),
    "kilo": Agent("Kilo Code", "~/.kilo/skills", ".agents/skills", ("kilo",), ("~/.kilo",)),
    "droid": Agent("Droid (Factory)", "~/.factory/skills", ".agents/skills", ("droid",), ("~/.factory",)),
    "qwen-code": Agent("Qwen Code", "~/.qwen/skills", ".qwen/skills", ("qwen",), ("~/.qwen",)),
    "trae": Agent("Trae", "~/.trae/skills", ".trae/skills", (), ("~/.trae",)),
    "continue": Agent("Continue", "~/.continue/skills", ".continue/skills", (), ("~/.continue",)),
    "augment": Agent("Augment", "~/.augment/skills", ".augment/skills", ("auggie",), ("~/.augment",)),
    "crush": Agent("Crush", "~/.config/crush/skills", ".crush/skills", ("crush",), ("~/.config/crush",)),
    "junie": Agent("Junie", "~/.junie/skills", ".junie/skills", (), ("~/.junie",)),
    "kiro-cli": Agent("Kiro CLI", "~/.kiro/skills", ".kiro/skills", ("kiro-cli",), ("~/.kiro",)),
    "openhands": Agent("OpenHands", "~/.openhands/skills", ".openhands/skills", (), ("~/.openhands",)),
    "mistral-vibe": Agent("Mistral Vibe", "~/.vibe/skills", ".vibe/skills", ("vibe",), ("~/.vibe",)),
    "antigravity": Agent("Antigravity", "~/.gemini/antigravity/skills", ".agents/skills", (), ("~/.gemini/antigravity",)),
    "qoder": Agent("Qoder", "~/.qoder/skills", ".qoder/skills", (), ("~/.qoder",)),
    "codebuddy": Agent("CodeBuddy", "~/.codebuddy/skills", ".codebuddy/skills", (), ("~/.codebuddy",)),
    "iflow-cli": Agent("iFlow CLI", "~/.iflow/skills", ".iflow/skills", ("iflow",), ("~/.iflow",)),
    "openclaw": Agent("OpenClaw", "~/.openclaw/skills", "skills", ("openclaw",), ("~/.openclaw",)),
}


def home() -> Path:
    return Path(os.environ.get("PLUGIN_HOME") or Path.home())


def expand(path: str) -> Path:
    return home() / path[2:] if path.startswith("~/") else Path(path)


def skill_names(only: list[str] | None) -> list[str]:
    names = sorted(p.parent.name for p in SKILLS.glob("*/SKILL.md"))
    if only:
        unknown = sorted(set(only) - set(names))
        if unknown:
            sys.exit(f"unknown skill(s): {', '.join(unknown)} (see: make list)")
        names = [n for n in names if n in only]
    return names


def detected(agent: Agent) -> bool:
    return any(shutil.which(c) for c in agent.commands) or any(expand(d).exists() for d in agent.home_dirs)


def target_dir(agent: Agent, scope: str, project_dir: Path) -> Path:
    base = expand(agent.user) if scope == "user" else project_dir / agent.project
    return base / agent.subdir if agent.subdir else base


# ---------------------------------------------------------------------------------------------------------------------
# skills-directory install (copy with the prefix, or symlink without one)


def rewrite(skill_dir: Path, name: str, prefix: str, all_names: list[str]) -> None:
    """Prefix the `name:` field and the links between skills in the copied files."""
    others = [n for n in all_names if n != ROUTER]
    link = re.compile(r"\((\.\./)+(" + "|".join(map(re.escape, others)) + r")/")
    for md in skill_dir.rglob("*.md"):
        text = md.read_text(encoding="utf-8")
        if md.name == "SKILL.md" and md.parent == skill_dir and name != ROUTER:
            text = re.sub(r"^name:\s*.*$", f"name: {prefix}-{name}", text, count=1, flags=re.M)
        text = link.sub(lambda m: m.group(0).replace(f"/{m.group(2)}/", f"/{prefix}-{m.group(2)}/"), text)
        md.write_text(text, encoding="utf-8")


def install_skills(agent: Agent, scope: str, project_dir: Path, names: list[str], prefix: str, mode: str, dry: bool) -> int:
    base = target_dir(agent, scope, project_dir)
    all_names = skill_names(None)
    count = 0
    for name in names:
        dest = base / (f"{prefix}-{name}" if prefix and name != ROUTER else name)
        if dest.exists() or dest.is_symlink():
            if not (dest / MARKER).exists() and not dest.is_symlink():
                print(f"  skip {dest}: exists and was not installed by this tool")
                continue
            if not dry:
                shutil.rmtree(dest) if dest.is_dir() and not dest.is_symlink() else dest.unlink()
        print(f"  {'would install' if dry else 'install'} {dest.name}")
        if dry:
            count += 1
            continue
        base.mkdir(parents=True, exist_ok=True)
        if mode == "symlink":
            if prefix and name != ROUTER:
                sys.exit("--mode symlink needs --prefix '' (a prefixed skill must be rewritten, so it is copied)")
            dest.symlink_to(SKILLS / name, target_is_directory=True)
        else:
            shutil.copytree(SKILLS / name, dest, ignore=IGNORED)
            if prefix:
                rewrite(dest, name, prefix, all_names)
            (dest / MARKER).write_text(json.dumps({"source": str(REPO), "skill": name, "prefix": prefix}) + "\n", encoding="utf-8")
        count += 1
    return count


def prune_stale(agent: Agent, scope: str, project_dir: Path, prefix: str, dry: bool) -> int:
    """Remove directories this tool installed earlier for skills that were renamed or deleted since (or that used another prefix),
    so `make <harness>` after a rename/removal leaves exactly the current set. Foreign directories are never touched."""
    base = target_dir(agent, scope, project_dir)
    if not base.is_dir():
        return 0
    current = set(skill_names(None))
    removed = 0
    for entry in sorted(base.iterdir()):
        stale = False
        if entry.is_symlink():
            target = Path(os.readlink(entry))  # development symlinks into skills/: stale when the skill directory is gone
            stale = SKILLS in target.parents and not target.exists()
        elif (entry / MARKER).exists():
            try:
                meta = json.loads((entry / MARKER).read_text(encoding="utf-8"))
            except ValueError:
                meta = {}
            stale = meta.get("skill") not in current or meta.get("prefix", prefix) != prefix
        if stale:
            print(f"  {'would remove' if dry else 'remove'} {entry.name} (no longer in this repository)")
            if not dry:
                shutil.rmtree(entry) if entry.is_dir() and not entry.is_symlink() else entry.unlink()
            removed += 1
    return removed


def uninstall_skills(agent: Agent, scope: str, project_dir: Path, dry: bool) -> int:
    base = target_dir(agent, scope, project_dir)
    if not base.is_dir():
        return 0
    removed = 0
    names = skill_names(None)
    for entry in sorted(base.iterdir()):
        owned = (entry / MARKER).exists() or (entry.is_symlink() and entry.resolve().parent == SKILLS)
        if not owned:
            continue
        print(f"  {'would remove' if dry else 'remove'} {entry}")
        if not dry:
            shutil.rmtree(entry) if entry.is_dir() and not entry.is_symlink() else entry.unlink()
        removed += 1
    if not dry and agent.subdir and base.is_dir() and not any(base.iterdir()):
        base.rmdir()
    return removed


# ---------------------------------------------------------------------------------------------------------------------
# plugin install (Claude Code, Codex): the namespace `<name>:<skill>`


def run(cmd: list[str], dry: bool, check: bool = True) -> int:
    print("  $ " + " ".join(cmd))
    if dry:
        return 0
    result = subprocess.run(cmd, capture_output=True, text=True)
    for line in (result.stdout + result.stderr).strip().splitlines()[-4:]:
        print("    " + line)
    if check and result.returncode:
        print(f"  command failed ({result.returncode})")
    return result.returncode


def plugin_commands(agent: Agent, scope: str, action: str) -> list[list[str]]:
    tool = agent.plugin
    if tool == "claude":
        if action == "install":
            return [["claude", "plugin", "marketplace", "add", str(REPO)],
                    ["claude", "plugin", "install", f"{PLUGIN}@{MARKETPLACE}", "--scope", scope if scope == "user" else "project"]]
        return [["claude", "plugin", "uninstall", f"{PLUGIN}@{MARKETPLACE}"],
                ["claude", "plugin", "marketplace", "remove", MARKETPLACE]]
    if tool == "omp":
        if action == "install":
            listed = subprocess.run(["omp", "plugin", "marketplace", "list"], capture_output=True, text=True)
            known = MARKETPLACE in (listed.stdout + listed.stderr)
            # `add` fails when the name exists; refresh the catalog instead. `install --force` re-copies the plugin (a rename or
            # removal shows up without a version bump).
            first = ["omp", "plugin", "marketplace", "update", MARKETPLACE] if known else ["omp", "plugin", "marketplace", "add", str(REPO)]
            return [first, ["omp", "plugin", "install", "--force", "--scope", scope, f"{PLUGIN}@{MARKETPLACE}"]]
        return [["omp", "plugin", "uninstall", "--scope", scope, f"{PLUGIN}@{MARKETPLACE}"],
                ["omp", "plugin", "marketplace", "remove", MARKETPLACE]]
    if action == "install":  # codex
        return [["codex", "plugin", "marketplace", "add", str(REPO)], ["codex", "plugin", "add", f"{PLUGIN}@{MARKETPLACE}"]]
    return [["codex", "plugin", "remove", f"{PLUGIN}@{MARKETPLACE}"], ["codex", "plugin", "marketplace", "remove", MARKETPLACE]]


def plugin_state(agent: Agent) -> str:
    tool = agent.plugin
    if not shutil.which(tool):
        return "cli not found"
    out = subprocess.run([tool, "plugin", "list"], capture_output=True, text=True)
    text = out.stdout + out.stderr
    key = f"{PLUGIN}@{MARKETPLACE}"
    if key in text and "not installed" not in text.split(key, 1)[1].split("\n", 1)[0]:
        return "installed"
    return "not installed"


# ---------------------------------------------------------------------------------------------------------------------


def select_agents(args: argparse.Namespace) -> list[str]:
    chosen: list[str] = []
    for item in args.agent or []:
        chosen += [a.strip() for a in item.split(",") if a.strip()]
    if args.all:
        chosen = list(AGENTS)
    elif args.detected or not chosen:
        chosen += [key for key, a in AGENTS.items() if detected(a)]
        chosen = [c for c in chosen if c != "universal" or not args.detected]
    unknown = sorted(set(chosen) - set(AGENTS))
    if unknown:
        sys.exit(f"unknown agent(s): {', '.join(unknown)} (see: make agents)")
    seen: list[str] = []
    for key in chosen:
        if key not in seen:
            seen.append(key)
    # harnesses that share one directory (.agents/skills) install once
    return seen


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["install", "uninstall", "status", "agents"])
    parser.add_argument("--agent", action="append", help="harness name or comma list (see `agents`); repeatable")
    parser.add_argument("--all", action="store_true", help="every known harness")
    parser.add_argument("--detected", action="store_true", help="every harness found on this machine (default when no --agent)")
    parser.add_argument("--scope", choices=["user", "project"], default="user", help="user = global, project = ./<agent>/skills")
    parser.add_argument("--project-dir", default=".", help="project root for --scope project")
    parser.add_argument("--prefix", default=PLUGIN, help="skill name prefix for non-plugin installs ('' keeps the original names)")
    parser.add_argument("--mode", choices=["copy", "symlink"], default="copy", help="symlink needs --prefix '' (development)")
    parser.add_argument("--skill", action="append", help="only these skills (names without the prefix); repeatable or comma list")
    parser.add_argument("--plugin", choices=["auto", "yes", "no"], default="auto",
                        help="Claude Code / Codex: install as the namespaced plugin (auto: when the CLI exists)")
    parser.add_argument("--dir", help="install into this skills directory (any harness that reads one); skills are copied with --prefix")
    parser.add_argument("--names", action="store_true", help="with `agents`: print only the harness names (used by the Makefile)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.dir:
        AGENTS["custom"] = Agent("custom directory", args.dir, args.dir)
        args.agent = ["custom"]
    project_dir = Path(args.project_dir).expanduser().resolve()
    only = [s for item in (args.skill or []) for s in item.split(",") if s] or None

    if args.command == "agents":
        if args.names:
            print(" ".join(AGENTS))
            return 0
        for key, agent in AGENTS.items():
            mark = "detected" if detected(agent) else "        "
            kind = f"plugin {PLUGIN}:<skill> or " if agent.plugin else ""
            print(f"{key:15} {mark}  {kind}{agent.user}  (project: {agent.project})  {agent.label}")
        return 0

    agents = select_agents(args)
    if not agents:
        print("no harness detected: pass --agent <name> (see `agents`) or --all")
        return 1
    names = skill_names(only)
    exit_code = 0

    if args.command == "status":
        for key in agents:
            agent = AGENTS[key]
            base = target_dir(agent, args.scope, project_dir)
            owned = [e.name for e in base.iterdir() if (e / MARKER).exists()] if base.is_dir() else []
            plug = f"  plugin: {plugin_state(agent)}" if agent.plugin else ""
            print(f"{key:15} {len(owned):2} skill dir(s) in {base}{plug}")
        return 0

    done_dirs: set[Path] = set()
    for key in agents:
        agent = AGENTS[key]
        print(f"{key}: {agent.label}")
        use_plugin = agent.plugin and args.scope in ("user", "project") and (
            args.plugin == "yes" or (args.plugin == "auto" and shutil.which(agent.plugin)))
        if args.command == "install":
            if use_plugin:
                failed = False
                for cmd in plugin_commands(agent, args.scope, "install"):
                    failed |= bool(run(cmd, args.dry_run))
                exit_code |= failed
                if failed:
                    print(f"  -> {agent.label}: NOT installed (see the failed command above)")
                    continue
                hint = {"claude": f"/{PLUGIN} (and /{PLUGIN}:<skill>)", "codex": f"${PLUGIN}:{PLUGIN}", "omp": f"/skill:{PLUGIN} (plugin {PLUGIN})"}[agent.plugin]
                print(f"  -> enabled as {hint}")
                continue
            target = target_dir(agent, args.scope, project_dir)
            if target in done_dirs:
                print(f"  {target} already handled by another selected harness")
                continue
            done_dirs.add(target)
            n = install_skills(agent, args.scope, project_dir, names, args.prefix, args.mode, args.dry_run)
            gone = prune_stale(agent, args.scope, project_dir, args.prefix, args.dry_run)
            sep = f"{args.prefix}-" if args.prefix else ""
            print(f"  -> {n} skill(s) in {target}" + (f", {gone} stale removed" if gone else "") + f"; start with {ROUTER}, others as {sep}<skill>")
        else:
            if use_plugin:
                for cmd in plugin_commands(agent, args.scope, "uninstall"):
                    run(cmd, args.dry_run, check=False)
            target = target_dir(agent, args.scope, project_dir)
            if target in done_dirs:
                continue
            done_dirs.add(target)
            n = uninstall_skills(agent, args.scope, project_dir, args.dry_run)
            print(f"  -> removed {n} skill dir(s) from {target}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
