# Canonical Model Overview - Claire de Binare

**Erstellt von**: claire-architect
**Datum**: 2025-11-16
**Zweck**: Autoritative Strukturdefinition für das kanonische Systemmodell

---

## Zielbild

Das kanonische Systemmodell ist die **Single Source of Truth** für alle Aspekte des Claire-de-Binare-Systems.
Es bildet die Grundlage für:
- Cleanroom-Migration
- Automatische Code-Generierung
- Deployment-Automation
- Test-Suite-Generierung
- Governance & Compliance
- Dokumentations-Synchronisation

---

## Kategorien & Entitäten

### 1. Services

**Definition**: Eigenständige, containerisierte Softwarekomponenten mit definierten Schnittstellen.

**Struktur**:
| Feld | Typ | Beschreibung | Pflicht |
|------|-----|--------------|---------|
| `id` | String | Eindeutiger Identifier (z.B. `cdb_core`) | ✅ |
| `name` | String | Menschenlesbarer Name (z.B. "Signal Engine") | ✅ |
| `description` | String | Funktionale Beschreibung | ✅ |
| `container_name` | String | Docker-Container-Name | ✅ |
| `image` | String | Docker-Image (z.B. `python:3.11-slim` oder Build-Context) | ✅ |
| `port_host` | Integer | Host-Port | ⚠️ Optional |
| `port_container` | Integer | Container-Port | ✅ |
| `health_endpoint` | String | Health-Check-Pfad (z.B. `/health`) | ✅ |
| `metrics_endpoint` | String | Prometheus-Metrics-Pfad | ⚠️ Optional |
| `dependencies` | List[String] | Abhängige Services (IDs) | ⚠️ Optional |
| `consumes_topics` | List[String] | Redis-Topics, die konsumiert werden | ⚠️ Optional |
| `produces_topics` | List[String] | Redis-Topics, die produziert werden | ⚠️ Optional |
| `env_variables` | List[String] | Benötigte ENV-Variablen (Keys) | ⚠️ Optional |
| `volumes` | List[Object] | Volume-Mappings | ⚠️ Optional |
| `security_flags` | Object | Security-Hardening (non-root, read-only, caps) | ⚠️ Optional |
| `network` | String | Docker-Netzwerk | ✅ |
| `restart_policy` | String | Restart-Verhalten (z.B. `unless-stopped`) | ✅ |

**Beziehungen**:
- `Service` → nutzt `ENV-Variablen`
- `Service` → konsumiert/produziert `Events`
- `Service` → abhängig von `Service` (Dependencies)
- `Service` → exponiert `Monitoring`-Metriken
- `Service` → unterliegt `Security`-Policies

---

### 2. ENV-Variablen

**Definition**: Konfigurationsparameter, die zur Laufzeit aus der Umgebung geladen werden.

**Struktur**:
| Feld | Typ | Beschreibung | Pflicht |
|------|-----|--------------|---------|
| `key` | String | ENV-Variablen-Name (z.B. `MAX_DAILY_DRAWDOWN_PCT`) | ✅ |
| `description` | String | Bedeutung der Variable | ✅ |
| `category` | Enum | `Secret`, `Config`, `Feature-Flag`, `Infra` | ✅ |
| `type` | Enum | `string`, `int`, `float`, `bool` | ✅ |
| `unit` | String | Einheit (z.B. `percent`, `seconds`) | ⚠️ Optional |
| `default` | Any | Standardwert | ⚠️ Optional |
| `min` | Number | Minimaler Wert | ⚠️ Optional |
| `max` | Number | Maximaler Wert | ⚠️ Optional |
| `required` | Boolean | Pflichtfeld? | ✅ |
| `scope` | Enum | `global`, `service-specific` | ✅ |
| `used_by_services` | List[String] | Service-IDs, die diese Variable nutzen | ⚠️ Optional |

**Beziehungen**:
- `ENV-Variable` → genutzt von `Service`
- `ENV-Variable` (Risk-Parameter) → beeinflusst `Risk-Parameter`
- `ENV-Variable` (Secret) → unterliegt `Security`-Policy

---

### 3. Risk-Parameter

**Definition**: Spezielle ENV-Variablen, die das Risikomanagement steuern.

**Struktur**:
| Feld | Typ | Beschreibung | Pflicht |
|------|-----|--------------|---------|
| `name` | String | Parameter-Name (z.B. "Daily Drawdown Limit") | ✅ |
| `env_key` | String | ENV-Variablen-Key (z.B. `MAX_DAILY_DRAWDOWN_PCT`) | ✅ |
| `unit` | String | Einheit (z.B. `decimal`, `percent`) | ✅ |
| `default` | Number | Standardwert | ✅ |
| `min` | Number | Minimaler Wert | ✅ |
| `max` | Number | Maximaler Wert | ✅ |
| `layer` | Integer | Risk-Layer-Priorität (1 = höchste) | ✅ |
| `effect` | String | Wirkung (z.B. "Halt trading immediately") | ✅ |
| `guard_type` | Enum | `hard_limit`, `soft_limit`, `circuit_breaker` | ✅ |

