# Regime Service - Dockerfile

FROM python:3.11-slim

WORKDIR /app

# System-Dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python Dependencies
COPY services/regime/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Service-Code
COPY services/regime/*.py ./

# Nicht-Root User
RUN useradd -m -u 1000 regimeuser && \
    chown -R regimeuser:regimeuser /app
USER regimeuser

# Health-Check
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD curl -f http://localhost:8004/health || exit 1

# Port
EXPOSE 8004

# Start
CMD ["python", "-u", "service.py"]
