# Dockerfile - DB Writer Service
# Claire de Binare Trading Bot

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

# Install dependencies
RUN pip install --no-cache-dir redis psycopg2-binary prometheus-client

# Core Domain Models (shared)
COPY core /app/core

# Copy service code
COPY services/db_writer/db_writer.py .

# Non-Root User
RUN useradd --create-home --uid 1000 dbwriter \
    && chown -R dbwriter:dbwriter /app
USER dbwriter

# Health check (check if Redis is reachable - DB Writer connects to it)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import redis; r = redis.Redis(host='${REDIS_HOST:-cdb_redis}', port=6379); r.ping()" || exit 1

# Run service
CMD ["python", "-u", "db_writer.py"]
