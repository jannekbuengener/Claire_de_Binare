# Paper Trading Runner - Containerized Service
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 paperuser

# Set working directory
WORKDIR /app

# Copy requirements first (for layer caching)
COPY tools/paper_trading/requirements.txt /app/tools/paper_trading/
RUN pip install --no-cache-dir -r tools/paper_trading/requirements.txt

# Copy application code
COPY core/ /app/core/
COPY services/ /app/services/
COPY tools/paper_trading/ /app/tools/paper_trading/

# Create logs directory
RUN mkdir -p /app/logs && chown -R paperuser:paperuser /app/logs

# Switch to non-root user
USER paperuser

# Expose health check port
EXPOSE 8004

# Set Python path
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8004/health || exit 1

# Run paper trading service
CMD ["python", "tools/paper_trading/service.py"]
