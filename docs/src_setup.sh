#!/bin/bash

cd /workspaces/UMLBot/src
uv pip install --upgrade pip setuptools wheel\
	    && uv pip install -e ".[dev]"