**Beziehungen**:
- `Risk-Parameter` → Teil von `Workflows` (Risk-Guards)
- `Risk-Parameter` → mapped zu `ENV-Variablen`
- `Risk-Parameter` → validiert durch `claire-risk-engine-guardian`

---

### 4. Workflows

**Definition**: Prozesse mit definierten Triggern, Schritten und Guards.

**Struktur**:
| Feld | Typ | Beschreibung | Pflicht |
|------|-----|--------------|---------|
| `name` | String | Workflow-Name (z.B. "Signal Validation") | ✅ |
| `trigger` | String | Auslöser (z.B. "Signal Event received") | ✅ |
| `steps` | List[Object] | Workflow-Schritte (Name, Service, Aktion) | ✅ |
| `guards` | List[Object] | Risk-Guards (Parameter, Bedingung, Aktion) | ⚠️ Optional |
| `fallbacks` | List[Object] | Fallback-Verhalten bei Fehlern | ⚠️ Optional |
| `timeout` | Integer | Max. Ausführungszeit (Sekunden) | ⚠️ Optional |

**Beziehungen**:
- `Workflow` → nutzt `Risk-Parameter` als Guards
- `Workflow` → ausgeführt durch `Service`
- `Workflow` → publiziert `Events`
- `Workflow` → triggert `Monitoring`-Alerts

---

### 5. Events

**Definition**: Nachrichten, die über Redis Pub/Sub zwischen Services ausgetauscht werden.

**Struktur**:
| Feld | Typ | Beschreibung | Pflicht |
|------|-----|--------------|---------|
| `topic` | String | Topic-Name (z.B. `market_data`) | ✅ |
| `producer` | List[String] | Service-IDs, die dieses Event produzieren | ✅ |
| `consumers` | List[String] | Service-IDs, die dieses Event konsumieren | ✅ |
| `schema` | Object | JSON-Schema des Event-Payloads | ✅ |
| `frequency` | String | Erwartete Frequenz (z.B. "continuous", "on-demand") | ⚠️ Optional |
| `retention` | String | Retention-Policy (z.B. "none", "persist to DB") | ⚠️ Optional |

**Beziehungen**:
- `Event` → produziert von `Service`
- `Event` → konsumiert von `Service`
- `Event` → definiert in `EVENT_SCHEMA.json`
- `Event` → Teil von `Workflows`

---

### 6. Monitoring

**Definition**: Observability-Komponenten (Metriken, Alerts, Dashboards).

**Struktur**:
| Feld | Typ | Beschreibung | Pflicht |
|------|-----|--------------|---------|
| `type` | Enum | `metric`, `alert`, `dashboard` | ✅ |
| `name` | String | Monitoring-Element-Name | ✅ |
| `source` | String | Quelle (z.B. Service-ID, Event-Topic) | ✅ |
| `level` | Enum | `CRITICAL`, `WARNING`, `INFO` (nur Alerts) | ⚠️ Optional |
| `target` | String | Ziel (z.B. `prometheus`, `grafana`, `alerts` Topic) | ✅ |
| `payload_format` | String | Format der Daten (z.B. JSON-Schema für Alerts) | ⚠️ Optional |

**Beziehungen**:
- `Monitoring` (Metric) → scraped von `prometheus`
- `Monitoring` (Alert) → publiziert auf `alerts` Event-Topic
- `Monitoring` (Dashboard) → visualisiert in `grafana`
- `Monitoring` → verbunden mit `Service`

---

### 7. Storage

**Definition**: Persistente Datenspeicher (Volumes, Datenbanken).

**Struktur**:
| Feld | Typ | Beschreibung | Pflicht |
|------|-----|--------------|---------|
| `type` | Enum | `volume`, `database` | ✅ |
| `name` | String | Storage-Name (z.B. `redis_data`, `claire_de_binare` DB) | ✅ |
| `driver` | String | Storage-Driver (z.B. `local`, `postgres`) | ✅ |
| `used_by_services` | List[String] | Service-IDs, die diesen Storage nutzen | ✅ |
| `backup_policy` | String | Backup-Strategie | ⚠️ Optional |
| `size_limit` | String | Größenlimit (falls relevant) | ⚠️ Optional |

**Beziehungen**:
- `Storage` → genutzt von `Service`
- `Storage` → unterliegt `Security`-Policies (Encryption, Access Control)

---

### 8. Security

**Definition**: Security-Policies, Hardening-Flags, Secrets-Management.

