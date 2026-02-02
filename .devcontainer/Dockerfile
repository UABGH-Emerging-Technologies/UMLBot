# Base from Microsoft DevContainers Miniconda Python image
ARG VARIANT="3.11-bullseye"
FROM mcr.microsoft.com/devcontainers/python:0-${VARIANT}

ARG NODE_VERSION="none"

RUN curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | gpg --dearmor | tee /usr/share/keyrings/yarn.gpg > /dev/null \
    && echo "deb [signed-by=/usr/share/keyrings/yarn.gpg] https://dl.yarnpkg.com/debian stable main" | tee /etc/apt/sources.list.d/yarn.list \
    && apt-get update && export DEBIAN_FRONTEND=noninteractive \
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

RUN if [ "${NODE_VERSION}" != "none" ]; then \
        su vscode -c "umask 0002 && . /usr/local/share/nvm/nvm.sh && nvm install ${NODE_VERSION} 2>&1"; \
    fi

USER vscode