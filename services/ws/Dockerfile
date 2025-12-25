FROM python:3.11-slim

WORKDIR /app

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
