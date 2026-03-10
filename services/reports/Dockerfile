FROM python:3.11-slim-bookworm@sha256:65a93d69fa75478d554f4ad27c85c1e69fa184956261b4301ebaf6dbb0a3543d

LABEL maintainer="CDB Team"
LABEL description="Daily Orders Summary Report Service"

WORKDIR /app

# Fix CVE-2026-23949 (jaraco.context), CVE-2026-24049 (wheel)
RUN python -m pip install --no-cache-dir --upgrade setuptools==82.0.0 wheel==0.46.2

# Install system dependencies (procps for pgrep healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY daily_orders_summary.py .

# Make script executable
RUN chmod +x daily_orders_summary.py

# Run as non-root user
RUN useradd -m -u 1000 reporter && chown -R reporter:reporter /app
USER reporter

# Start service
CMD ["python", "daily_orders_summary.py"]
