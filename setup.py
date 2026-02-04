"""Packaging configuration for UMLBot."""

from pathlib import Path

from setuptools import find_packages, setup

# Load packages from requirements.txt
BASE_DIR = Path(__file__).parent
requirements_path = Path(BASE_DIR, "requirements.txt")
required_packages = []
dependency_links = []

with open(requirements_path, encoding="utf8") as file:
    for ln in file:
        ln = ln.strip()
        if ln.startswith("./"):  # handle local directory
            dependency_links.append(ln)
        else:
            required_packages.append(ln)

docs_packages = ["mkdocs", "mkdocs-monorepo-plugin", "mkdocstrings[python]"]

style_packages = ["black", "flake8", "isort"]

dev_packages = [
    "mkdocstrings[python]",
    "black[jupyter]",
    "autopep8",
    "pip-tools",
    "pandas",
    "pytest",
    "pytest-asyncio",
    "pytest-mock",
]

# Define our package
setup(
    name="UMLBot",
    version="0.01",
    description="An app to allow creation and refinement of UML diagrams fromo plain language text with generative AI and plantUML",
    author="Ryan Godwin",
    author_email="ryangodwin@uabmc.edu",
    url="https://github.com/UABGH-Emerging-Technologies/UMLBot",
    python_requires=">=3.8",
    packages=find_packages(),
    install_requires=[required_packages],
    extras_require={"dev": docs_packages + style_packages + dev_packages, "docs": docs_packages},
    dependency_links=dependency_links,
)
