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

# Expose health endpoint port
EXPOSE 8004

# Run service
CMD ["python", "-u", "service.py"]
