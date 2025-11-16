1. Redis

Muss ein Passwort erzwingen: --requirepass $REDIS_PASSWORD

Nur lokal binden: 127.0.0.1:6380 → 6379

AOF aktiviert: --appendonly yes

Memory Policy: allkeys-lru

Keine öffentlichen Ports.

2. Postgres

Kein Default-Passwort.

Passwort muss per .env gesetzt werden:
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:?not set}

Port lokal, kein Host-Expose.

3. Grafana & Prometheus

Grafana darf nie mit Default-Admin laufen.

Passwort muss gesetzt sein:
GRAFANA_PASSWORD=${GRAFANA_PASSWORD:?not set}

4. Container Hardening (alle Services)

Run as non-root: user: 1000:1000

Kein Write auf Root-FS: read_only: true

tmpfs: /tmp

security_opt: no-new-privileges:true

cap_drop: [ALL]

5. Execution-Service (zusätzlich)

Base-Image slim

System-Dependencies: curl, libpq-dev, build-essential

PYTHON Flags:

PYTHONDONTWRITEBYTECODE=1

PYTHONUNBUFFERED=1

6. Secrets

Werden nur über Environment-Variablen geladen.

Keine Fallbacks, keine Defaults.

Keine Secrets im Repo, keine .pem/.key/.pfx/.sqlite.

7. Healthchecks

Alle Services müssen einen /health Endpoint besitzen.

Curl-check im Compose/Kubernetes.
