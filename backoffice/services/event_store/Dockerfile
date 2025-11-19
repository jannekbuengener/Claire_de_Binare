FROM python:3.11-slim

# Security hardening
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY service.py .

# Copy event_sourcing module from services/
COPY ../../../services/event_sourcing.py /app/services/

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD curl -fsS http://localhost:8004/health || exit 1

# Expose port
EXPOSE 8004

# Run service
CMD ["python", "service.py"]
