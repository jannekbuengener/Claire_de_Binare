# Allocation Service - Dockerfile

FROM python:3.11-slim

WORKDIR /app

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
