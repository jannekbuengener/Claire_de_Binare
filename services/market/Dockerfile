FROM python:3.11-slim

WORKDIR /app

# Upgrade pip to fix CVE-2025-8869 (CVSS 5.9)
RUN pip install --upgrade pip==25.3

# System-Dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY services/market/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY services/market/service.py .
COPY services/market/email_alerter.py .

# Create logs directory
RUN mkdir -p /app/logs /app/logs/events

# Non-Root User
RUN useradd --create-home --uid 1000 marketuser \
    && chown -R marketuser:marketuser /app
USER marketuser

# Health-Check
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD curl -f http://localhost:8004/health || exit 1

# Expose health endpoint port
EXPOSE 8004

# Run service
CMD ["python", "-u", "service.py"]
