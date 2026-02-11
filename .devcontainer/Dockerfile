# Base from Microsoft DevContainers Miniconda Python image
ARG VARIANT="3.11-bullseye"
FROM mcr.microsoft.com/devcontainers/python:0-${VARIANT}

ARG NODE_VERSION="none"

RUN rm -f /etc/apt/sources.list.d/yarn.list /usr/share/keyrings/yarn.gpg \
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
        curl -fsSL "https://deb.nodesource.com/setup_${NODE_VERSION}.x" | bash - \
        && apt-get update \
        && apt-get install -y --no-install-recommends nodejs \
        && rm -rf /var/lib/apt/lists/* \
        && node --version \
        && npm --version; \
    fi
RUN apt-cache policy nodejs && which npm || true
USER vscode
