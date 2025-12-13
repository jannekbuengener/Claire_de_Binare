# Dockerfile - DB Writer Service
# Claire de Binare Trading Bot

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir redis psycopg2-binary

# Core Domain Models (shared)
COPY core /app/core

# Copy service code
COPY services/db_writer/db_writer.py .

# Health check (check if Redis is reachable - DB Writer connects to it)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import redis; r = redis.Redis(host='${REDIS_HOST:-cdb_redis}', port=6379); r.ping()" || exit 1

# Run service
CMD ["python", "-u", "db_writer.py"]
