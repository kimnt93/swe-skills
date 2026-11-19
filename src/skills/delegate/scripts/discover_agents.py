#!/usr/bin/env python3
"""
discover_agents.py
Scans PATH and standard user installation directories to discover available AI coding agent CLIs,
as well as orchestration engines (Orca and T3 Code).
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from typing import Dict, Optional

KNOWN_AGENTS = {
    "codex": {
        "name": "OpenAI Codex CLI",
        "binaries": ["codex"],
        "direct_command": ["codex", "exec", "{brief}"],
        "orca_command": "codex",
        "description": "OpenAI Codex CLI agent for terminal coding and automation."
    },
    "claude": {
        "name": "Claude Code",
        "binaries": ["claude"],
        "direct_command": ["claude", "-p", "{brief}"],
        "orca_command": "claude",
        "description": "Anthropic Claude Code CLI for terminal-based engineering."
    },
    "omp": {
        "name": "Oh My Pi",
        "binaries": ["omp"],
        "direct_command": ["omp", "--prompt", "{brief}"],
        "orca_command": "omp",
        "description": "Oh My Pi interactive coding agent."
    },
    "pi": {
        "name": "Pi Coding Agent",
        "binaries": ["pi"],
        "direct_command": ["pi", "-p", "{brief}"],
        "orca_command": "pi",
        "description": "Pi command-line coding agent."
    },
    "agy": {
        "name": "Google Antigravity CLI",
        "binaries": ["agy"],
        "direct_command": ["agy", "-p", "{brief}"],
        "orca_command": "agy",
        "description": "Google Antigravity autonomous coding agent CLI."
    },
    "opencode": {
        "name": "OpenCode",
        "binaries": ["opencode"],
        "direct_command": ["opencode", "exec", "{brief}"],
        "orca_command": "opencode",
        "description": "OpenCode agent CLI."
    },
    "devin": {
        "name": "Devin CLI",
        "binaries": ["devin"],
        "direct_command": ["devin", "run", "{brief}"],
        "orca_command": "devin",
        "description": "Devin AI software engineer CLI."
    },
    "kiro": {
        "name": "Kiro CLI",
        "binaries": ["kiro-cli", "kiro"],
        "direct_command": ["kiro-cli", "-p", "{brief}"],
        "orca_command": "kiro-cli",
        "description": "Kiro spec-driven AI development CLI."
    },
    "grok": {
        "name": "xAI Grok Build CLI",
        "binaries": ["grok", "xai"],
        "direct_command": ["grok", "-p", "{brief}"],
        "orca_command": "grok",
        "description": "xAI Grok terminal-native coding agent."
    },
    "cursor": {
        "name": "Cursor Agent",
        "binaries": ["cursor-agent", "cursor"],
        "direct_command": ["cursor-agent", "{brief}"],
        "orca_command": "cursor-agent",
        "description": "Cursor IDE CLI coding agent."
    },
    "deepseek": {
        "name": "DeepSeek Harness",
        "binaries": ["dsh", "deepseek"],
        "direct_command": ["dsh", "exec", "{brief}"],
        "orca_command": "dsh",
        "description": "DeepSeek Harness runtime and agent engine."
    },
    "muse": {
        "name": "Meta Muse Code",
        "binaries": ["muse", "muse-code"],
        "direct_command": ["muse", "exec", "{brief}"],
        "orca_command": "muse",
        "description": "Meta Muse Code software engineering agent."
    },
    "hermes": {
        "name": "Hermes Agent",
        "binaries": ["hermes-agent", "hermes"],
        "direct_command": ["hermes-agent", "{brief}"],
        "orca_command": "hermes-agent",
        "description": "Hermes autonomous task & engineering agent."
    },
    "commandcode": {
        "name": "Command Code",
        "binaries": ["cmd", "commandcode"],
        "direct_command": ["cmd", "{brief}"],
        "orca_command": "cmd",
        "description": "Command Code CLI implementer agent."
    },
    "copilot": {
        "name": "GitHub Copilot CLI",
        "binaries": ["copilot", "gh-copilot"],
        "direct_command": ["copilot", "-p", "{brief}"],
        "orca_command": "copilot",
        "description": "GitHub Copilot developer assistant."
    },
    "kimi": {
        "name": "Kimi Code",
        "binaries": ["kimi"],
        "direct_command": ["kimi", "-p", "{brief}"],
        "orca_command": "kimi",
        "description": "Moonshot Kimi Code CLI agent."
    },
    "zcode": {
        "name": "Z.AI ZCode",
        "binaries": ["zcode"],
        "direct_command": ["zcode", "{brief}"],
        "orca_command": "zcode",
        "description": "Z.AI ZCode command-line coding agent."
    },
    "qwen": {
        "name": "Alibaba Qwen Code",
        "binaries": ["qwen", "qwen-code"],
        "direct_command": ["qwen", "-p", "{brief}"],
        "orca_command": "qwen",
        "description": "Alibaba Qwen Code terminal coding agent."
    },
    "aider": {
        "name": "Aider",
        "binaries": ["aider"],
        "direct_command": ["aider", "--message", "{brief}", "--no-git"],
        "orca_command": "aider",
        "description": "Aider command-line AI pair programmer."
    },
    "cline": {
        "name": "Cline CLI",
        "binaries": ["cline"],
        "direct_command": ["cline", "-p", "{brief}"],
        "orca_command": "cline",
        "description": "Cline autonomous coding assistant CLI."
    },
    "qoder": {
        "name": "Qoder CLI",
        "binaries": ["qoder"],
        "direct_command": ["qoder", "{brief}"],
        "orca_command": "qoder",
        "description": "Qoder developer assistant CLI."
    }
}

ADDITIONAL_SEARCH_DIRS = [
    os.path.expanduser("~/.local/bin"),
    os.path.expanduser("~/.t3/bin"),
    os.path.expanduser("~/.grok/bin"),
    os.path.expanduser("~/.cargo/bin"),
    os.path.expanduser("~/.npm-global/bin"),
    "/usr/local/bin",
    "/usr/bin"
]

def find_binary(binary_name: str) -> Optional[str]:
    for directory in ADDITIONAL_SEARCH_DIRS:
        candidate = os.path.join(directory, binary_name)
        if os.path.lexists(candidate):
            return candidate
    return shutil.which(binary_name)

def resolve_orca_cli() -> Optional[str]:
    if os.environ.get("ORCA_CLI_COMMAND"):
        candidate = os.environ["ORCA_CLI_COMMAND"]
        if os.path.lexists(candidate):
            return candidate
    if os.environ.get("ORCA_DEV_REPO_ROOT"):
        hit = find_binary("orca-dev")
        if hit:
            return hit
    hit_ide = find_binary("orca-ide")
    if hit_ide:
        return hit_ide
    in_orca = bool(os.environ.get("TERM_PROGRAM") == "Orca" or os.environ.get("ORCA_AGENT_PANE"))
    if in_orca:
        hit_orca = find_binary("orca")
        if hit_orca:
            return hit_orca
    return hit_ide or find_binary("orca")

def resolve_t3_cli() -> Optional[str]:
    if os.environ.get("T3_CLI_COMMAND"):
        candidate = os.environ["T3_CLI_COMMAND"]
        if os.path.lexists(candidate):
            return candidate
    return find_binary("t3") or find_binary("t3code")

def discover_agents() -> Dict:
    detected = {}
    missing = {}
    for agent_id, meta in KNOWN_AGENTS.items():
        resolved_path = None
        for b in meta["binaries"]:
            hit = find_binary(b)
            if hit:
                resolved_path = hit
                break
        info = {
            "id": agent_id,
            "name": meta["name"],
            "description": meta["description"],
            "installed": resolved_path is not None,
            "binary_path": resolved_path,
            "direct_command": meta["direct_command"],
            "orca_command": meta["orca_command"]
        }
        if resolved_path:
            detected[agent_id] = info
        else:
            missing[agent_id] = info
    orca_path = resolve_orca_cli()
    t3_path = resolve_t3_cli()
    return {
        "orca": {
            "available": orca_path is not None,
            "binary_path": orca_path,
            "in_orca_env": bool(os.environ.get("TERM_PROGRAM") == "Orca" or os.environ.get("ORCA_AGENT_PANE"))
        },
        "t3": {
            "available": t3_path is not None,
            "binary_path": t3_path
        },
        "detected_agents": detected,
        "missing_agents": missing
    }

def main() -> int:
    if "--self-test" in sys.argv:
        res = discover_agents()
        assert "orca" in res and "t3" in res and "detected_agents" in res
        print("discover_agents self-test passed")
        return 0

    as_json = "--json" in sys.argv
    result = discover_agents()
    if as_json:
        print(json.dumps(result, indent=2))
        return 0

    print("=== AI Coding Agent Discovery ===")
    print(f"Orca CLI: {'Available (' + str(result['orca']['binary_path']) + ')' if result['orca']['available'] else 'Not found'}")
    print(f"T3 Code CLI: {'Available (' + str(result['t3']['binary_path']) + ')' if result['t3']['available'] else 'Not found'}")
    print("\n--- Installed Agent CLIs ---")
    if result["detected_agents"]:
        for aid, data in result["detected_agents"].items():
            print(f"  • {data['name']} (`{aid}`): {data['binary_path']}")
    else:
        print("  (No known agent CLIs found in PATH)")
    print("\n--- Other Supported Agents ---")
    for aid, data in result["missing_agents"].items():
        print(f"  - {data['name']} (`{aid}`)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
