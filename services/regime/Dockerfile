# Regime Service - Dockerfile

FROM python:3.14-slim-trixie@sha256:cea0e6040540fb2b965b6e7fb5ffa00871e632eef63719f0ea54bca189ce14a6

WORKDIR /app

# Security: upgrade OS packages with available Trixie security patches (#2289)
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Security pin (#4095): pip 26.1.2 fixes CVE-2026-8643, supersedes the CVE-2025-8869 pin
RUN pip install --upgrade pip==26.1.2
RUN python -m pip install --no-cache-dir --upgrade setuptools==83.0.0 wheel==0.46.2

# System-Dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python Dependencies
COPY services/regime/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Core Domain Models (shared)
COPY core /app/core

# Service-Code
COPY services/regime/*.py ./

# Nicht-Root User
RUN useradd -m -u 1000 regimeuser && \
    chown -R regimeuser:regimeuser /app
USER regimeuser

# Health-Check
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD curl -f http://localhost:8008/health || exit 1

# Port
EXPOSE 8008

# Start
CMD ["python", "-u", "service.py"]
