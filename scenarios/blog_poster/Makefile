.PHONY: install dev test clean

install:
	uv pip install -e .

dev:
	uv pip install -e ".[dev]"

test:
	uv run pytest tests/

clean:
	rm -rf build/ dist/ *.egg-info/ __pycache__/ .pytest_cache/