**Struktur**:
| Feld | Typ | Beschreibung | Pflicht |
|------|-----|--------------|---------|
| `policy_name` | String | Security-Policy-Name | ✅ |
| `scope` | Enum | `service`, `network`, `storage`, `env` | ✅ |
| `flags` | Object | Security-Flags (z.B. `no-new-privileges`, `read_only`) | ✅ |
| `applied_to` | List[String] | Entitäten (Service-IDs, Storage-Namen) | ✅ |
| `risk_level` | Enum | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` | ✅ |
| `enforcement` | Enum | `mandatory`, `recommended`, `optional` | ✅ |

**Beziehungen**:
- `Security` → angewendet auf `Service`, `Storage`, `ENV-Variablen`
- `Security` → validiert durch `claire-risk-engine-guardian`
- `Security` (Secrets) → Teil von `ENV-Variablen` (Kategorie `Secret`)

---

### 9. Infra/Runtime

**Definition**: Infrastruktur-Komponenten (Netzwerke, Ports, Container-Runtime).

**Struktur**:
| Feld | Typ | Beschreibung | Pflicht |
|------|-----|--------------|---------|
| `type` | Enum | `network`, `port_mapping`, `runtime_config` | ✅ |
| `name` | String | Infra-Element-Name | ✅ |
| `configuration` | Object | Spezifische Konfiguration | ✅ |
| `services` | List[String] | Betroffene Service-IDs | ⚠️ Optional |

**Beziehungen**:
- `Infra/Runtime` → verbindet `Services` (Netzwerke)
- `Infra/Runtime` → exponiert `Services` (Port-Mappings)

---

## Beziehungsmatrix

| Von ↓ / Zu → | Services | ENV | Risk-Param | Workflows | Events | Monitoring | Storage | Security | Infra |
|--------------|----------|-----|------------|-----------|--------|------------|---------|----------|-------|
| **Services** | Depends | Nutzt | — | Führt aus | Prod/Cons | Exponiert | Nutzt | Unterliegt | Teil von |
| **ENV** | Genutzt von | — | Mapped zu | — | — | — | — | Unterliegt | — |
| **Risk-Param** | — | Mapped zu | — | Guards für | — | — | — | — | — |
| **Workflows** | Ausgeführt von | — | Nutzt | — | Triggert | Triggert | — | — | — |
| **Events** | Prod/Cons von | — | — | Teil von | — | — | — | — | — |
| **Monitoring** | Von | — | — | — | — | — | — | — | — |
| **Storage** | Genutzt von | — | — | — | — | — | — | Unterliegt | — |
| **Security** | Auf | Auf | — | — | — | — | Auf | — | — |
| **Infra** | Verbindet | — | — | — | — | — | — | — | — |

---

## Nutzung für Code-Generierung

### Automatische Artefakte

Aus dem kanonischen Modell können folgende Artefakte automatisch generiert werden:

1. **docker-compose.yml**
   - Services → Container-Definitionen
   - ENV → environment-Sections
   - Security → security_opt, cap_drop, read_only
   - Infra → networks, volumes, ports

2. **Pydantic-Models**
   - Events → Schema-Klassen
   - ENV → Config-Klassen mit Validierung (pydantic-settings)
   - Risk-Parameter → Risk-Config-Klassen

3. **Test-Suites**
   - Services → Health-Check-Tests
   - Workflows → Integration-Tests
   - Risk-Parameter → Unit-Tests (Range-Checks, Limit-Validierung)

4. **Dokumentation**
   - Services → Service-Catalog
   - Events → Event-Schema-Docs
   - Risk-Parameter → Risk-Management-Guide
   - Workflows → Process-Documentation

5. **Deployment-Pipelines**
   - Services → Build-Stages
   - Dependencies → Deploy-Order
   - Health-Checks → Readiness-Gates

### Template-Generierung

- `canonical_schema.yaml` → JSON-Schema für Validierung
- `canonical_system_map.md` → System-Übersicht (menschlich lesbar)
- `canonical_deployment_manifest.yml` → Kubernetes/Docker-Swarm-Manifest

### Governance & Compliance

- **Completeness-Check**: Alle Services haben Health-Endpoints?
- **Security-Audit**: Alle Services mit Hardening-Flags?
- **Risk-Validation**: Alle Risk-Parameter innerhalb Min/Max?
- **Consistency-Check**: ENV-Namen, Event-Schemas, Service-Dependencies konsistent?

---

## Nächste Schritte (Phase 2+)

1. **software-jochen**: Extraktion aller Entities aus bestehenden Dokus → `canonical_schema.yaml`
2. **agata-van-data**: Konfliktauflösung, Normalisierung → `facts_canonical.md`
3. **devops-infrastructure-architect**: System-Map, Deployment-Prinzipien → `canonical_system_map.md`
4. **claire-risk-engine-guardian**: Risk-/Security-Finalisierung → Sektion in `facts_canonical.md`
5. **Alle Agenten**: Migration-Plan, Decision-Log, Readiness-Report

---

**Status**: Phase 1 abgeschlossen ✅
**Nächste Phase**: software-jochen extrahiert Entities aus Dokus
