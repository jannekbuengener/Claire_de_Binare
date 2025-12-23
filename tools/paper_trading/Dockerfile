# Paper Trading Runner - Dockerfile

FROM python:3.11-slim

WORKDIR /app

# System tooling
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends curl; \
    rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY tools/paper_trading/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Shared core models
COPY core /app/core

# Runner implementation
COPY tools/paper_trading/*.py ./

EXPOSE 8004

CMD ["python", "-u", "service.py"]
