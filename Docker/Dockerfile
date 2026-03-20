# =============================================================================
# Stage 1 – Extract PlantUML JAR from the official image
# =============================================================================
FROM plantuml/plantuml-server:jetty AS plantuml-extractor

# The official image bundles the JAR inside the WAR; extract it.
RUN mkdir -p /opt/plantuml \
    && cp /plantuml.war /opt/plantuml/plantuml.jar

# =============================================================================
# Stage 2 – Unified runtime (Python + JRE only)
# =============================================================================
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

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
    && rm -rf /var/lib/apt/lists/*

# ---- JRE 17 (Temurin / Adoptium) -------------------------------------------
RUN curl -fsSL https://packages.adoptium.net/artifactory/api/gpg/key/public \
        | gpg --dearmor -o /usr/share/keyrings/adoptium.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/adoptium.gpg] https://packages.adoptium.net/artifactory/deb bookworm main" \
        > /etc/apt/sources.list.d/adoptium.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends temurin-17-jre \
    && rm -rf /var/lib/apt/lists/*

# ---- PlantUML JAR from stage 1 ----------------------------------------------
COPY --from=plantuml-extractor /opt/plantuml/plantuml.jar /opt/plantuml/plantuml.jar
ENV UMLBOT_PLANTUML_JAR_PATH=/opt/plantuml/plantuml.jar

# ---- Python dependencies ----------------------------------------------------
COPY requirements.txt pyproject.toml setup.py /app/
COPY llm_utils /app/llm_utils
COPY UMLBot /app/UMLBot
COPY app /app/app
COPY assets /app/assets
COPY streamlit_app.py /app/streamlit_app.py
COPY api_startup.sh /app/api_startup.sh
RUN chmod +x /app/api_startup.sh

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

EXPOSE 8000

ENTRYPOINT ["./api_startup.sh"]
