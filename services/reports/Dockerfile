FROM python:3.14-slim-bookworm@sha256:86f975aca15cf04a40b399eebede9aea7c82eae084d1f1a0a6ef6bcaae871a30

LABEL maintainer="CDB Team"
LABEL description="Daily Orders Summary Report Service"

WORKDIR /app

# Security pin (#4095): pip 26.1.2 fixes CVE-2026-8643
RUN pip install --upgrade pip==26.1.2

# Fix CVE-2026-23949 (jaraco.context), CVE-2026-24049 (wheel)
RUN python -m pip install --no-cache-dir --upgrade setuptools==83.0.0 wheel==0.46.2

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
