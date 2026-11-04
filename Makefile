# Build the plugin and install it into agent harnesses.
#
#   make build                      render dist/$(PLUGIN_NAME)/ from src/ (default name: swe, see plugin.env)
#   PLUGIN_NAME=acme make claude    build as "acme", install into Claude Code -> /acme, /acme:go-code
#   make claude | codex | omp | hermes | opencode | ...   build, validate, install (make agents lists all)
#   make claude omp hermes          several at once
#   make install                    every harness found on this machine (ALL=1: every harness the tool knows)
#   make claude REMOVE=1            remove it again (only what this tool installed)
#   make cli                        link the command <name>-cli (default swe-cli) into BIN_DIR (~/.local/bin)
#   make validate | docs | test | package | publish | status | list | agents | clean
#
# Options: SCOPE=user|project  PROJECT_DIR=.  PREFIX=<name>  SKILLS="go-code py-code"  PLUGIN=auto|yes|no  DRY_RUN=1
-include plugin.local.env
include plugin.env
export PLUGIN_NAME PLUGIN_TITLE PLUGIN_OWNER PLUGIN_VERSION PLUGIN_HOMEPAGE PLUGIN_DESCRIPTION PLUGIN_DOMAIN

PY          ?= python3
DIST        := dist/$(PLUGIN_NAME)
SCOPE       ?= user
PROJECT_DIR ?= .
PREFIX      ?= $(PLUGIN_NAME)
PLUGIN      ?= auto
SKILLS      ?=
DIR         ?=
BIN_DIR     ?= $(HOME)/.local/bin
comma       := ,
space       := $(subst ,, )
INSTALL      = $(PY) $(DIST)/scripts/install.py
ACTION       = $(if $(REMOVE),uninstall,install)
FLAGS        = --scope $(SCOPE) --project-dir $(PROJECT_DIR) --prefix "$(PREFIX)" --plugin $(PLUGIN) \
               $(if $(SKILLS),--skill "$(subst $(space),$(comma),$(strip $(SKILLS)))") $(if $(DRY_RUN),--dry-run)
HARNESSES   := claude codex omp devin opencode hermes universal amp gemini-cli cursor github-copilot windsurf goose \
               cline roo kilo droid qwen-code trae continue augment crush junie kiro-cli openhands mistral-vibe \
               antigravity qoder codebuddy iflow-cli openclaw

.PHONY: help cli build validate docs test package publish install custom list agents status clean $(HARNESSES)

help:
	@sed -n '1,12p' Makefile | sed 's/^# \{0,1\}//'

build:
	@$(PY) scripts/build.py

cli: build
	@mkdir -p $(BIN_DIR)
	ln -sfn $(CURDIR)/cli/bin/main $(BIN_DIR)/$(PLUGIN_NAME)-cli
	@echo "$(BIN_DIR)/$(PLUGIN_NAME)-cli -> $(CURDIR)/cli/bin/main (cd into a directory and run: $(PLUGIN_NAME)-cli init)"

validate: build
	@$(PY) $(DIST)/scripts/validate_skills.py

docs:
	@$(PY) scripts/gen_docs.py

test:
	bash tests/build_test.sh
	bash tests/enforcement_test.sh
	bash tests/harness_test.sh
	bash tests/frontend_test.sh
	bash cli/tests/selftest.sh
	bash cli/tests/flowtest.sh
	bash cli/tests/inittest.sh

package: validate
	cd dist && rm -f $(PLUGIN_NAME)-$(PLUGIN_VERSION).zip && zip -qr $(PLUGIN_NAME)-$(PLUGIN_VERSION).zip $(PLUGIN_NAME)
	@echo "dist/$(PLUGIN_NAME)-$(PLUGIN_VERSION).zip"

$(HARNESSES): %: validate
	$(INSTALL) $(ACTION) --agent $@ $(FLAGS)

install: validate
	$(INSTALL) $(ACTION) $(if $(ALL),--all,--detected) $(FLAGS)

custom: validate
	@test -n "$(DIR)" || { echo "usage: make custom DIR=<the harness's skills directory>"; exit 2; }
	$(INSTALL) $(ACTION) --dir "$(DIR)" $(FLAGS)

list: build
	@ls $(DIST)/skills

agents: build
	$(INSTALL) agents

status: build
	$(INSTALL) status --detected $(FLAGS)

publish: validate
	bash scripts/publish.sh $(if $(PUSH),--push)

clean:
	@echo "note: installed harnesses read dist/$(PLUGIN_NAME); run make claude codex omp after a clean"
	rm -rf dist
