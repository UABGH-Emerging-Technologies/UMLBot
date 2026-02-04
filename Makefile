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
# Styling
.PHONY: style
style:
	black . 
	flake8 
	python3 -m isort .
	autopep8 --recursive --aggressive --aggressive .
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
