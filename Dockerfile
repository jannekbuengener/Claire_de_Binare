# Claire de Binaire - Screener Dockerfile
# Multi-Stage Build für Python Trading-Bot

FROM python:3.11-slim as base

# Build-Arg für welches Script ausgeführt wird
ARG SCRIPT_NAME=mexc_top5_ws.py

# Arbeitsverzeichnis
WORKDIR /app

# System-Dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Script kopieren
COPY ${SCRIPT_NAME} ./app.py
COPY backoffice/logging_config.json ./logging_config.json

# Log-Verzeichnis
RUN mkdir -p /app/logs

# Nicht-Root User
RUN useradd -m -u 1000 botuser && \
    chown -R botuser:botuser /app
USER botuser

# Health-Check Endpoint (falls im Script vorhanden)
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

# Start
CMD ["python", "-u", "app.py"]
