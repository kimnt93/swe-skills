# verify.mk: the one proof command of a service. In the service Makefile: include verify.mk
# PLUGIN_SKILLS = the check scripts vendored into this repo (tools/skills/<skill>/scripts/...), so CI
# runs exactly what agents run. The verify-create skill vendors them.
PLUGIN_SKILLS ?= tools/skills
PORT ?= 3000
SERVICE ?= $(notdir $(CURDIR))
SCHEMAS ?= schemas
INFRA ?= docker-compose.infra.local.yaml
E2E ?= go test -tags e2e ./internal/e2e/...
RUN ?= go run ./cmd/api
READY_SECONDS ?= 60

.PHONY: verify verify-static verify-live

verify: verify-static verify-live

verify-static:
	$(MAKE) lint
	$(MAKE) test-race
	python3 $(PLUGIN_SKILLS)/api-contract/scripts/audit_api.py .
	if [ -d "$(SCHEMAS)" ]; then python3 $(PLUGIN_SKILLS)/db-migrations/scripts/check_migrations.py $(SCHEMAS); fi
	if [ -f go.mod ]; then (cd $(PLUGIN_SKILLS)/go-code/scripts/structcheck && go run . $(CURDIR)); fi
	if [ -f go.mod ]; then (cd $(PLUGIN_SKILLS)/go-code/scripts/archcheck && go run . $(CURDIR)); fi
	if grep -q 'tool.importlinter' pyproject.toml 2>/dev/null; then PYTHONPATH=src uv tool run --from import-linter lint-imports --no-cache; fi
	test -z "$$(git status --porcelain)"

# Infra up, e2e tests, the service started and probed live; everything torn down even on failure.
verify-live:
	@set -e; log="$$(mktemp)"; pid=""; \
	cleanup() { if [ -n "$$pid" ]; then kill "$$pid" 2>/dev/null || true; fi; \
	  docker compose -f $(INFRA) down -v >/dev/null 2>&1 || true; rm -f "$$log"; }; \
	trap cleanup EXIT; \
	docker compose -f $(INFRA) up -d --wait; \
	$(E2E); \
	$(RUN) >"$$log" 2>&1 & pid=$$!; \
	ready=0; \
	for i in $$(seq $(READY_SECONDS)); do \
	  if curl -fsS http://127.0.0.1:$(PORT)/healthz >/dev/null 2>&1; then ready=1; break; fi; sleep 1; \
	done; \
	if [ "$$ready" = 0 ]; then echo "service not ready on :$(PORT)"; tail -40 "$$log"; exit 1; fi; \
	python3 $(PLUGIN_SKILLS)/api-contract/scripts/probe_api.py http://127.0.0.1:$(PORT) --service $(SERVICE) --env local
