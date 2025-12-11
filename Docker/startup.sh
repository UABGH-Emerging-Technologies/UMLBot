#!/bin/bash
# Install uv globally first (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Ensure Python venv is created (idempotent)
if [ ! -d "/workspaces/design_drafter/.venv" ]; then
    make venv
fi

# Check for npm and install Node dependencies (fail fast if missing)
if ! command -v npm &> /dev/null; then
    echo "npm not found. Node.js should be installed via devcontainer config (NODE_VERSION=18)."
    exit 1
fi

# Install/update Node/TypeScript dependencies for frontend
cd "/workspaces/design_drafter/umlai-ts" && npm install

# Auto-activate the venv for new shells (append to shell rc files)
echo 'source /workspaces/design_drafter/.venv/bin/activate' >> /home/vscode/.bashrc
echo 'source /workspaces/design_drafter/.venv/bin/activate' >> /home/vscode/.zshrc

# Set PYTHONPATH for local modules (for Python import resolution)
echo 'export PYTHONPATH="/workspaces/design_drafter/llm_utils:${PYTHONPATH}"' >> ~/.profile

# MLFlow setup (tracking URI for MLFlow experiments)
export MLFLOW_TRACKING_URI="http://localhost:5000/"

# Start the Typescript app instead of the Gradio Python app
if [ -f "/workspaces/design_drafter/.venv/bin/activate" ]; then
    source /workspaces/design_drafter/.venv/bin/activate
else
    echo "Python virtualenv not found at /workspaces/design_drafter/.venv/bin/activate"
    exit 1
fi
cd "/workspaces/design_drafter/umlai-ts" && exec npm start
