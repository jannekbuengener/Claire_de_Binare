FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY service.py .
COPY email_alerter.py .

# Create logs directory
RUN mkdir -p /app/logs /app/logs/events

# Non-Root User (Security: Run as unprivileged user)
RUN useradd --create-home --uid 1000 marketuser && \
    chown -R marketuser:marketuser /app
USER marketuser

# Expose health endpoint port
EXPOSE 8004

# Run service
CMD ["python", "-u", "service.py"]
