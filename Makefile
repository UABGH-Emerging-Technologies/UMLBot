# Makefile
SHELL = /bin/bash

# Load .env file if it exists
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

# help
.PHONY: help
help:
	@echo "Commands:"
	@echo "venv          : creates a virtual environment."
	@echo "style         : executes style formatting."
	@echo "clean         : cleans all unnecessary files."
	@echo "docs          : builds documentation with mkdocs."
	@echo "run           : starts backend and frontend together."
	@echo "backend       : starts only the FastAPI server."
	@echo "frontend      : starts only the Streamlit frontend."
	@echo "docker-build  : builds the single-container image."
	@echo "docker-up     : starts the container."
	@echo "docker-down   : stops the container."
	@echo "docker-logs   : tails container logs."
# Styling
.PHONY: style
style:
	black UMLBot app tests streamlit_app.py __init__.py
	flake8
	python3 -m isort UMLBot app tests streamlit_app.py __init__.py
	autopep8 --recursive --aggressive --aggressive UMLBot app tests streamlit_app.py __init__.py
# Environment
.ONESHELL:
venv:
	uv venv .venv --clear
	source .venv/bin/activate && \
	uv sync

# PlantUML JAR — use devcontainer copy for local dev unless already set
PLANTUML_JAR ?= $(PWD)/.devcontainer/plantuml/plantuml.jar

# Run both backend and frontend
.PHONY: run backend frontend
run:
	@echo "Starting backend and frontend..."
	$(MAKE) backend &
	$(MAKE) frontend

backend:
	JAVA_TOOL_OPTIONS="-Djava.awt.headless=true" UMLBOT_PLANTUML_JAR_PATH=$(PLANTUML_JAR) PYTHONPATH=$(PWD) .venv/bin/python app/server.py

frontend:
	PYTHONPATH=$(PWD) .venv/bin/streamlit run streamlit/diagram_builder.py --server.port 8501

# Full-stack single container
.PHONY: docker-build
docker-build:
	docker compose build

.PHONY: docker-up
docker-up:
	docker compose up -d

.PHONY: docker-down
docker-down:
	docker compose down

.PHONY: docker-logs
docker-logs:
	docker compose logs -f

.PHONY: test
test:
	PYTHONPATH=$(PWD) .venv/bin/python -m pytest -q
# Docs
.PHONY: docs
docs:
	.venv/bin/mkdocs build
	.venv/bin/mkdocs serve -a 0.0.0.0:8000

# Cleaning
.PHONY: clean
clean: style
	find . -type f -name "*.DS_Store" -ls -delete
	find . | grep -E "(__pycache__|\.pyc|\.pyo)" | xargs rm -rf
	find . | grep -E ".pytest_cache" | xargs rm -rf
	find . | grep -E ".ipynb_checkpoints" | xargs rm -rf
	rm -f .coverage
