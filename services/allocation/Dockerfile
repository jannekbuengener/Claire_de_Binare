# Allocation Service - Dockerfile

FROM python:3.11-slim-trixie@sha256:6d85378d88a19cd4d76079817532d62232be95757cb45945a99fec8e8084b9c2

WORKDIR /app

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
