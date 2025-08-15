format:
	uvx ruff format
install:
	uv sync
test:
	uv run pytest tests/