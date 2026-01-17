FROM python:3.11-slim

LABEL maintainer="CDB Team"
LABEL description="Daily Orders Summary Report Service"

WORKDIR /app

# Install dependencies
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
