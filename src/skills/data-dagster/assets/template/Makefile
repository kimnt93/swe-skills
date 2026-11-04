.PHONY: verify lint test dev
verify: lint test
lint:
	uv run ruff format --check src tests
	uv run ruff check src tests
test:
	uv run pytest
dev:
	uv run dagster dev -m dag.definitions
