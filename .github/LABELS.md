# 🏷️ Label-Strategie — Claire de Binaire

**Status:** Aktiv  
**Owner:** Maintainer  
**Last Updated:** 2025-12-19

---

## Prinzip: 3-Achsen-System

Jedes Issue/PR erhält Labels aus **maximal 3 Dimensionen:**

1. **Type** (Was?) → `type:*`
2. **Scope** (Wo?) → `scope:*`
3. **Priority** (Wann?) → `prio:*`

Zusätzlich:
- **Status** → `status:*` (Lifecycle)
- **Tech Tags** → `python`, `docker`, `redis`, etc.

---

## Label-Referenz

### Type (Was wird gemacht?)

| Label | Beschreibung | Beispiel |
|-------|-------------|----------|
| `type:bug` | Fehlerbehebung | CI-Pipeline schlägt fehl |
| `type:feature` | Neue Funktion | Redis Retry-Logik |
| `type:refactor` | Code-Umbau ohne Funktionsänderung | DRY in `risk_engine.py` |
| `type:docs` | Dokumentation | ADR-031 hinzufügen |
| `type:chore` | Wartung, Cleanup, Tooling | Workflows aufräumen |
| `type:security` | Sicherheitsproblem | Secrets in `.env.example` |

### Scope (Wo wird gearbeitet?)

| Label | Beschreibung | Services/Dateien |
|-------|-------------|------------------|
| `scope:core` | Trading Core | `signal_engine`, `risk_engine`, `order_manager`, `position_tracker` |
| `scope:infra` | Infrastructure | `docker-compose.yml`, Netzwerk, Secrets |
| `scope:ci` | CI/CD | `.github/workflows/*` |
| `scope:monitoring` | Observability | Prometheus, Grafana, Alerts |
| `scope:data` | Persistence | PostgreSQL, Redis, Migrations |
| `scope:docs` | Dokumentation | `docs/`, ADRs, README |

### Priority (Wann?)

| Label | Beschreibung | SLA |
|-------|-------------|-----|
| `prio:must` | Release Blocker | Vor nächstem Release |
| `prio:should` | Hoch | Nächstes Milestone |
| `prio:nice` | Nice-to-Have | Backlog |

### Status (Lifecycle)

| Label | Beschreibung |
|-------|-------------|
| `status:ready` | Bereit zur Bearbeitung |
| `status:blocked` | Blockiert (Dependency/Admin) |
| `status:in-review` | PR offen |
| `status:wontfix` | Wird nicht bearbeitet |

> **Hinweis:** Dies ist die kanonische `status:*`-Menge. Alte Labels wie
> `status:idea`, `status:approved`, `status:review`, `status:merged`,
> `status:descoped`, `status:rejected` sind **nicht** kanonisch und werden
> weder in Workflows noch im Board-Mapping verwendet. Project-v2-Statuswerte
> (`Backlog`, `Ready`, `In Progress`, `Review`, `Done`) sind Board-Feldwerte,
> keine Labels.

### Triage

| Label | Beschreibung |
|-------|-------------|
| `triage:offen` | Offenes Item ohne Milestone — Triage erforderlich |

### Tech Tags (Optional)

| Label | Verwendung |
|-------|-----------|
| `python` | Python-Code, Typisierung |
| `docker` | Docker, Compose |
| `redis` | Redis Pub/Sub, Streams |
| `postgres` | PostgreSQL, Schemas |
| `testing` | Test-Coverage, E2E |
| `dependencies` | Dependabot Updates |

---

## Beispiele

### Issue: CI-Pipeline bricht bei Unit-Tests ab
```
type:bug
scope:ci
prio:should
testing
```

### Issue: Neue Redis-Verbindung mit Retry-Logik
```
type:feature
scope:data
prio:nice
redis
python
```

### Issue: Docker-Secrets nicht in docker-compose.yml
```
type:security
scope:infra
prio:must
docker
```

### Issue: ADR-031 Dokumentation fehlt
```
type:docs
scope:docs
prio:should
```

---

## Migration bestehender Labels

**Entfernte Labels:**
- `type:testing` → `testing` + `type:chore`/`type:feature`
- `scope:security` → `type:security`
- `infrastructure` → `scope:infra`
- `security` → `type:security`
- `monitoring` → `scope:monitoring`
- `ci-cd` → `scope:ci`
- `github-actions` → `scope:ci`
- Alle `milestone:m1-m9` → GitHub Milestones (native)
- Alle `epic:*` → GitHub Projects

**Neue Labels:**
- `type:refactor` (explizite Code-Umbauten)
- `scope:data` (PostgreSQL/Redis)
- `status:wontfix` (explizite Closures)

---

## Automatisierung

- **Auto-Sync:** `.github/workflows/sync-labels.yml` synchronisiert Labels bei Push
- **Manual Sync:** `gh workflow run sync-labels.yml`

---

## Wartung

Labels werden zentral in `.github/workflows/labels.json` verwaltet.

**Review-Zyklus:** Quartalsweise (oder bei Bedarf)
