# Signal Engine - Dockerfile

FROM python:3.11-slim

WORKDIR /app

# System-Dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip to fix CVE-2025-8869 (CVSS 5.9)
RUN pip install --upgrade pip==25.3

# Python Dependencies
COPY services/signal/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Core Domain Models (shared)
COPY core /app/core

# Service-Code
COPY services/signal/*.py ./

# Nicht-Root User
RUN useradd -m -u 1000 signaluser && \
    chown -R signaluser:signaluser /app
USER signaluser

# Health-Check
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Port
EXPOSE 8001

# Start
CMD ["python", "-u", "service.py"]
