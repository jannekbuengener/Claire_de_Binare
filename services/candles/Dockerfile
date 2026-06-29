# Candle Aggregator Service - Dockerfile

FROM python:3.14-slim-bookworm@sha256:4ff4b92a68355dbdb52584ab3391dff8d371a61d4e063468bfd0130e3189c6d9

WORKDIR /app

# Upgrade pip to fix CVE-2025-8869 (CVSS 5.9)
RUN pip install --upgrade pip==25.3
RUN python -m pip install --no-cache-dir --upgrade setuptools==82.0.0 wheel==0.46.2

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
