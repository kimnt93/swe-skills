#!/usr/bin/env python3
"""
delegate.py
Universal multi-agent delegation runner supporting Orca CLI sessions, T3 Code threads,
and direct headless CLI relays.

Supports:
  - Multi-engine dispatch: --engine [auto|orca|t3|cli]
  - Model selection (--model / -m)
  - Reasoning effort controls (--reasoning / -r)
  - YOLO mode (auto-accept tool permissions, enabled by DEFAULT)
  - Verification test gate execution (--verify)
  - Structured output adhering to delegate-relay.result.v1
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_VERSION = "delegate-relay.result.v1"

AGENT_CLI_MAPPINGS = {
    "codex": {
        "binary": "codex",
        "headless_args": ["exec"],
        "model_flag": "--model",
        "reasoning_flag": "--reasoning-effort",
        "yolo_flags": ["--dangerously-skip-permissions"],
        "orca_cmd": "codex",
        "t3_model": "o3-mini"
    },
    "claude": {
        "binary": "claude",
        "headless_args": ["-p"],
        "model_flag": "--model",
        "reasoning_flag": None,
        "yolo_flags": ["--dangerously-skip-permissions"],
        "orca_cmd": "claude",
        "t3_model": "claude-3-7-sonnet"
    },
    "omp": {
        "binary": "omp",
        "headless_args": ["--prompt"],
        "model_flag": "--model",
        "reasoning_flag": None,
        "yolo_flags": ["--dangerously-skip-permissions"],
        "orca_cmd": "omp",
        "t3_model": "google-antigravity/gemini-2.5-flash"
    },
    "pi": {
        "binary": "pi",
        "headless_args": ["-p"],
        "model_flag": "--model",
        "reasoning_flag": None,
        "yolo_flags": ["--yolo"],
        "orca_cmd": "pi",
        "t3_model": "pi"
    },
    "agy": {
        "binary": "agy",
        "headless_args": ["-p"],
        "model_flag": "--model",
        "reasoning_flag": None,
        "yolo_flags": ["--dangerously-skip-permissions"],
        "orca_cmd": "agy",
        "t3_model": "gemini-2.5-flash"
    },
    "opencode": {
        "binary": "opencode",
        "headless_args": ["exec"],
        "model_flag": "--model",
        "reasoning_flag": None,
        "yolo_flags": ["--yolo"],
        "orca_cmd": "opencode",
        "t3_model": "opencode"
    },
    "devin": {
        "binary": "devin",
        "headless_args": ["run"],
        "model_flag": "--model",
        "reasoning_flag": None,
        "yolo_flags": ["--yolo"],
        "orca_cmd": "devin",
        "t3_model": "devin"
    },
    "kiro": {
        "binary": "kiro-cli",
        "fallback_binaries": ["kiro"],
        "headless_args": ["-p"],
        "model_flag": "--model",
        "reasoning_flag": None,
        "yolo_flags": ["--dangerously-skip-permissions"],
        "orca_cmd": "kiro-cli",
        "t3_model": "kiro"
    },
    "grok": {
        "binary": "grok",
        "fallback_binaries": ["xai"],
        "headless_args": ["-p"],
        "model_flag": "--model",
        "reasoning_flag": None,
        "yolo_flags": ["--dangerously-skip-permissions"],
        "orca_cmd": "grok",
        "t3_model": "grok-beta"
    },
    "cursor": {
        "binary": "cursor-agent",
        "fallback_binaries": ["cursor"],
        "headless_args": [],
        "model_flag": "--model",
        "reasoning_flag": None,
        "yolo_flags": ["--yolo"],
        "orca_cmd": "cursor-agent",
        "t3_model": "cursor"
    },
    "deepseek": {
        "binary": "dsh",
        "fallback_binaries": ["deepseek"],
        "headless_args": ["exec"],
        "model_flag": "--model",
        "reasoning_flag": None,
        "yolo_flags": ["--yolo"],
        "orca_cmd": "dsh",
        "t3_model": "deepseek-r1"
    },
    "muse": {
        "binary": "muse",
        "fallback_binaries": ["muse-code"],
        "headless_args": ["exec"],
        "model_flag": "--model",
        "reasoning_flag": None,
        "yolo_flags": ["--dangerously-skip-permissions"],
        "orca_cmd": "muse",
        "t3_model": "muse"
    },
    "hermes": {
        "binary": "hermes-agent",
        "fallback_binaries": ["hermes"],
        "headless_args": [],
        "model_flag": "--model",
        "reasoning_flag": None,
        "yolo_flags": ["--yolo"],
        "orca_cmd": "hermes-agent",
        "t3_model": "hermes"
    },
    "commandcode": {
        "binary": "cmd",
        "fallback_binaries": ["commandcode"],
        "headless_args": [],
        "model_flag": "--model",
        "reasoning_flag": None,
        "yolo_flags": ["--yolo"],
        "orca_cmd": "cmd",
        "t3_model": "commandcode"
    },
    "copilot": {
        "binary": "copilot",
        "fallback_binaries": ["gh-copilot"],
        "headless_args": ["-p"],
        "model_flag": "--model",
        "reasoning_flag": None,
        "yolo_flags": ["--allow-all"],
        "orca_cmd": "copilot",
        "t3_model": "copilot"
    },
    "kimi": {
        "binary": "kimi",
        "headless_args": ["-p"],
        "model_flag": "--model",
        "reasoning_flag": None,
        "yolo_flags": ["--yolo"],
        "orca_cmd": "kimi",
        "t3_model": "kimi"
    },
    "zcode": {
        "binary": "zcode",
        "headless_args": [],
        "model_flag": "--model",
        "reasoning_flag": None,
        "yolo_flags": ["--yolo"],
        "orca_cmd": "zcode",
        "t3_model": "zcode"
    },
    "qwen": {
        "binary": "qwen",
        "fallback_binaries": ["qwen-code"],
        "headless_args": ["-p"],
        "model_flag": "--model",
        "reasoning_flag": None,
        "yolo_flags": ["--yolo"],
        "orca_cmd": "qwen",
        "t3_model": "qwen-2.5-coder-32b"
    },
    "aider": {
        "binary": "aider",
        "headless_args": ["--message", "--no-git"],
        "model_flag": "--model",
        "reasoning_flag": None,
        "yolo_flags": ["--yes-always"],
        "orca_cmd": "aider",
        "t3_model": "aider"
    },
    "cline": {
        "binary": "cline",
        "headless_args": ["-p"],
        "model_flag": "--model",
        "reasoning_flag": None,
        "yolo_flags": ["--yolo"],
        "orca_cmd": "cline",
        "t3_model": "cline"
    },
    "qoder": {
        "binary": "qoder",
        "headless_args": [],
        "model_flag": "--model",
        "reasoning_flag": None,
        "yolo_flags": ["--yolo"],
        "orca_cmd": "qoder",
        "t3_model": "qoder"
    }
}

ADDITIONAL_BIN_DIRS = [
    os.path.expanduser("~/.local/bin"),
    os.path.expanduser("~/.t3/bin"),
    os.path.expanduser("~/.grok/bin"),
    os.path.expanduser("~/.cargo/bin"),
    os.path.expanduser("~/.npm-global/bin"),
    "/usr/local/bin",
    "/usr/bin"
]

def find_executable(name: str) -> Optional[str]:
    for directory in ADDITIONAL_BIN_DIRS:
        candidate = os.path.join(directory, name)
        if os.path.lexists(candidate):
            return candidate
    return shutil.which(name)

def get_config_search_paths() -> list[Path]:
    paths: list[Path] = []
    env_cfg = os.environ.get("SWE_CONFIG")
    if env_cfg:
        paths.append(Path(env_cfg))
    paths.append(Path("./config.json"))
    paths.append(Path(__file__).resolve().parents[2] / "config.json")
    paths.append(Path(__file__).resolve().parents[3] / "config.json")

    home = Path.home()
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            paths.append(Path(appdata) / "swe" / "config.json")
        paths.append(home / ".config" / "swe" / "config.json")
    elif sys.platform == "darwin":
        paths.append(home / "Library" / "Application Support" / "swe" / "config.json")
        paths.append(home / ".config" / "swe" / "config.json")
    else:
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            paths.append(Path(xdg_config) / "swe" / "config.json")
        paths.append(home / ".config" / "swe" / "config.json")
    return paths

def load_config() -> dict[str, Any]:
    for path in get_config_search_paths():
        if path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return {}

def resolve_orca_cli() -> Optional[str]:
    if os.environ.get("ORCA_CLI_COMMAND"):
        candidate = os.environ["ORCA_CLI_COMMAND"]
        if os.path.lexists(candidate):
            return candidate
    if os.environ.get("ORCA_DEV_REPO_ROOT"):
        hit = find_executable("orca-dev")
        if hit:
            return hit
    hit_ide = find_executable("orca-ide")
    if hit_ide:
        return hit_ide
    in_orca = bool(os.environ.get("TERM_PROGRAM") == "Orca" or os.environ.get("ORCA_AGENT_PANE"))
    if in_orca:
        hit_orca = find_executable("orca")
        if hit_orca:
            return hit_orca
    return hit_ide or find_executable("orca")

def resolve_t3_cli() -> Optional[str]:
    if os.environ.get("T3_CLI_COMMAND"):
        candidate = os.environ["T3_CLI_COMMAND"]
        if os.path.lexists(candidate):
            return candidate
    return find_executable("t3") or find_executable("t3code")

def get_git_diff_stat(cwd: str) -> str:
    try:
        proc = subprocess.run(["git", "diff", "--stat"], cwd=cwd, capture_output=True, text=True, check=False)
        return proc.stdout.strip()
    except Exception:
        return ""

def get_touched_files(cwd: str) -> List[str]:
    try:
        proc = subprocess.run(["git", "status", "--porcelain"], cwd=cwd, capture_output=True, text=True, check=False)
        files = []
        for line in proc.stdout.splitlines():
            line = line.strip()
            if line:
                parts = line.split(maxsplit=1)
                if len(parts) == 2:
                    files.append(parts[1])
        return files
    except Exception:
        return []

def run_verification(cmd_str: Optional[str], cwd: str) -> Optional[Dict]:
    if not cmd_str:
        return None
    try:
        proc = subprocess.run(cmd_str, shell=True, cwd=cwd, capture_output=True, text=True, timeout=120)
        return {
            "command": cmd_str,
            "passed": proc.returncode == 0,
            "output": (proc.stdout + "\n" + proc.stderr).strip()[-1000:]
        }
    except subprocess.TimeoutExpired:
        return {
            "command": cmd_str,
            "passed": False,
            "output": "Verification timed out after 120s"
        }
    except Exception as e:
        return {
            "command": cmd_str,
            "passed": False,
            "output": f"Error running verification: {str(e)}"
        }

def execute_orca_session(orca_bin: str, agent: str, brief: str, timeout_sec: int, cwd: str) -> Tuple[int, str]:
    agent_info = AGENT_CLI_MAPPINGS.get(agent, {})
    cmd_name = agent_info.get("orca_cmd", agent)
    create_proc = subprocess.run(
        [orca_bin, "terminal", "create", "--worktree", "active", "--command", cmd_name, "--json"],
        cwd=cwd, capture_output=True, text=True, check=False
    )
    if create_proc.returncode != 0:
        return 1, f"Failed to create Orca terminal: {create_proc.stderr or create_proc.stdout}"
    send_proc = subprocess.run(
        [orca_bin, "terminal", "send", "--worktree", "active", "--text", brief, "--enter", "--json"],
        cwd=cwd, capture_output=True, text=True, check=False
    )
    if send_proc.returncode != 0:
        return 1, f"Failed to send brief to Orca terminal: {send_proc.stderr or send_proc.stdout}"
    timeout_ms = timeout_sec * 1000
    wait_proc = subprocess.run(
        [orca_bin, "terminal", "wait", "--for", "tui-idle", "--timeout-ms", str(timeout_ms), "--json"],
        cwd=cwd, capture_output=True, text=True, check=False
    )
    read_proc = subprocess.run(
        [orca_bin, "terminal", "read", "--worktree", "active", "--lines", "200", "--json"],
        cwd=cwd, capture_output=True, text=True, check=False
    )
    output_text = read_proc.stdout
    try:
        parsed = json.loads(read_proc.stdout)
        if isinstance(parsed, dict) and "result" in parsed and "text" in parsed["result"]:
            output_text = parsed["result"]["text"]
    except Exception:
        pass
    if wait_proc.returncode != 0:
        return 124, f"Orca terminal wait timed out or failed:\n{output_text}"
    return 0, output_text

def execute_t3_thread(t3_bin: str, agent: str, model: Optional[str], brief: str, timeout_sec: int, cwd: str) -> Tuple[int, str]:
    agent_info = AGENT_CLI_MAPPINGS.get(agent, {})
    chosen_model = model or agent_info.get("t3_model")
    cmd = [t3_bin, "thread", "start", "--wait", "--json"]
    if chosen_model:
        cmd.extend(["--model", chosen_model])
    cmd.extend([cwd, brief])
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout_sec)
        out = (proc.stdout + "\n" + proc.stderr).strip()
        return proc.returncode, out
    except subprocess.TimeoutExpired:
        return 124, f"T3 Code thread execution timed out after {timeout_sec}s"
    except Exception as exc:
        return 1, f"Failed to run T3 thread: {exc}"

def execute_direct_cli(agent: str, model: Optional[str], reasoning: Optional[str], yolo: bool, brief: str, timeout_sec: int, cwd: str) -> Tuple[int, str]:
    agent_info = AGENT_CLI_MAPPINGS.get(agent)
    if not agent_info:
        return 1, f"Unknown agent: {agent}"
    binary = find_executable(agent_info["binary"])
    if not binary:
        for fb in agent_info.get("fallback_binaries", []):
            hit = find_executable(fb)
            if hit:
                binary = hit
                break
    if not binary:
        return 1, f"Binary for agent '{agent}' ({agent_info['binary']}) not found in PATH."
    cmd = [binary]
    cmd.extend(agent_info.get("headless_args", []))
    if yolo and agent_info.get("yolo_flags"):
        cmd.extend(agent_info["yolo_flags"])
    if model and agent_info.get("model_flag"):
        cmd.extend([agent_info["model_flag"], model])
    if reasoning and agent_info.get("reasoning_flag"):
        cmd.extend([agent_info["reasoning_flag"], reasoning])
    cmd.append(brief)
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout_sec)
        out = (proc.stdout + "\n" + proc.stderr).strip()
        return proc.returncode, out
    except subprocess.TimeoutExpired:
        return 124, f"Direct CLI execution timed out after {timeout_sec}s"
    except Exception as exc:
        return 1, f"Direct CLI execution failed: {exc}"

def self_test() -> int:
    cfg = load_config()
    assert isinstance(cfg, dict)
    assert "codex" in AGENT_CLI_MAPPINGS
    assert "claude" in AGENT_CLI_MAPPINGS
    assert "omp" in AGENT_CLI_MAPPINGS
    paths = get_config_search_paths()
    assert len(paths) >= 2
    print("delegate.py self-test passed")
    return 0

def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()

    parser = argparse.ArgumentParser(description="Multi-engine task delegation runner.")
    parser.add_argument("--agent", "-a", help="Target agent (e.g. codex, claude, omp, pi)")
    parser.add_argument("--engine", "-e", choices=["auto", "orca", "t3", "cli"], default=None,
                        help="Execution engine: orca, t3, cli, or auto (default)")
    parser.add_argument("--brief", "-b", help="File containing the brief, or literal brief string")
    parser.add_argument("--model", "-m", help="Model slug to override default")
    parser.add_argument("--reasoning", "-r", help="Reasoning effort (low, medium, high)")
    parser.add_argument("--verify", "-v", help="Verification command (e.g. make verify, npm test)")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout in seconds (default: 300)")
    parser.add_argument("--cwd", default=os.getcwd(), help="Working directory for delegation")
    parser.add_argument("--no-yolo", action="store_true", help="Disable auto-approval / YOLO mode")
    parser.add_argument("--json", action="store_true", help="Output result strictly in JSON")
    parser.add_argument("--dry-run", action="store_true", help="Print dispatch plan without executing")

    args = parser.parse_args()
    config = load_config()

    agent = args.agent or config.get("default_agent", "codex")
    engine = args.engine or config.get("default_engine") or config.get("delegation", {}).get("engine", "auto")
    yolo = not args.no_yolo and config.get("delegation", {}).get("yolo", True)
    timeout_sec = args.timeout or int(config.get("delegation", {}).get("timeout_ms", 300000) / 1000)

    brief_content = ""
    if args.brief:
        if os.path.isfile(args.brief):
            with open(args.brief, "r", encoding="utf-8") as f:
                brief_content = f.read()
        else:
            brief_content = args.brief
    else:
        if not sys.stdin.isatty():
            brief_content = sys.stdin.read()
        else:
            brief_content = "Execute current assigned card task."

    if args.dry_run:
        plan = {
            "agent": agent,
            "engine": engine,
            "model": args.model,
            "reasoning": args.reasoning,
            "yolo": yolo,
            "timeout_sec": timeout_sec,
            "brief_preview": brief_content[:200]
        }
        print(json.dumps(plan, indent=2))
        return 0

    chosen_engine = engine
    orca_bin = resolve_orca_cli()
    t3_bin = resolve_t3_cli()
    if chosen_engine == "auto":
        if bool(os.environ.get("TERM_PROGRAM") == "Orca" or os.environ.get("ORCA_AGENT_PANE")) and orca_bin:
            chosen_engine = "orca"
        elif t3_bin:
            chosen_engine = "t3"
        elif orca_bin:
            chosen_engine = "orca"
        else:
            chosen_engine = "cli"

    start_time = time.time()
    exit_code = 0
    output_text = ""
    resolved_mode = "direct_cli"

    if chosen_engine == "orca" and orca_bin:
        resolved_mode = "orca_session"
        exit_code, output_text = execute_orca_session(orca_bin, agent, brief_content, timeout_sec, args.cwd)
    elif chosen_engine == "t3" and t3_bin:
        resolved_mode = "t3_thread"
        exit_code, output_text = execute_t3_thread(t3_bin, agent, args.model, brief_content, timeout_sec, args.cwd)
    else:
        resolved_mode = "direct_cli"
        exit_code, output_text = execute_direct_cli(agent, args.model, args.reasoning, yolo, brief_content, timeout_sec, args.cwd)

    execution_time_ms = int((time.time() - start_time) * 1000)
    touched_files = get_touched_files(args.cwd)
    diff_stat = get_git_diff_stat(args.cwd)
    verification_result = run_verification(args.verify, args.cwd)

    status = "success"
    if exit_code == 124:
        status = "timeout"
    elif exit_code != 0:
        status = "error"

    result = {
        "schema": SCHEMA_VERSION,
        "agent": agent,
        "mode": resolved_mode,
        "status": status,
        "exitCode": exit_code,
        "executionTimeMs": execution_time_ms,
        "touchedFiles": touched_files,
        "diffStat": diff_stat,
        "verification": verification_result,
        "summary": output_text[-2000:].strip() if output_text else "No output captured."
    }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"[{status.upper()}] Agent {agent} finished in {execution_time_ms}ms (exit code {exit_code})")
        if touched_files:
            print("Touched files:")
            for f in touched_files:
                print(f"  • {f}")
        if diff_stat:
            print(f"Diff stat:\n{diff_stat}")
        if verification_result:
            pass_str = "PASSED" if verification_result["passed"] else "FAILED"
            print(f"Verification ({verification_result['command']}): {pass_str}")
    return exit_code

if __name__ == "__main__":
    sys.exit(main())
