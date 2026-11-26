#!/usr/bin/env python3
"""
discover_agents.py
Lists the coding CLIs (harnesses) installed on this machine and the Orca CLI that runs them. It starts nothing.
The id Orca takes as --agent is Orca's own: `orca orchestration worker-start --help` says which it knows.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from typing import Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import delegate  # noqa: E402

KNOWN_AGENTS = {
    "codex": {
        "name": "OpenAI Codex CLI",
        "binaries": ["codex"],
        "description": "OpenAI Codex CLI agent for terminal coding and automation."
    },
    "claude": {
        "name": "Claude Code",
        "binaries": ["claude"],
        "description": "Anthropic Claude Code CLI for terminal-based engineering."
    },
    "omp": {
        "name": "Oh My Pi",
        "binaries": ["omp"],
        "description": "Oh My Pi interactive coding agent."
    },
    "pi": {
        "name": "Pi Coding Agent",
        "binaries": ["pi"],
        "description": "Pi command-line coding agent."
    },
    "agy": {
        "name": "Google Antigravity CLI",
        "binaries": ["agy"],
        "description": "Google Antigravity autonomous coding agent CLI."
    },
    "opencode": {
        "name": "OpenCode",
        "binaries": ["opencode"],
        "description": "OpenCode agent CLI."
    },
    "devin": {
        "name": "Devin CLI",
        "binaries": ["devin"],
        "description": "Devin AI software engineer CLI."
    },
    "kiro": {
        "name": "Kiro CLI",
        "binaries": ["kiro-cli", "kiro"],
        "description": "Kiro spec-driven AI development CLI."
    },
    "grok": {
        "name": "xAI Grok Build CLI",
        "binaries": ["grok", "xai"],
        "description": "xAI Grok terminal-native coding agent."
    },
    "cursor": {
        "name": "Cursor Agent",
        "binaries": ["cursor-agent", "cursor"],
        "description": "Cursor IDE CLI coding agent."
    },
    "deepseek": {
        "name": "DeepSeek Harness",
        "binaries": ["dsh", "deepseek"],
        "description": "DeepSeek Harness runtime and agent engine."
    },
    "muse": {
        "name": "Meta Muse Code",
        "binaries": ["muse", "muse-code"],
        "description": "Meta Muse Code software engineering agent."
    },
    "hermes": {
        "name": "Hermes Agent",
        "binaries": ["hermes-agent", "hermes"],
        "description": "Hermes autonomous task & engineering agent."
    },
    "commandcode": {
        "name": "Command Code",
        "binaries": ["cmd", "commandcode"],
        "description": "Command Code CLI implementer agent."
    },
    "copilot": {
        "name": "GitHub Copilot CLI",
        "binaries": ["copilot", "gh-copilot"],
        "description": "GitHub Copilot developer assistant."
    },
    "kimi": {
        "name": "Kimi Code",
        "binaries": ["kimi"],
        "description": "Moonshot Kimi Code CLI agent."
    },
    "zcode": {
        "name": "Z.AI ZCode",
        "binaries": ["zcode"],
        "description": "Z.AI ZCode command-line coding agent."
    },
    "qwen": {
        "name": "Alibaba Qwen Code",
        "binaries": ["qwen", "qwen-code"],
        "description": "Alibaba Qwen Code terminal coding agent."
    },
    "aider": {
        "name": "Aider",
        "binaries": ["aider"],
        "description": "Aider command-line AI pair programmer."
    },
    "cline": {
        "name": "Cline CLI",
        "binaries": ["cline"],
        "description": "Cline autonomous coding assistant CLI."
    },
    "qoder": {
        "name": "Qoder CLI",
        "binaries": ["qoder"],
        "description": "Qoder developer assistant CLI."
    }
}

ADDITIONAL_SEARCH_DIRS = [
    os.path.expanduser("~/.local/bin"),
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
    """The same rule delegate.py uses: never a bare 'orca' outside an Orca terminal."""
    try:
        return delegate.orca_command(which=find_binary)
    except delegate.TABLE.Stop:
        return None

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
            "binary_path": resolved_path
        }
        if resolved_path:
            detected[agent_id] = info
        else:
            missing[agent_id] = info
    orca_path = resolve_orca_cli()
    return {
        "orca": {
            "available": orca_path is not None,
            "binary_path": orca_path,
            "in_orca_env": bool(os.environ.get("TERM_PROGRAM") == "Orca" or os.environ.get("ORCA_AGENT_PANE"))
        },
        "detected_agents": detected,
        "missing_agents": missing
    }

def main() -> int:
    if "--self-test" in sys.argv:
        res = discover_agents()
        assert set(res) == {"orca", "detected_agents", "missing_agents"}
        every = {**res["detected_agents"], **res["missing_agents"]}
        assert set(every) == set(KNOWN_AGENTS)
        assert all(set(x) == {"id", "name", "description", "installed", "binary_path"} for x in every.values())
        print("discover_agents self-test passed")
        return 0

    as_json = "--json" in sys.argv
    result = discover_agents()
    if as_json:
        print(json.dumps(result, indent=2))
        return 0

    print("=== AI Coding Agent Discovery ===")
    print(f"Orca CLI: {'Available (' + str(result['orca']['binary_path']) + ')' if result['orca']['available'] else 'Not found'}")
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
