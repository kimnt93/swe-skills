.PHONY: sync fmt lint test test-integration run
sync:
	uv sync
fmt:
	uv run ruff format src tests && uv run ruff check --fix src tests
lint:
	uv run ruff format --check src tests && uv run ruff check src tests
test:
	uv run pytest
test-integration:
	set -a; . ./.env; set +a; uv run pytest -m integration -o addopts=""
run:
	uv run service serve
