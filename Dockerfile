FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        default-jre-headless \
        graphviz \
        fonts-dejavu-core \
        unixodbc \
        curl \
    && rm -rf /var/lib/apt/lists/*

ADD https://github.com/plantuml/plantuml/releases/latest/download/plantuml.jar /opt/plantuml/plantuml.jar
ENV UMLBOT_PLANTUML_JAR_PATH=/opt/plantuml/plantuml.jar

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY . .
RUN uv sync --no-dev

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["python", "app/server.py"]
