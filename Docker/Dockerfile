# =============================================================================
# Stage 1 – Build the Next.js frontend
# =============================================================================
FROM node:18-bookworm-slim AS frontend-builder

WORKDIR /app

COPY app/frontend/package.json app/frontend/package-lock.json /app/
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 make g++ \
    && rm -rf /var/lib/apt/lists/*
RUN npm ci

COPY app/frontend /app

# At runtime the frontend talks to the backend on the same host.
ENV NEXT_PUBLIC_GRADIO_API_BASE=http://127.0.0.1:7860
RUN npm run build

# =============================================================================
# Stage 2 – Extract Jetty + PlantUML WAR from the official image
# =============================================================================
FROM plantuml/plantuml-server:jetty AS plantuml-extractor

# Nothing to do – we just COPY from this stage below.

# =============================================================================
# Stage 3 – Unified runtime
# =============================================================================
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    UMLBOT_SINGLE_CONTAINER=true

WORKDIR /app

# ---- System dependencies ----------------------------------------------------
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        unixodbc-dev \
        curl \
        gnupg \
        graphviz \
        fonts-dejavu-core \
        supervisor \
    && rm -rf /var/lib/apt/lists/*

# ---- JRE 17 (Temurin / Adoptium) -------------------------------------------
RUN curl -fsSL https://packages.adoptium.net/artifactory/api/gpg/key/public \
        | gpg --dearmor -o /usr/share/keyrings/adoptium.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/adoptium.gpg] https://packages.adoptium.net/artifactory/deb bookworm main" \
        > /etc/apt/sources.list.d/adoptium.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends temurin-17-jre \
    && rm -rf /var/lib/apt/lists/*

# ---- Node.js 18 (nodesource) -----------------------------------------------
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# ---- PlantUML / Jetty from stage 2 -----------------------------------------
COPY --from=plantuml-extractor /usr/local/jetty  /opt/jetty
COPY --from=plantuml-extractor /var/lib/jetty     /opt/jetty-base
COPY --from=plantuml-extractor /plantuml.war      /plantuml.war

# Set context path to root so URLs match http://localhost:8080/png/{encoded}
ENV CONTEXT_PATH=/

# ---- Python dependencies ----------------------------------------------------
COPY requirements.txt pyproject.toml setup.py /app/
COPY llm_utils /app/llm_utils
COPY UMLBot /app/UMLBot
COPY gradio_app.py /app/gradio_app.py
COPY app /app/app
COPY assets /app/assets

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt \
    && pip install --no-cache-dir -r /app/llm_utils/requirements.txt \
    && pip install --no-cache-dir \
        "langchain==0.3.27" \
        "langchain-community==0.3.31" \
        "langchain-openai==0.3.35" \
        "langchain-prompty==0.1.2" \
    && pip install --no-cache-dir -e /app/llm_utils \
    && pip install --no-cache-dir -e /app \
    && python -c "import langchain; from langchain.prompts import ChatPromptTemplate; print('langchain OK', langchain.__version__)"

# ---- Next.js production build from stage 1 ----------------------------------
COPY --from=frontend-builder /app/package.json   /app/app/frontend/package.json
COPY --from=frontend-builder /app/node_modules   /app/app/frontend/node_modules
COPY --from=frontend-builder /app/.next          /app/app/frontend/.next
COPY --from=frontend-builder /app/public         /app/app/frontend/public

# ---- supervisord config -----------------------------------------------------
RUN mkdir -p /var/log/supervisor
COPY Docker/supervisord.conf /etc/supervisor/conf.d/umlbot.conf

EXPOSE 3000 7860 8080

CMD ["supervisord", "-n", "-c", "/etc/supervisor/conf.d/umlbot.conf"]
