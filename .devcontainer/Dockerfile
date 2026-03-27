# Base from Microsoft DevContainers Python image
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
        default-jre-headless \
    && rm -rf /var/lib/apt/lists/*

USER vscode
