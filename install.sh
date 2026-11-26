#!/usr/bin/env bash
# ==============================================================================
# swe-skills Installer
# Installs swe-skills across all detected AI agent harnesses.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/kimnt93/swe-skills/main/install.sh | bash
#   curl -fsSL ... | bash -s -- --version v1.0.0
#   ./install.sh [--harness all|antigravity|claude|codex|omp|orca] [--uninstall]
# ==============================================================================

set -e

PLUGIN_NAME="${PLUGIN_NAME:-swe}"
REPO="${REPO:-kimnt93/swe-skills}"
GITHUB_URL="https://github.com/${REPO}"
INSTALL_BASE="${HOME}/.local/share/${PLUGIN_NAME}-skills"
BIN_DIR="${HOME}/.local/bin"

VERSION="latest"
TARGET_HARNESS="auto"
DRY_RUN=false
UNINSTALL=false

# ANSI colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}==>${NC} ${BOLD}$1${NC}"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_warn() { echo -e "${YELLOW}Warning:${NC} $1"; }
log_error() { echo -e "${RED}Error:${NC} $1" >&2; }

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --version|-v)
      VERSION="$2"
      shift 2
      ;;
    --harness|-h)
      TARGET_HARNESS="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --uninstall)
      UNINSTALL=true
      shift
      ;;
    --all)
      TARGET_HARNESS="all"
      shift
      ;;
    --help)
      echo "${PLUGIN_NAME}-skills installer"
      echo "Usage: install.sh [options]"
      echo "  --version <tag>    Install specific release version (default: latest)"
      echo "  --harness <name>   Target specific harness: auto, all, antigravity, claude, codex, omp, orca"
      echo "  --all              Install into all known harnesses"
      echo "  --dry-run          Preview install steps without changing files"
      echo "  --uninstall        Remove installed skills, binaries, and harness links"
      exit 0
      ;;
    *)
      log_warn "Unknown argument: $1"
      shift
      ;;
  esac
done

# ------------------------------------------------------------------------------
# Check for local directory vs remote release download
# ------------------------------------------------------------------------------
SOURCE_DIR=""
CURRENT_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || true)"

if [ -f "${CURRENT_SCRIPT_DIR}/scripts/build.py" ] && [ -d "${CURRENT_SCRIPT_DIR}/src/skills" ]; then
  SOURCE_DIR="${CURRENT_SCRIPT_DIR}"
  log_info "Installing from local source: ${SOURCE_DIR}"
  if [ "$DRY_RUN" = false ]; then
    python3 "${SOURCE_DIR}/scripts/build.py"
  fi
elif [ -d "${CURRENT_SCRIPT_DIR}/dist/${PLUGIN_NAME}" ]; then
  SOURCE_DIR="${CURRENT_SCRIPT_DIR}/dist/${PLUGIN_NAME}"
  log_info "Installing from existing dist: ${SOURCE_DIR}"
else
  SOURCE_DIR="${INSTALL_BASE}"
fi

# ------------------------------------------------------------------------------
# Uninstall Routine
# ------------------------------------------------------------------------------
if [ "$UNINSTALL" = true ]; then
  log_info "Uninstalling ${PLUGIN_NAME}-skills..."
  
  if [ "$DRY_RUN" = true ]; then
    log_info "[dry-run] Would remove binary link ${BIN_DIR}/${PLUGIN_NAME}-cli and all harness links"
    exit 0
  fi

  # Remove binary symlink
  if [ -L "${BIN_DIR}/${PLUGIN_NAME}-cli" ] || [ -f "${BIN_DIR}/${PLUGIN_NAME}-cli" ]; then
    rm -f "${BIN_DIR}/${PLUGIN_NAME}-cli"
    log_success "Removed ${BIN_DIR}/${PLUGIN_NAME}-cli"
  fi

  # Remove harness links
  HARNESS_DIRS=(
    "${HOME}/.gemini/config/plugins/${PLUGIN_NAME}-skills"
    "${HOME}/.gemini/config/skills/${PLUGIN_NAME}"
    "${HOME}/.claude/plugins/${PLUGIN_NAME}"
    "${HOME}/.claude/skills/${PLUGIN_NAME}"
    "${HOME}/.codex/skills/${PLUGIN_NAME}"
    "${HOME}/.omp/skills/${PLUGIN_NAME}"
    "${HOME}/.config/orca/skills/${PLUGIN_NAME}"
    "${HOME}/.config/opencode/skills/${PLUGIN_NAME}"
    "${HOME}/.kiro/skills/${PLUGIN_NAME}"
    "${HOME}/.grok/skills/${PLUGIN_NAME}"
    "${HOME}/.hermes/skills/${PLUGIN_NAME}"
  )

  for dir in "${HARNESS_DIRS[@]}"; do
    if [ -L "$dir" ] || [ -e "$dir" ]; then
      rm -rf "$dir"
      log_success "Removed $dir"
    fi
  done

  if [ -d "${INSTALL_BASE}" ]; then
    rm -rf "${INSTALL_BASE}"
    log_success "Removed ${INSTALL_BASE}"
  fi

  log_success "${PLUGIN_NAME}-skills successfully uninstalled."
  exit 0
fi

