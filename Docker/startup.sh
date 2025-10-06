#!/bin/sh
PROJECT_ROOT="/workspaces/Design_Drafter"   
VENV_PATH="$PROJECT_ROOT/.venv"         # Note: env kept in the repo folder

# Install uv globally first
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create the virtual environment with uv
uv venv "$VENV_PATH" --clear

# Install uv **inside** that newly created venv to be safe
"$VENV_PATH/bin/python" -m pip install uv

# Use the venv's uv
export PATH="$VENV_PATH/bin:$PATH"

# Sync all development packages
uv sync --locked --all-extras --dev

# Rebuild the virtual environment (if needed)
make venv

# Auto-activate the venv for new shells
echo 'source /workspaces/Design_Drafter/.venv/bin/activate' >> /home/vscode/.bashrc
echo 'source /workspaces/Design_Drafter/.venv/bin/activate' >> /home/vscode/.zshrc

# Set PYTHONPATH for local modules
echo 'export PYTHONPATH="/workspaces/Design_Drafter/llm_utils:${PYTHONPATH}"' >> ~/.profile

# MLFlow setup
export MLFLOW_TRACKING_URI="http://138.26.48.232:5000/"

# Now, start the Gradio app
# Replace 'gradio_app.py' with the correct filename if needed
# Run in background or foreground as desired
# Example:
cd "$PROJECT_ROOT"
python gradio_app.py