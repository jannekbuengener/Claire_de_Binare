# Candle Aggregator Service - Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Upgrade pip to fix CVE-2025-8869 (CVSS 5.9)
RUN pip install --upgrade pip==25.3

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
