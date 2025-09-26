#!/bin/bash

cd /workspaces/Design_Drafter/src
uv pip install --upgrade pip setuptools wheel\
	    && uv pip install -e ".[dev]"
