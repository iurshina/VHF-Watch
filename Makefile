.PHONY: help install format lint typecheck run docker-build docker-run

help:
	@echo "Available commands:"
	@echo "  make install       Install project with Poetry"
	@echo "  make format        Format code with Black"
	@echo "  make lint          Lint code with Ruff"
	@echo "  make typecheck     Run MyPy on codebase"
	@echo "  make run           Run the CLI via Poetry"
	@echo "  make docker-build  Build Docker image"
	@echo "  make docker-run    Run Docker container"

install:
	poetry install

format:
	poetry run black .

lint:
	poetry run ruff .

typecheck:
	poetry run mypy vhf_watch/

run:
	poetry run python -m vhf_watch --debug --duration 10

docker-build:
	docker build -t vhf-watch .

docker-run:
	docker run --rm -it vhf-watch