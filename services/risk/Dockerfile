FROM python:3.11-slim-bookworm@sha256:65a93d69fa75478d554f4ad27c85c1e69fa184956261b4301ebaf6dbb0a3543d

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
  && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip==25.3
RUN python -m pip install --no-cache-dir --upgrade setuptools==82.0.0 wheel==0.46.2
COPY services/risk/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core /app/core
COPY services/risk /app/services/risk

RUN mkdir -p /app/services \
  && touch /app/services/__init__.py \
  && touch /app/services/risk/__init__.py \
  && mkdir -p /app/data

RUN useradd -m -u 1000 riskuser \
  && chown -R riskuser:riskuser /app
USER riskuser

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -f http://localhost:8002/health || exit 1

CMD ["python", "-m", "services.risk.service"]
