.PHONY: setup pipeline dashboard lint format format-check typecheck check

setup:
	uv sync

pipeline:
	uv run python load_data.py

dashboard:
	@echo "TODO: start dashboard server"

lint:
	uv run ruff check .

format:
	uv run ruff format .
	uv run ruff check --fix .

format-check:
	uv run ruff format --check .

typecheck:
	uv run pyrefly check

check: format-check lint typecheck
