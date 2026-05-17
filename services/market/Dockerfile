FROM python:3.11-slim-trixie@sha256:6d85378d88a19cd4d76079817532d62232be95757cb45945a99fec8e8084b9c2

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Upgrade pip to fix CVE-2025-8869 (CVSS 5.9)
RUN pip install --upgrade pip==26.1
RUN python -m pip install --no-cache-dir --upgrade setuptools==82.0.0 wheel==0.46.2

COPY services/market/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core /app/core
COPY services/market /app/services/market

RUN mkdir -p /app/services \
  && touch /app/services/__init__.py \
  && touch /app/services/market/__init__.py

RUN useradd -m -u 1000 marketuser \
  && chown -R marketuser:marketuser /app
USER marketuser

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD curl -f http://localhost:8009/health || exit 1

EXPOSE 8009

CMD ["python", "-m", "services.market.service"]
