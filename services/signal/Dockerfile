# Signal Engine - Dockerfile

FROM python:3.11-slim

WORKDIR /app

# System-Dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Service-Code
COPY *.py ./

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
