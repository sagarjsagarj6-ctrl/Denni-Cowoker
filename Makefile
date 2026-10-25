.PHONY: install test lint format typecheck check serve

install:
	uv sync --extra dev

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy src

check: lint typecheck test

serve:
	uv run dynamic-agents serve
