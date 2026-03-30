# Docker Compose Fragmente

Governance-konforme Infrastruktur-Definition (CDB_INFRA_POLICY.md).

## Struktur

```
infrastructure/compose/
├── compose.blue.yml     # BLUE runtime (Core: Postgres, Redis, Risk, Execution, …)
├── compose.red.yml      # RED runtime (Signal, WS, Prometheus, Grafana, …)
├── base.yml             # Legacy shared base (CI/test only)
├── dev.yml              # Legacy dev overlay (CI/test only)
├── test.yml             # 431B Docker CI lab overlay
├── Dockerfile.test      # Test-runner image for test.yml
├── TEST_OVERLAY_README.md # CI-lab usage notes
├── prod.yml             # Legacy prod overlay
├── surrealdb.yml        # SurrealDB sidecar stack
├── surrealdb-dev.yml    # SurrealDB dev ports (localhost only)
└── README.md            # Diese Datei
```

## Kanonische Pfade

### Lokale Runtime
```bash
docker compose -f infrastructure/compose/compose.blue.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d
```

### Docker CI Lab Baseline (431B)
```bash
docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/test.yml up --abort-on-container-exit
```

### Legacy Compose Chain (CI/test only)

`base.yml + dev.yml` ist **nicht** der kanonische Runtime-Pfad. Sie bleibt nur fuer CI-Labs und explizite Kompatibilitaetsflows:

```bash
# CI Lab Baseline
docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/test.yml up --abort-on-container-exit
```

### SurrealDB Sidecar (Standalone)
```bash
docker compose -f infrastructure/compose/surrealdb.yml -f infrastructure/compose/surrealdb-dev.yml up -d
```

Mit `surrealdb-dev.yml` liegt SurrealDB lokal auf `127.0.0.1:8010`, damit es nicht mit `cdb_ws` auf `127.0.0.1:8000` kollidiert.

## Governance-Compliance

- **CDB_INFRA_POLICY.md**: IaC + GitOps, fragmentierte Compose-Dateien
- **CDB_CONSTITUTION.md**: Stateless Services, ENV-only Config
- **CDB_GOVERNANCE.md**: Git als Single Source of Truth

## Fragmente-Beschreibung

### base.yml
- **Zweck**: Shared base fuer dev/prod/test
- **Services**: Redis, Postgres, Prometheus, Grafana
- **Netzwerk**: cdb_network (bridge)
- **Volumes**: Named Volumes (redis_data, postgres_data, etc.)
- **Secrets**: Via ./.secrets/ Dateien

### test.yml
- **Zweck**: Kanonische 431B Docker CI lab baseline
- **Modell**: Isolierter Test-Overlay ueber `base.yml`
- **Isolation**: Separate `_test` Container, Volumes und `cdb_test_network`
- **Runner**: `cdb_test_runner` baut aus `Dockerfile.test` und fuehrt pytest im Container aus

### dev.yml
- **Zweck**: Secondary local/compatibility overrides
- **Port-Bindings**: Alle Services extern erreichbar
- **Debug-Volumes**: Logs gemountet
- **Relaxed Security**: Kein read-only, CAP_DROP
- **Application Services**: cdb_ws, cdb_signal, cdb_risk, cdb_execution, cdb_db_writer

### prod.yml
- **Zweck**: Production Overrides
- **Resource-Limits**: CPU & Memory Caps
- **Restart-Policy**: on-failure (nicht unless-stopped)
- **Enhanced Security**: read-only, no-new-privileges, CAP_DROP=ALL
- **Health-Checks**: Verschärft (kürzere Intervalle)

## Migration von Legacy

Die root-level `docker-compose.yml` existiert nicht mehr im Working Repo.

**Kanonische Pfade:**
1. **Runtime:** `compose.blue.yml` + `compose.red.yml` (oder `make docker-up`)
2. **CI-Lab:** `base.yml` + `test.yml` (isolierter Test-Overlay)

## Kubernetes-Readiness

Diese Fragmente sind K8s-ready:
- Stateless Services (kein lokaler State)
- ENV-only Config (kein Hardcoding)
- Health-Endpoints (/health, /ready)
- Service Isolation (eigenständig deploybar)

## Nächste Schritte

- [ ] Sekundaere Workflow-Pfade bei Bedarf spaeter auf die 431B-Baseline ziehen
- [ ] K8s-Manifeste aus Fragmenten generieren (via Kompose)
