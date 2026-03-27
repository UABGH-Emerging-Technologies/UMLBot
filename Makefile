# Makefile
SHELL = /bin/bash
# help
.PHONY: help
help:
	@echo "Commands:"
	@echo "venv          : creates a virtual environment."
	@echo "style         : executes style formatting."
	@echo "clean         : cleans all unnecessary files."
	@echo "docs          : builds documentation with mkdocs."
	@echo "run           : starts the FastAPI server locally."
	@echo "streamlit     : starts the Streamlit frontend."
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

# Run the FastAPI server locally
.PHONY: run
run:
	PYTHONPATH=$(PWD) .venv/bin/python app/server.py

# Streamlit frontend
.PHONY: streamlit
streamlit:
	PYTHONPATH=$(PWD) .venv/bin/streamlit run streamlit_app.py --server.port 8501

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
