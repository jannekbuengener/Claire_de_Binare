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

# System dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY services/ws/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Core Domain Models (shared)
COPY core /app/core

# Service code
COPY services/ws/*.py ./
COPY services/ws/mexc_proto_gen /app/mexc_proto_gen

# Create logs directory
RUN mkdir -p /app/logs /app/logs/events

# Non-root user
RUN useradd --create-home --uid 1000 wsuser \
    && chown -R wsuser:wsuser /app
USER wsuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose health endpoint port
EXPOSE 8000

# Run service
CMD ["python", "-u", "service.py"]
