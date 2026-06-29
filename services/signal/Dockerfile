FROM python:3.14-slim-trixie@sha256:b877e50bd90de10af8d82c57a022fc2e0dc731c5320d762a27986facfc3355c1

WORKDIR /app

# Security: upgrade OS packages with available Trixie security patches (#2289)
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Base deps
RUN apt-get update && apt-get install -y \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Python deps
RUN pip install --upgrade pip==26.1
RUN python -m pip install --no-cache-dir --upgrade setuptools==82.0.0 wheel==0.46.2
COPY services/signal/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY core /app/core
COPY services/signal /app/services/signal
# Ensure python package layout for module execution
RUN mkdir -p /app/services \
  && touch /app/services/__init__.py \
  && touch /app/services/signal/__init__.py

# Run as non-root
RUN useradd -m -u 1000 signaluser \
  && chown -R signaluser:signaluser /app
USER signaluser

# Optional: container-level healthcheck (compose also defines one)
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -f http://localhost:8005/health || exit 1

CMD ["python", "-m", "services.signal.service"]