# ------------------------------------------------------------------------------
# Download Release if remote install
# ------------------------------------------------------------------------------
if [ "$SOURCE_DIR" = "${INSTALL_BASE}" ]; then
  log_info "Fetching ${PLUGIN_NAME}-skills release (${VERSION})..."
  
  ARCHIVE_URL=""
  if [ "$VERSION" = "latest" ]; then
    ARCHIVE_URL="${GITHUB_URL}/releases/latest/download/${PLUGIN_NAME}-skills.tar.gz"
  else
    ARCHIVE_URL="${GITHUB_URL}/releases/download/${VERSION}/${PLUGIN_NAME}-skills.tar.gz"
  fi

  if [ "$DRY_RUN" = false ]; then
    mkdir -p "${INSTALL_BASE}"
    TMP_ARCHIVE="$(mktemp /tmp/${PLUGIN_NAME}-skills-XXXXXX.tar.gz)"
    
    if command -v curl >/dev/null 2>&1; then
      if ! curl -fsSL "$ARCHIVE_URL" -o "$TMP_ARCHIVE" 2>/dev/null; then
        # Fallback to cloning repository if release archive not published yet
        log_warn "Release asset not found. Falling back to git clone..."
        rm -f "$TMP_ARCHIVE"
        rm -rf "${INSTALL_BASE}"
        git clone --depth 1 "${GITHUB_URL}.git" "${INSTALL_BASE}"
      fi
    elif command -v wget >/dev/null 2>&1; then
      if ! wget -q "$ARCHIVE_URL" -O "$TMP_ARCHIVE" 2>/dev/null; then
        log_warn "Release asset not found. Falling back to git clone..."
        rm -f "$TMP_ARCHIVE"
        rm -rf "${INSTALL_BASE}"
        git clone --depth 1 "${GITHUB_URL}.git" "${INSTALL_BASE}"
      fi
    fi

    if [ -f "$TMP_ARCHIVE" ]; then
      tar -xzf "$TMP_ARCHIVE" -C "${INSTALL_BASE}" --strip-components=1 2>/dev/null || tar -xzf "$TMP_ARCHIVE" -C "${INSTALL_BASE}"
      rm -f "$TMP_ARCHIVE"
    fi

    if [ -f "${INSTALL_BASE}/scripts/build.py" ]; then
      python3 "${INSTALL_BASE}/scripts/build.py"
    fi
  else
    log_info "[dry-run] Would fetch from ${ARCHIVE_URL} and unpack to ${INSTALL_BASE}"
  fi
fi

# ------------------------------------------------------------------------------
# Install Global Binary Symlink
# ------------------------------------------------------------------------------
log_info "Configuring global CLI executable..."
CLI_SRC=""
if [ -f "${CURRENT_SCRIPT_DIR}/cli/bin/main" ]; then
  CLI_SRC="${CURRENT_SCRIPT_DIR}/cli/bin/main"
elif [ -f "${INSTALL_BASE}/cli/bin/main" ]; then
  CLI_SRC="${INSTALL_BASE}/cli/bin/main"
fi

if [ -n "$CLI_SRC" ]; then
  if [ "$DRY_RUN" = false ]; then
    mkdir -p "${BIN_DIR}"
    ln -sfn "${CLI_SRC}" "${BIN_DIR}/${PLUGIN_NAME}-cli"
    log_success "Linked executable: ${BIN_DIR}/${PLUGIN_NAME}-cli -> ${CLI_SRC}"
  else
    log_info "[dry-run] Would link ${BIN_DIR}/${PLUGIN_NAME}-cli -> ${CLI_SRC}"
  fi
fi

# ------------------------------------------------------------------------------
# Ensure config.json exists
# ------------------------------------------------------------------------------
CONFIG_DIR="${HOME}/.config/${PLUGIN_NAME}"
if [ "$DRY_RUN" = false ]; then
  mkdir -p "${CONFIG_DIR}"
  if [ ! -f "${CONFIG_DIR}/config.json" ]; then
    if [ -f "${CURRENT_SCRIPT_DIR}/config.example.json" ]; then
      cp "${CURRENT_SCRIPT_DIR}/config.example.json" "${CONFIG_DIR}/config.json"
      log_success "Initialized configuration at ${CONFIG_DIR}/config.json"
    elif [ -f "${INSTALL_BASE}/config.example.json" ]; then
      cp "${INSTALL_BASE}/config.example.json" "${CONFIG_DIR}/config.json"
      log_success "Initialized configuration at ${CONFIG_DIR}/config.json"
    fi
  fi
fi

# ------------------------------------------------------------------------------
# Install Skills into Harnesses
# ------------------------------------------------------------------------------
DIST_DIR=""
if [ -d "${CURRENT_SCRIPT_DIR}/dist/${PLUGIN_NAME}" ]; then
  DIST_DIR="${CURRENT_SCRIPT_DIR}/dist/${PLUGIN_NAME}"
elif [ -d "${INSTALL_BASE}/dist/${PLUGIN_NAME}" ]; then
  DIST_DIR="${INSTALL_BASE}/dist/${PLUGIN_NAME}"
fi

if [ -n "$DIST_DIR" ] && [ -f "${DIST_DIR}/scripts/install.py" ]; then
  INSTALL_CMD=(python3 "${DIST_DIR}/scripts/install.py" install)
  if [ "$TARGET_HARNESS" = "all" ]; then
    INSTALL_CMD+=(--all)
  elif [ "$TARGET_HARNESS" = "auto" ]; then
    INSTALL_CMD+=(--detected)
  else
    INSTALL_CMD+=(--agent "$TARGET_HARNESS")
  fi
  if [ "$DRY_RUN" = true ]; then
    INSTALL_CMD+=(--dry-run)
  fi

  log_info "Registering skills with agent harnesses..."
  "${INSTALL_CMD[@]}"
fi

echo ""
log_success "${BOLD}${PLUGIN_NAME}-skills installation complete!${NC}"
echo "Try running:"
echo "    ${PLUGIN_NAME}-cli playbooks"
echo "    ${PLUGIN_NAME}-cli agents init     # then fill the team's agent table: no agent starts without it"
echo "    ${PLUGIN_NAME}-cli doctor"
echo "    ${PLUGIN_NAME}-cli update"
echo "Or use /${PLUGIN_NAME}:playbook-plan inside your agent harness."
