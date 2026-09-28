.PHONY: setup pipeline dashboard lint format format-check typecheck check

setup:
	uv sync

pipeline:
	uv run python load_data.py
	uv run python analysis.py

view-analysis: 
	uv run marimo edit analysis.py --host 0.0.0.0 --port 2717 --headless --no-token

dashboard:
	uv run marimo run dashboard.py --host 0.0.0.0 --port 2718 --headless

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
