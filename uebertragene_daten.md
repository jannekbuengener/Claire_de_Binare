# SOURCE: SECURITY_FIX_PLAN.md

```md
# Sicherheits-Fix-Plan

## Docker Compose

```diff
diff --git a/docker-compose.yml b/docker-compose.yml
@@
-      - "6380:6379"
-    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
+      - "127.0.0.1:6380:6379"
+    environment:
+      REDIS_PASSWORD: ${REDIS_PASSWORD:?REDIS_PASSWORD not set}
+    command: /bin/sh -c "redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru --requirepass $$REDIS_PASSWORD"
@@
-      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-cdb_secure_password}
+      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD not set}
@@
-      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:-admin123}
+      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:?GRAFANA_PASSWORD not set}
@@
-    healthcheck:
-      test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
+    healthcheck:
+      test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
+    user: "1000:1000"
+    security_opt:
+      - no-new-privileges:true
+    cap_drop:
+      - ALL
+    tmpfs:
+      - /tmp
+    read_only: true
@@
-    tmpfs:
-      - /tmp
+    tmpfs:
+      - /tmp
+    read_only: true
@@
-    tmpfs:
-      - /tmp
+    tmpfs:
+      - /tmp
+    read_only: true
@@
-    tmpfs:
-      - /tmp
+    tmpfs:
+      - /tmp
+    read_only: true
@@
-    tmpfs:
-      - /tmp
+    tmpfs:
+      - /tmp
+    read_only: true
```

## Environment Files

```diff
diff --git a/.env b/.env
@@
-REDIS_PASSWORD=
+REDIS_PASSWORD=change_this_redis_secret_now
@@
-GRAFANA_PASSWORD=admin123_CHANGE_ME
+GRAFANA_PASSWORD=change_this_grafana_secret_now
@@
-POSTGRES_PASSWORD=cdb_secure_password_CHANGE_ME
+POSTGRES_PASSWORD=change_this_postgres_secret_now
```

```diff
diff --git a/backoffice/.env.example b/backoffice/.env.example
@@
+# Redis
+REDIS_HOST=redis
+REDIS_PORT=6379
+REDIS_PASSWORD=
+REDIS_DB=0
+
+# Monitoring
+PROMETHEUS_PORT=9090
+GRAFANA_PORT=3000
+GRAFANA_PASSWORD=
+
+# Datenbank
+POSTGRES_HOST=cdb_postgres
+POSTGRES_PORT=5432
+POSTGRES_USER=cdb_user
+POSTGRES_PASSWORD=
+POSTGRES_DB=claire_de_binare
```

## Execution-Service Image

```diff
diff --git a/backoffice/services/execution_service/Dockerfile b/backoffice/services/execution_service/Dockerfile
@@
-FROM python:3.11-slim
+FROM python:3.11-slim
+
+ENV PYTHONDONTWRITEBYTECODE=1 \
+    PYTHONUNBUFFERED=1
@@
-# Copy all files
-COPY . /app
-
-# Install dependencies
-RUN pip install --no-cache-dir -r requirements.txt
-
-# Expose port
-EXPOSE 8003
-
-# Start service
-CMD ["python", "-u", "service.py"]
+# System-Abhängigkeiten (für Healthcheck & Psycopg2)
+RUN apt-get update \
+    && apt-get install -y --no-install-recommends \
+        curl \
+        build-essential \
+        libpq-dev \
+    && rm -rf /var/lib/apt/lists/*
+
+# Python Requirements
+COPY requirements.txt ./
+RUN pip install --no-cache-dir -r requirements.txt
+
+# Service-Code kopieren
+COPY . /app
+
+# Non-Root User
+RUN useradd --create-home --uid 1000 execuser \
+    && chown -R execuser:execuser /app
+USER execuser
+
+# Exposed Port
+EXPOSE 8003
+
+# Start Kommando
+CMD ["python", "-u", "service.py"]
```

## Rollback-Hinweise

- Vor Rollback Secrets sichern (Redis-AOF, Postgres-Volume).
- Rückbau der Hardening-Flags nur durchführen, wenn funktionale Regression nachweislich nicht anders lösbar.

## Validierung

1. `docker compose config` – erwartet keine Fehler.
2. `docker compose up -d redis postgres grafana execution_service` – Container starten ohne Crash.
3. `docker exec -it cdb_redis redis-cli -a "$Env:REDIS_PASSWORD" ping` – Antwort `PONG`.
4. `docker exec -it cdb_postgres psql -U cdb_user -d claire_de_binare -c "\dt"` – erfolgreiche Authentifizierung mit neuem Passwort.
5. `curl http://localhost:8003/health` – Status `200`.
```

# SOURCE: SECURITY_RISK_REPORT.md

```md
# Sicherheitsrisikobericht

| ID | Titel | Schweregrad | Fundstelle | Impact | Exploitability | Fix | Nachweis |
|----|-------|-------------|------------|--------|----------------|-----|----------|
| SR-001 | Redis ohne Auth & Host-Expose | 🔴 | docker-compose.yml:12-31, .env:30-37 | Vollständiger Zugriff auf Message-Bus; Manipulation von `orders`/`signals` möglich | Hoch – Port 6380 offen, kein Passwort erforderlich | `--requirepass` mit verpflichtendem Secret, Port auf Loopback gebunden | `rg -n "redis-server" docker-compose.yml` |
| SR-002 | Postgres Passwort-Fallback | 🔴 | docker-compose.yml:30-40, .env:56-63 | DB-Komplettübernahme, Manipulation von Trades/Orders, Datenabfluss | Hoch – bekannter Default `cdb_secure_password_2025` verwendbar | Fallback entfernt, Secret über `.env` verpflichtend | `rg -n "POSTGRES_PASSWORD" docker-compose.yml .env` |
| SR-003 | Grafana Admin-Standardpasswort | 🟠 | docker-compose.yml:78-86, .env:36-44 | Admin-Übernahme, Dashboard-Manipulation, Credential-Leak | Hoch – Default `admin123` bekannt, Login ohne Rate-Limit | Secret zwingend via `.env`, Operator muss starkes Passwort setzen | `rg -n "GF_SECURITY_ADMIN_PASSWORD" docker-compose.yml` |
| SR-004 | Execution-Service läuft als Root ohne Hardening | 🟠 | backoffice/services/execution_service/Dockerfile:1-40, docker-compose.yml:176-205 | Container-Escape-Risiko via Python/psycopg2 Exploit, Dateisystem-Manipulation | Mittel – Service exponiert Flask-Endpunkte, mehrere Third-Party-Module | Non-Root-User, Cap-Drop, `no-new-privileges`, Read-Only Root-FS | `rg -n "no-new-privileges" docker-compose.yml` |

## STRIDE-Zuordnung

- SR-001: Tampering, Spoofing, Denial of Service
- SR-002: Tampering, Information Disclosure, Elevation of Privilege
- SR-003: Information Disclosure, Tampering
- SR-004: Elevation of Privilege, Tampering, Repudiation

## Status 2025-10-25

Alle oben genannten Risiken wurden mit den beigefügten Patches mitigiert; Rest-Risiko besteht nur bei nicht rotierten Secrets.
```
