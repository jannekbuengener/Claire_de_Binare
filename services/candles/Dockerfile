# Candle Aggregator Service - Dockerfile

FROM python:3.14-slim-bookworm@sha256:86f975aca15cf04a40b399eebede9aea7c82eae084d1f1a0a6ef6bcaae871a30

WORKDIR /app

# Security pin (#4095): pip 26.1.2 fixes CVE-2026-8643, supersedes the CVE-2025-8869 pin
RUN pip install --upgrade pip==26.1.2
RUN python -m pip install --no-cache-dir --upgrade setuptools==83.0.0 wheel==0.46.2

# System-Dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python Dependencies
COPY services/candles/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Core Domain Models (shared)
COPY core /app/core

# Service-Code
COPY services/candles/*.py ./

# Nicht-Root User
RUN useradd -m -u 1000 candleuser && \
    chown -R candleuser:candleuser /app
USER candleuser

# Health-Check
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD curl -f http://localhost:8007/health || exit 1

# Port
EXPOSE 8007

# Start
CMD ["python", "-u", "service.py"]
