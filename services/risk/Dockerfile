FROM python:3.14-slim-trixie@sha256:cea0e6040540fb2b965b6e7fb5ffa00871e632eef63719f0ea54bca189ce14a6

WORKDIR /app

# Security: upgrade OS packages with available Trixie security patches (#2289)
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Security pin (#4095): pip 26.1.2 fixes CVE-2026-8643, supersedes the CVE-2025-8869 pin
RUN pip install --upgrade pip==26.1.2
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
