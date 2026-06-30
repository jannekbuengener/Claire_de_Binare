# Paper Trading Runner - Containerized Service
FROM python:3.14-slim-bookworm@sha256:4ff4b92a68355dbdb52584ab3391dff8d371a61d4e063468bfd0130e3189c6d9

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 paperuser

# Set working directory
WORKDIR /app

# Fix CVE-2026-23949 (jaraco.context), CVE-2026-24049 (wheel)
RUN python -m pip install --no-cache-dir --upgrade setuptools==82.0.0 wheel==0.46.2

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
