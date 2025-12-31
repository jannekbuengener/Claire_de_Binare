# Docker Compose Fragmente

Governance-konforme Infrastruktur-Definition (CDB_INFRA_POLICY.md).

## Struktur

```
infrastructure/compose/
├── base.yml    # Core Infrastructure (Redis, Postgres, Prometheus, Grafana)
├── dev.yml     # Dev Overrides (Port-Bindings, Debug-Volumes)
├── prod.yml    # Prod Overrides (Resource-Limits, Security)
└── README.md   # Diese Datei
```

## Usage

### Development
```bash
docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/dev.yml up -d
```

### Production
```bash
docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/prod.yml up -d
```

### Legacy (Fallback)
```bash
docker compose up -d  # Nutzt root-level docker-compose.yml
```

## Governance-Compliance

- **CDB_INFRA_POLICY.md**: IaC + GitOps, fragmentierte Compose-Dateien
- **CDB_CONSTITUTION.md**: Stateless Services, ENV-only Config
- **CDB_GOVERNANCE.md**: Git als Single Source of Truth

## Fragmente-Beschreibung

### base.yml
- **Zweck**: Core Infrastructure (immer benötigt)
- **Services**: Redis, Postgres, Prometheus, Grafana
- **Netzwerk**: cdb_network (bridge)
- **Volumes**: Named Volumes (redis_data, postgres_data, etc.)
- **Secrets**: Via ./.secrets/ Dateien

### dev.yml
- **Zweck**: Development Overrides
- **Port-Bindings**: Alle Services extern erreichbar
- **Debug-Volumes**: Logs gemountet
- **Relaxed Security**: Kein read-only, CAP_DROP
- **Application Services**: cdb_ws, cdb_core, cdb_risk, cdb_execution, cdb_db_writer

### prod.yml
- **Zweck**: Production Overrides
- **Resource-Limits**: CPU & Memory Caps
- **Restart-Policy**: on-failure (nicht unless-stopped)
- **Enhanced Security**: read-only, no-new-privileges, CAP_DROP=ALL
- **Health-Checks**: Verschärft (kürzere Intervalle)

## Migration von Legacy

Legacy `docker-compose.yml` bleibt als Fallback erhalten (Abwärtskompatibilität).

**Empfohlene Migration:**
1. Testen mit Dev-Fragmenten: `docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/dev.yml up -d`
2. Validieren: Alle Services starten korrekt
3. Makefile anpassen: `make docker-up` nutzt Fragmente
4. Legacy `docker-compose.yml` als Backup behalten

## Kubernetes-Readiness

Diese Fragmente sind K8s-ready:
- Stateless Services (kein lokaler State)
- ENV-only Config (kein Hardcoding)
- Health-Endpoints (/health, /ready)
- Service Isolation (eigenständig deploybar)

## Nächste Schritte

- [ ] Makefile anpassen (PR-03)
- [ ] .env.example aktualisieren
- [ ] CI-Integration (.gitlab-ci.yml prüft Fragmente)
- [ ] K8s-Manifeste aus Fragmenten generieren (via Kompose)
