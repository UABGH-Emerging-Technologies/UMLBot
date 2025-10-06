# Base from Microsoft DevContainers Miniconda Python image
ARG VARIANT="3.11-bullseye"
FROM mcr.microsoft.com/devcontainers/python:0-${VARIANT}

# [Choice] Node.js version is set via build ARG; keep as in your original
ARG NODE_VERSION="none"
RUN if [ "${NODE_VERSION}" != "none" ]; then su vscode -c "umask 0002 && . /usr/local/share/nvm/nvm.sh && nvm install ${NODE_VERSION} 2>&1"; fi

# System dependencies for image/PIL support & other scientific deps
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
        sqlite3 \
        cmake \
        graphviz \
        pandoc \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender-dev \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Optionally copy any local fonts if you want to use custom ones:
# COPY fonts /usr/share/fonts/truetype/custom-fonts

# Install Python requirements as vscode
USER vscode

# Copy requirements.txt first for better cache
COPY --chown=vscode:vscode requirements.txt /workspaces/Design_Drafter/requirements.txt

# Install pip dependencies
RUN pip install --no-cache-dir -r /workspaces/Design_Drafter/requirements.txt

# Copy the whole source code (preserves user for devcontainer)
COPY --chown=vscode:vscode . /workspaces/Design_Drafter/

WORKDIR /workspaces/Design_Drafter

# It's common to EXPOSE Gradio/Flask port, but not strictly needed in devcontainer.
EXPOSE 7860

# Don't define CMD in a devcontainer Dockerfile, as the devcontainer
# controls which script is run using the postCreateCommand or by interactive dev.