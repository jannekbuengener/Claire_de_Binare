# Execution Service - Gehärtetes Image
# Claire de Binare Trading Bot
FROM python:3.11-slim-trixie@sha256:233de06753d30d120b1a3ce359d8d3be8bda78524cd8f520c99883bfe33964cf AS build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Build-Abhängigkeiten nur im Build-Stage
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python Requirements
COPY services/execution/requirements.txt ./
RUN python -m venv /venv \
    && /venv/bin/pip install --upgrade pip==25.3 \
    && /venv/bin/pip install --no-cache-dir --upgrade setuptools==82.0.0 wheel==0.46.2 \
    && /venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim-trixie@sha256:233de06753d30d120b1a3ce359d8d3be8bda78524cd8f520c99883bfe33964cf

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Runtime-Abhängigkeiten (kein build-essential/libpq-dev)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir --upgrade setuptools==82.0.0 wheel==0.46.2

COPY --from=build /venv /venv
ENV PATH="/venv/bin:$PATH"

# Core Domain Models (shared)
COPY core /app/core

# Service-Code kopieren
COPY services/execution/ /app

# Non-Root User
RUN useradd --create-home --uid 1000 execuser \
    && chown -R execuser:execuser /app
USER execuser

# Health-Check
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Exposed Port
EXPOSE 8003

# Start Kommando
CMD ["python", "-u", "service.py"]
