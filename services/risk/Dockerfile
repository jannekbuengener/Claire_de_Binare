FROM python:3.11-slim-trixie@sha256:6d85378d88a19cd4d76079817532d62232be95757cb45945a99fec8e8084b9c2

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
  && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip==26.1
RUN python -m pip install --no-cache-dir --upgrade setuptools==82.0.0 wheel==0.46.2
COPY services/risk/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core /app/core
COPY services/risk /app/services/risk

RUN mkdir -p /app/services \
  && touch /app/services/__init__.py \
  && touch /app/services/risk/__init__.py \
  && mkdir -p /app/data \
  && mkdir -p /app/kill_switch

RUN useradd -m -u 1000 riskuser \
  && chown -R riskuser:riskuser /app
USER riskuser

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -f http://localhost:8002/health || exit 1

CMD ["python", "-m", "services.risk.service"]
