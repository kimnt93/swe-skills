.PHONY: verify test lint
verify: lint test
lint:
	uv run ruff format --check src tests
	uv run ruff check src tests
test:
	uv run pytest
