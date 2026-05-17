# Allocation Service - Dockerfile

FROM python:3.11-slim-trixie@sha256:e78299e55776ca065dcb769f80161f48465ad352014240eb5fe4712e22505e9b

WORKDIR /app

# Security: upgrade OS packages with available Trixie security patches (#2289)
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip to fix CVE-2025-8869 (CVSS 5.9)
RUN pip install --upgrade pip==26.1
RUN python -m pip install --no-cache-dir --upgrade setuptools==82.0.0 wheel==0.46.2

# System-Dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python Dependencies
COPY services/allocation/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Core Domain Models (shared)
COPY core /app/core

# Service-Code
COPY services/allocation/*.py ./

# Nicht-Root User
RUN useradd -m -u 1000 allocuser && \
    chown -R allocuser:allocuser /app
USER allocuser

# Health-Check
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD curl -f http://localhost:8005/health || exit 1

# Port
EXPOSE 8005

# Start
CMD ["python", "-u", "service.py"]
