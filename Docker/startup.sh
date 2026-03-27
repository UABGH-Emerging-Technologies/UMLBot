#!/bin/bash
# Devcontainer post-create setup script.
# Installs uv, creates .venv, downloads PlantUML JAR, activates venv.

set -e

# Install uv globally first (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

REPO_DIR="/workspaces/UMLBot"

# Ensure .venv is writable and created (idempotent)
if [ -d "${REPO_DIR}/.venv" ] && [ ! -w "${REPO_DIR}/.venv" ]; then
    if command -v sudo >/dev/null 2>&1; then
        sudo chown -R vscode:vscode "${REPO_DIR}/.venv"
    else
        echo ".venv exists but is not writable and sudo is unavailable."
        exit 1
    fi
fi
if [ ! -d "${REPO_DIR}/.venv" ] || [ ! -f "${REPO_DIR}/.venv/bin/activate" ]; then
    rm -rf "${REPO_DIR}/.venv"
    if command -v make >/dev/null 2>&1; then
        make -B venv
    elif command -v uv >/dev/null 2>&1; then
        uv venv "${REPO_DIR}/.venv"
    else
        python3 -m venv "${REPO_DIR}/.venv"
    fi
fi

# Download PlantUML JAR if not present
PLANTUML_DIR="${REPO_DIR}/.devcontainer/plantuml"
PLANTUML_JAR="${PLANTUML_DIR}/plantuml.jar"
if [ ! -f "${PLANTUML_JAR}" ]; then
    mkdir -p "${PLANTUML_DIR}"
    echo "Downloading PlantUML JAR..."
    curl -fsSL -o "${PLANTUML_JAR}" \
        "https://github.com/plantuml/plantuml/releases/latest/download/plantuml.jar"
fi

# Auto-activate the venv for new shells
echo "source ${REPO_DIR}/.venv/bin/activate" >> /home/vscode/.bashrc
echo "source ${REPO_DIR}/.venv/bin/activate" >> /home/vscode/.zshrc

# Set PYTHONPATH for local modules
echo "export PYTHONPATH=\"${REPO_DIR}/llm_utils:\${PYTHONPATH}\"" >> ~/.profile
echo "export UMLBOT_PLANTUML_JAR_PATH=\"${PLANTUML_JAR}\"" >> ~/.profile

echo "Devcontainer setup complete."
