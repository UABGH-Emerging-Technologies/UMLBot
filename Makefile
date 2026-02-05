# Makefile
SHELL = /bin/bash
# help
.PHONY: help
help:
    @echo "Commands:"
    @echo "venv    : creates a virtual environment."
    @echo "style   : executes style formatting."
    @echo "clean   : cleans all unnecessary files."
    @echo "docs    : builds documentation with mkdocs."
    @echo "docs-serve: serves the documentation locally."
    @echo "plantuml-up   : starts local PlantUML server via docker compose."
    @echo "plantuml-logs : tails PlantUML server logs."
    @echo "plantuml-down : stops PlantUML server and related services."
# Styling
.PHONY: style
style:
	black UMLBot app tests gradio_app.py setup.py __init__.py
	flake8
	python3 -m isort UMLBot app tests gradio_app.py setup.py __init__.py
	autopep8 --recursive --aggressive --aggressive UMLBot app tests gradio_app.py setup.py __init__.py
# Environment
.ONESHELL:
venv:
	uv venv .venv --clear
	source .venv/bin/activate && \
	uv add setuptools wheel && \
	uv add -r requirements.txt &&\
	uv pip install -e ".[dev]"

.PHONY: npm-install
npm-install:
	cd app/frontend && npm install

.PHONY: npm-build
npm-build:
	cd app/frontend && npm run build

.PHONY: npm-dev
npm-dev:
	cd app/frontend && npm run dev

.PHONY: plantuml-up
plantuml-up:
	docker compose up -d plantuml

.PHONY: plantuml-down
plantuml-down:
	docker compose down

.PHONY: plantuml-logs
plantuml-logs:
	docker compose logs -f plantuml

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
