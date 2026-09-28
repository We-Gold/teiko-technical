.PHONY: setup pipeline view-analysis dashboard lint format format-check typecheck check

# Use uv from PATH if available, otherwise fall back to the pip-installed module
UV := $(shell command -v uv 2>/dev/null || echo python3 -m uv)

setup:
	command -v uv >/dev/null 2>&1 || python3 -m pip install uv
	$(UV) sync

pipeline:
	$(UV) run python load_data.py
	$(UV) run python analysis.py

view-analysis:
	$(UV) run marimo edit analysis.py --host 0.0.0.0 --port 2717 --headless --no-token

dashboard:
	$(UV) run marimo run dashboard.py --host 0.0.0.0 --port 2718 --headless

lint:
	$(UV) run ruff check .

format:
	$(UV) run ruff format .
	$(UV) run ruff check --fix .

format-check:
	$(UV) run ruff format --check .

typecheck:
	$(UV) run pyrefly check

check: format-check lint typecheck
