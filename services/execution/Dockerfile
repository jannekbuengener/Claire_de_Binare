# Execution Service - Gehärtetes Image
# Claire de Binare Trading Bot

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1

WORKDIR /app

# System-Abhängigkeiten (für Healthcheck & Psycopg2)
RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
		curl \
		build-essential \
		libpq-dev \
	&& rm -rf /var/lib/apt/lists/*

# Python Requirements
COPY services/execution/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Core Domain Models (shared)
COPY core /app/core

# Service-Code kopieren
COPY services/execution/ /app

# Non-Root User
RUN useradd --create-home --uid 1000 execuser \
	&& chown -R execuser:execuser /app
USER execuser

# Exposed Port
EXPOSE 8003

# Start Kommando
CMD ["python", "-u", "service.py"]
