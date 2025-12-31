# Container Hardening

## Status: Implementiert (Issue #98)

Dieses Dokument beschreibt die Container-Härtungsmaßnahmen für CDB.

## Implementierte Maßnahmen

### 1. Non-Root User

Alle Service-Container laufen als non-root User:

| Service | User | UID |
|---------|------|-----|
| cdb_execution | execuser | 1000 |
| cdb_risk | riskuser | 1000 |
| cdb_signal | signaluser | 1000 |
| cdb_allocation | allocuser | 1000 |
| cdb_db_writer | dbwriter | 1000 |
| cdb_ws | wsuser | 1000 |

### 2. Security Options (docker-compose)

```yaml
security_opt:
  - no-new-privileges:true
cap_drop:
  - ALL
tmpfs:
  - /tmp
read_only: true
```

Angewendet auf:
- cdb_ws
- cdb_core
- cdb_risk
- cdb_execution

### 3. Base Images

| Service | Base Image | Größe |
|---------|------------|-------|
| Python Services | python:3.11-slim | ~130MB |
| Redis | redis:7.4.1-alpine | ~30MB |
| PostgreSQL | postgres:15.11-alpine | ~75MB |
| Prometheus | prom/prometheus:v3.1.0 | ~85MB |
| Grafana | grafana/grafana:11.4.0 | ~200MB |

### 4. CVE Mitigation

- **pip 25.3**: Alle Python-Images verwenden pip 25.3 (CVE-2025-8869 behoben)
- **Alpine Images**: Infrastruktur-Container verwenden Alpine-basierte Images

## Dockerfile Best Practices

### Aktuelles Template

```dockerfile
# Service Name - Gehärtetes Image
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Upgrade pip to fix CVEs
RUN pip install --upgrade pip==25.3

# System dependencies (minimal)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Python Requirements
COPY services/<service>/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Application Code
COPY core /app/core
COPY services/<service>/ /app

# Non-Root User
RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

# Health-Check
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD curl -f http://localhost:<port>/health || exit 1

EXPOSE <port>

CMD ["python", "-u", "service.py"]
```

## Compose-Level Hardening

### Vollständige Security-Konfiguration

```yaml
services:
  cdb_<service>:
    # ... image/build config ...
    user: "1000:1000"
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    # Optional: Specific capabilities if needed
    # cap_add:
    #   - NET_BIND_SERVICE
    tmpfs:
      - /tmp
    read_only: true
    # Memory/CPU limits
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
```

## Checkliste

### Container-Ebene
- [x] Non-root user in Dockerfile
- [x] PYTHONDONTWRITEBYTECODE=1
- [x] PYTHONUNBUFFERED=1
- [x] pip upgrade für CVE fixes
- [x] --no-cache-dir bei pip install
- [x] rm -rf /var/lib/apt/lists/*
- [x] Minimal dependencies (curl only)

### Compose-Ebene
- [x] no-new-privileges
- [x] cap_drop: ALL
- [x] read_only: true
- [x] tmpfs: /tmp
- [x] user: 1000:1000

### Ausstehend (Optional)
- [ ] Alpine statt Slim (kleinere Images, aber kompilierungs-aufwändiger)
- [ ] Multi-stage builds für kleinere finale Images
- [ ] Distroless base images (keine Shell)

## Verifikation

### Prüfen ob Container als non-root läuft:
```bash
docker exec cdb_execution whoami
# Erwartet: execuser (nicht root)
```

### Prüfen ob Capabilities gedroppt wurden:
```bash
docker exec cdb_execution cat /proc/1/status | grep Cap
# CapBnd sollte 0 oder minimal sein
```

### Prüfen ob read-only:
```bash
docker exec cdb_execution touch /test
# Erwartet: touch: cannot touch '/test': Read-only file system
```

## Referenzen

- Issue #98: Container Hardening
- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- SECURITY_ROADMAP.md M8 Phase 1
