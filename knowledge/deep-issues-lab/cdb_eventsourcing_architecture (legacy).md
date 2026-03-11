# Claire de Binare (CDB) – Event-Sourcing & Message-Bus Architektur

**Version:** 1.0  
**Datum:** Dezember 2024  
**Status:** Architektur-Konzept & Migrationsplan

---

## Executive Summary

Dieses Dokument definiert die Event-Sourcing-Strategie und Message-Bus-Migration für Claire de Binare (CDB), ein hochperformantes Krypto-Trading-System. Die Kernziele sind:

- **Determinismus:** Vollständige Reproduzierbarkeit aller Trading-Entscheidungen durch Event-Historie
- **Backtesting & Replay:** Sub-ms-präzise Simulation historischer Szenarien für Strategie-Optimierung
- **Latenz-Optimierung:** Sub-millisekunde Latenz für kritische Hot-Paths bei garantierter Delivery
- **Robustheit:** Kein Single-Point-of-Failure, Guaranteed Delivery, kein Blackbox-Verhalten

**Empfohlener Migrationspfad (18 Monate):**
- Phase 1 (3 Monate): Redis Pub/Sub + PostgreSQL Event-Log (MVP)
- Phase 2 (6 Monate): Hybrid-Betrieb mit NATS JetStream für kritische Streams
- Phase 3 (9 Monate): Vollständiger NATS JetStream Backbone, Kafka optional für Analytics

**Warum NATS JetStream als Hauptempfehlung:**
- Sub-millisekunde P99-Latenzen (<2ms vs. Kafka 15-50ms)
- Eingebautes Replay & Persistence ohne Zookeeper-Komplexität
- Deutlich einfachere Betriebsführung als Kafka
- Native Go-Integration (falls CDB Python-Services um Go-Komponenten erweitert)

---

## 1. Best Practices: Event-Sourcing in Trading-Systemen

### 1.1 Kernprinzipien aus HFT/Trading-Domäne

Basierend auf Recherche erfolgreicher Trading-Systeme (LMAX Disruptor, Exchange Core, Touch-Fire Trading):

**Event-First Design:**
- Alle Zustandsänderungen werden als immutable Events persistiert
- Current State wird durch Event-Replay rekonstruiert (CQRS-Pattern)
- Events sind die Single Source of Truth

**Latenz-Optimierung:**
- In-Memory Processing für Hot-Path (Order-Matching, Risk-Checks)
- Asynchrone Persistierung mit LMAX Disruptor-Pattern
- Event-Batching nur für Cold-Storage, nie im kritischen Pfad

**Determinismus:**
- Jedes Event mit präzisem Timestamp (µs-Auflösung) und Sequence-Number
- Reproduzierbare Order bei Event-Replay durch Sequencing
- Keine Abhängigkeit von externen Non-Deterministischen Quellen während Replay

**CQRS (Command Query Responsibility Segregation):**
- Write-Model: Commands → Events → Event Store
- Read-Model: Projektionen aus Events für schnelle Queries
- Separate Skalierung von Write- und Read-Operationen

### 1.2 Event-Driven Backtesting

Kritische Erkenntnisse aus der QuantStart-Community:
- Event-Driven Backtester eliminieren Lookahead-Bias komplett
- "Drip-Feed" von Market-Data-Events simuliert Live-Betrieb exakt
- Code-Reuse: Identischer Event-Handler für Backtest & Live-Trading

**CDB-Spezifische Anforderungen:**
- Replay-Speed: 100-1000x Echtzeit für schnelles Backtesting
- Snapshot-Support: Starte Replay von beliebigem Zeitpunkt
- Multi-Strategy Replay: Paralleles Testen mehrerer Strategien

---

## 2. Technologie-Vergleich: Redis Pub/Sub vs. Kafka vs. NATS JetStream

### 2.1 Vergleichstabelle

| **Kriterium** | **Redis Pub/Sub** | **Apache Kafka** | **NATS JetStream** |
|---------------|-------------------|------------------|-------------------|
| **Latenz (P99)** | <1ms | 15-50ms (mit Replication) | <2ms |
| **Latenz (P999)** | <5ms | 50-250ms | <10ms |
| **Durchsatz** | 100k-200k msg/s (single instance) | 1M+ msg/s (cluster) | 200k-500k msg/s (3-node cluster) |
| **Persistence** | ❌ Fire-and-Forget (Pub/Sub), ✅ Redis Streams | ✅ Log-basiert, konfigurierbare Retention | ✅ File- oder Memory-backed, flexibel |
| **Message Replay** | ❌ Nicht möglich (Pub/Sub), ✅ Redis Streams | ✅ Consumer-Offset-basiert | ✅ Zeit, Count oder Sequence-basiert |
| **Delivery Guarantee** | At-Most-Once | At-Least-Once, Exactly-Once | At-Most, At-Least, Exactly-Once |
| **Ordering** | ✅ Pro Channel | ✅ Pro Partition | ✅ Pro Stream/Subject |
| **Setup-Komplexität** | ⭐ Sehr einfach | ⭐⭐⭐⭐ Komplex (Zookeeper/KRaft, Partitions) | ⭐⭐ Moderat |
| **Betriebsaufwand** | ⭐ Minimal | ⭐⭐⭐⭐ Hoch (JVM-Tuning, Disk-Management) | ⭐⭐ Niedrig |
| **Horizontal Scaling** | ❌ Limitiert (Sharding komplex) | ✅ Exzellent (Partitions, Consumer Groups) | ✅ Gut (Clustering, Replication) |
| **Memory Overhead** | ⭐⭐ Niedrig (in-memory only) | ⭐⭐⭐⭐ Hoch (JVM Heap, Page Cache) | ⭐⭐ Niedrig (Go-Binary, effizient) |
| **Ökosystem** | Redis-Tooling | ✅ Riesig (Kafka Connect, Streams API) | ⭐⭐ Wachsend |
| **CDB-Eignung Hot-Path** | ✅ Exzellent | ❌ Zu hohe Latenz | ✅ Exzellent |
| **CDB-Eignung Analytics** | ❌ Keine Persistence | ✅ Optimal | ⭐⭐ Gut |

### 2.2 Detailanalyse

**Redis Pub/Sub:**
- **Vorteile:** Ultra-Low-Latency, einfachste Integration, bereits in CDB-Stack
- **Nachteile:** Keine Message-Persistence, keine Replay-Fähigkeit, Fire-and-Forget
- **Redis Streams als Alternative:** Persistenz + Consumer Groups, aber höhere Latenz als Pub/Sub
- **Anwendungsfall:** Ephemere Real-Time-Notifications, nicht für Event-Sourcing geeignet

**Apache Kafka:**
- **Vorteile:** Massive Throughput, exzellente Persistenz, riesiges Ökosystem
- **Nachteile:** Hohe Tail-Latencies (P99/P999), operationale Komplexität, JVM-Overhead
- **Anwendungsfall:** Analytics, Data-Pipelines, Event-Store für Cold-Storage
- **Nicht geeignet für:** Sub-ms Trading-Decisions, Low-Latency Order-Routing

**NATS JetStream:**
- **Vorteile:** Sub-ms Latenz, eingebautes Replay, einfache Ops, Golang-Effizienz
- **Nachteile:** Kleineres Ökosystem als Kafka, weniger Integrations-Tools
- **Anwendungsfall:** Low-Latency Event-Streaming, Microservices-Messaging, HFT-Systeme
- **Perfekt für CDB:** Balance zwischen Latenz, Persistenz und Betriebsfreundlichkeit

---

## 3. Zielarchitektur: Event-Sourcing in CDB

### 3.1 Event-Typen & Topics/Streams

**Primäre Event-Kategorien:**

1. **MarketData Events** (extern, read-only)
   - `marketdata.ticker.{symbol}` – Order-Book-Updates, Trades
   - `marketdata.candle.{symbol}.{timeframe}` – OHLCV-Daten
   - Volume: ~10k events/sec (Binance WebSocket Feed)
   - Retention: 30 Tage Hot + 1 Jahr Cold (S3)

2. **Signal Events** (intern, Strategy-Output)
   - `signals.strategy.{strategy_id}.{symbol}` – Buy/Sell-Signale
   - Payload: Signal-Strength, Confidence, Timestamp, Strategie-Metadaten
   - Volume: ~100-500 events/sec
   - Retention: 90 Tage Hot + 5 Jahre Cold (Backtesting)

3. **Risk Events** (intern, Risk-Engine)
   - `risk.decision.{account_id}` – Position-Limits, Exposure-Checks
   - `risk.alert.{severity}` – Warnungen, Circuit-Breaker-Triggers
   - Volume: ~50-200 events/sec
   - Retention: 1 Jahr (Compliance)

4. **Order Events** (intern, Order-Management)
   - `orders.command.{account_id}` – Neue Orders, Cancellations
   - `orders.status.{order_id}` – Status-Updates (Pending, Filled, Rejected)
   - Volume: ~200-1000 events/sec
   - Retention: 7 Jahre (regulatorische Anforderung)

5. **Fill Events** (extern + intern)
   - `fills.exchange.{exchange}.{symbol}` – Fills von Exchange
   - `fills.internal.{order_id}` – Interne Fill-Aggregation
   - Volume: ~100-500 events/sec
   - Retention: 7 Jahre (regulatorisch)

6. **PSM (Position State Machine) Events**
   - `psm.state.{position_id}` – Position-Lifecycle (Open, Modify, Close)
   - `psm.pnl.{position_id}` – Realized/Unrealized PnL-Updates
   - Volume: ~50-200 events/sec
   - Retention: 1 Jahr Hot + 7 Jahre Cold

### 3.2 Event-Schema-Design

**Event-Envelope (universell):**
```json
{
  "event_id": "uuid-v7",
  "event_type": "signal.generated",
  "timestamp": "2024-12-12T10:30:45.123456Z",
  "sequence_number": 123456789,
  "source_service": "strategy-engine-v2",
  "correlation_id": "backtest-run-42",
  "schema_version": "1.2.0",
  "payload": { ... }
}
```

**Kritische Design-Prinzipien:**
- **UUID v7:** Zeit-sortierbar für Ordering
- **Schema-Versionierung:** Ermöglicht Breaking-Changes ohne Downtime
- **Correlation-ID:** Für Distributed Tracing & Replay-Debugging
- **Sequence-Number:** Garantiert Ordering bei µs-gleichen Timestamps

### 3.3 Architektur-Diagramm (Textform)

```
┌─────────────────────────────────────────────────────────┐
│                   External Data Sources                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Binance WS  │  │  CoinGecko   │  │  Twitter API │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
└─────────┼──────────────────┼──────────────────┼──────────┘
          │                  │                  │
          └────────┬─────────┴──────────────────┘
                   ▼
         ┌─────────────────────┐
         │  Market Data Adapter │  (Python Service)
         │  Normalization +     │
         │  Rate-Limiting       │
         └──────────┬──────────┘
                    │ publishes to
                    ▼
     ┌──────────────────────────────────┐
     │   NATS JetStream (Core Backbone) │
     │                                   │
     │  Streams:                         │
     │  • marketdata.*                   │
     │  • signals.*                      │
     │  • orders.*                       │
     │  • fills.*                        │
     │  • risk.*                         │
     │  • psm.*                          │
     │                                   │
     │  Replication: 3-Node Cluster      │
     │  Persistence: File-backed         │
     └──┬───────────┬───────────┬────────┘
        │           │           │
    subscribes  subscribes  subscribes
        │           │           │
        ▼           ▼           ▼
  ┌─────────┐ ┌──────────┐ ┌────────────┐
  │Strategy │ │  Risk    │ │   Order    │
  │ Engine  │ │  Engine  │ │   Router   │
  └────┬────┘ └─────┬────┘ └──────┬─────┘
       │            │             │
       │ publishes  │ publishes   │ publishes
       │ signals.*  │ risk.*      │ orders.*
       │            │             │
       └────────────┴─────────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │   PostgreSQL DB      │ (Event-Store für Compliance)
         │  • events_log (JSONB)│
         │  • projections       │
         │  • snapshots         │
         └──────────────────────┘
                    │
                    │ (optional, für Analytics)
                    ▼
         ┌──────────────────────┐
         │   Kafka (Cold-Path)  │ (Phase 3, optional)
         │  • Long-term Archive │
         │  • ML Feature-Store  │
         └──────────────────────┘
```

### 3.4 CQRS Read-Models

**Projektionen für Query-Performance:**

1. **Current-State-Projections:**
   - `positions_view`: Aktuelle Positionen pro Account
   - `balances_view`: Real-Time Kontostände
   - `orderbook_snapshot`: Aggregierte Order-Book-Zustand

2. **Analytics-Projections:**
   - `pnl_timeseries`: PnL pro Strategy/Symbol/Timeframe
   - `trade_statistics`: Win-Rate, Sharpe-Ratio, Drawdown
   - `risk_metrics`: VAR, Exposure, Correlation

**Update-Mechanismus:**
- Event-Handler hören auf relevante Streams
- Projektionen werden in-memory (Redis) + persistent (PostgreSQL) gehalten
- Bei Node-Restart: Rebuild aus Event-Store oder Snapshot-Wiederherstellung

### 3.5 Replay & Backtesting

**Replay-Modi:**

1. **Full-Replay (Incident-Analyse):**
   - Replay gesamter Event-History ab Timestamp T
   - Debugging von Trading-Anomalien
   - Performance: 100x Real-Time (~10 Tage in 2 Stunden)

2. **Strategy-Backtest (Research):**
   - Replay nur `marketdata.*` + `signals.*`
   - Parallele Ausführung von 10+ Strategien
   - Performance: 1000x Real-Time (1 Jahr in 8 Stunden)

3. **Compliance-Audit:**
   - Replay `orders.*` + `fills.*` + `risk.*`
   - Nachweis korrekter Risk-Controls
   - Performance: 10x Real-Time (für detaillierte Logs)

**Replay-Infrastruktur:**
```python
# Pseudocode: Replay-Engine
class ReplayEngine:
    def replay(start_time, end_time, event_types, speed_factor=1.0):
        events = jetstream.fetch(
            subjects=event_types,
            start_sequence=get_sequence_at(start_time),
            end_sequence=get_sequence_at(end_time)
        )
        
        clock = SimulatedClock(start_time, speed_factor)
        
        for event in events:
            clock.wait_until(event.timestamp)
            dispatch_to_handlers(event)
            
        return get_results()
```

---

## 4. Migrationspfad (18 Monate)

### Phase 1: Redis-Only + PostgreSQL Event-Log (Monate 1-3)

**Ziel:** Minimales Event-Sourcing MVP ohne größere Infrastruktur-Änderungen.

**Implementierung:**
- Behalte Redis Pub/Sub für Real-Time-Messaging
- Füge PostgreSQL-Tabelle `events_log` hinzu:
  ```sql
  CREATE TABLE events_log (
      id BIGSERIAL PRIMARY KEY,
      event_id UUID NOT NULL,
      event_type VARCHAR(100) NOT NULL,
      timestamp TIMESTAMPTZ NOT NULL,
      sequence_number BIGINT NOT NULL,
      payload JSONB NOT NULL,
      source_service VARCHAR(50),
      correlation_id UUID,
      INDEX (event_type, timestamp),
      INDEX (correlation_id)
  );
  ```
- Services publishen Events zu Redis UND loggen zu PostgreSQL (async)
- Snapshots alle 1000 Events für schnelleres Replay

**Deliverables:**
- [ ] Event-Logger-Modul (Python)
- [ ] PostgreSQL-Schema & Indizes
- [ ] Replay-Script (basic) für debugging
- [ ] Monitoring: Event-Log-Latency (<10ms P99)

**Risiken:**
- PostgreSQL kann Bottleneck werden bei >1k events/sec → Batch-Writes nutzen
- Kein Replay in Echtzeit möglich (nur Offline)

### Phase 2: Hybrid-Betrieb mit NATS JetStream (Monate 4-9)

**Ziel:** Schrittweise Migration kritischer Streams zu NATS JetStream.

**Reihenfolge der Migration:**
1. **Monat 4-5:** `marketdata.*` → NATS (Read-Only, kein Risiko)
2. **Monat 6-7:** `signals.*` + `risk.*` → NATS
3. **Monat 8-9:** `orders.*` + `fills.*` → NATS (kritischster Teil!)

**Dual-Write-Phase:**
- Events werden parallel zu Redis UND NATS gepublished
- Subscriber lesen primär von NATS, Fallback auf Redis
- Verifikation: Diff-Tool prüft Konsistenz zwischen Redis/NATS

**Infrastruktur:**
- NATS-Cluster: 3 Nodes (Docker-Compose → später Kubernetes)
- Retention: 7 Tage File-backed (Hot), danach Archive zu S3
- Monitoring: Prometheus + Grafana Dashboards

**Deliverables:**
- [ ] NATS JetStream Setup (Docker/K8s)
- [ ] Migration-Scripts pro Event-Typ
- [ ] Dual-Write-Verification-Tool
- [ ] Latency-Benchmarks: NATS vs. Redis
- [ ] Replay-Engine mit NATS-Backend
- [ ] Runbooks für NATS-Operations

**Risiken:**
- Dual-Write erhöht Komplexität → Klare Rollback-Strategie
- NATS-Cluster-Tuning für optimale Latenz nötig

### Phase 3: Full NATS + optionales Kafka (Monate 10-18)

**Ziel:** Redis Pub/Sub vollständig abgelöst, NATS als primärer Backbone.

**Implementierung:**
- Entferne Redis-Publisher aus allen Services
- Redis bleibt nur für Caching (Projections, Session-State)
- Optional: Kafka als Archive-Layer für Cold-Storage (>30 Tage)
  - NATS → Kafka-Bridge für `orders.*`, `fills.*` (Compliance)
  - Kafka-Retention: Mehrere Jahre, günstiger Storage

**Kafka-Integration (optional):**
```
NATS JetStream (Hot: 7 Tage)
      │
      ├─> NATS-to-Kafka Connector
      │
      ▼
Apache Kafka (Cold: 7 Jahre)
      │
      ├─> Kafka Connect → S3
      └─> Kafka Streams → ML-Pipelines
```

**Infrastructure-as-Code:**
- Terraform/Pulumi für NATS-Cluster (AWS/GCP/Bare-Metal)
- Kubernetes-Operators für Auto-Scaling
- GitOps (ArgoCD/Flux) für Deployments

**Deliverables:**
- [ ] IaC-Templates für Production-Deployment
- [ ] Disaster-Recovery-Playbooks
- [ ] Automated Backtest-Pipelines (CI/CD)
- [ ] Compliance-Reports aus Event-Store
- [ ] Performance-Tuning: <1ms P99 für kritische Paths
- [ ] Team-Training: NATS-Operations

**Risiken:**
- Kafka fügt Komplexität hinzu → Nur wenn Analytics-Use-Case klar
- Betriebskosten steigen → Kosten-Benefit-Analyse

---

## 5. Policy- & Governance-Implikationen für CDB_POLICY_STACK

### 5.1 Event-Schema-Governance

**Policy-Dokument:** `CDB-POL-ES-001: Event Schema Management`

**Anforderungen:**
1. **Schema-Registry:**
   - Alle Event-Schemas müssen in Git-Repository versioniert sein
   - JSON-Schema oder Protobuf-Definitions
   - Breaking-Changes benötigen Review-Prozess

2. **Versionierung:**
   - Semantic Versioning: Major.Minor.Patch
   - Major-Changes: Backward-Incompatible (z.B. Feld gelöscht)
   - Minor-Changes: Backward-Compatible (z.B. Feld hinzugefügt)

3. **Deprecation-Policy:**
   - Mindestens 6 Monate Notice vor Schema-Removal
   - Deprecation-Warnings in Event-Envelope

**Verantwortlichkeiten:**
- Schema-Owner pro Event-Typ (definiert in RACI-Matrix)
- Architecture-Board genehmigt Major-Changes

### 5.2 Event-Retention & Data-Lifecycle

**Policy-Dokument:** `CDB-POL-ES-002: Event Retention & Archival`

**Retention-Regeln:**
| **Event-Typ** | **Hot-Storage (NATS)** | **Cold-Storage (S3/Kafka)** | **Grund** |
|---------------|------------------------|----------------------------|-----------|
| `marketdata.*` | 7 Tage | 1 Jahr | Backtesting |
| `signals.*` | 30 Tage | 5 Jahre | Strategy-Research |
| `orders.*` | 30 Tage | 7 Jahre | MiFID II / Regulatorik |
| `fills.*` | 30 Tage | 7 Jahre | Steuer / Audit |
| `risk.*` | 30 Tage | 1 Jahr | Risk-Reporting |
| `psm.*` | 30 Tage | 1 Jahr | PnL-Analyse |

**Anonymisierung:**
- Nach 1 Jahr: Entferne PII (Personal Identifiable Information) aus Events
- Behalte aggregierte Metriken für Langzeit-Analyse

### 5.3 Replay & Audit-Trail

**Policy-Dokument:** `CDB-POL-ES-003: Event Replay & Audit`

**Anforderungen:**
1. **Audit-Trail:**
   - Jedes Event muss `source_service`, `user_id`, `correlation_id` enthalten
   - Immutability: Events dürfen NIEMALS modifiziert werden
   - Tampering-Detection: Checksummen über Event-Batches

2. **Replay-Rechte:**
   - Nur authorisierte Services dürfen Replay-Operationen starten
   - Replay-Logs werden auditiert (wer, wann, warum)
   - Production-Replays benötigen 4-Augen-Prinzip

3. **Incident-Response:**
   - Bei Trading-Anomalien: Sofortiger Replay für Root-Cause-Analyse
   - Replay-Window: Mindestens 48 Stunden vor Incident
   - Ergebnisse müssen dokumentiert werden (Incident-Report)

### 5.4 Latency & Performance-SLAs

**Policy-Dokument:** `CDB-POL-ES-004: Event-Processing SLAs`

**Service-Level-Objectives:**
| **Path** | **P50 Latency** | **P99 Latency** | **P999 Latency** | **Availability** |
|----------|----------------|----------------|-----------------|------------------|
| MarketData-Ingestion | <0.5ms | <2ms | <10ms | 99.9% |
| Signal-Generation | <1ms | <5ms | <20ms | 99.9% |
| Order-Routing | <1ms | <3ms | <15ms | 99.99% |
| Risk-Checks | <0.5ms | <2ms | <10ms | 99.99% |
| Event-Persistence | <5ms | <10ms | <50ms | 99.9% |

**Monitoring:**
- Real-Time Dashboards (Grafana)
- Alerts bei SLA-Verletzungen (PagerDuty)
- Weekly Performance-Reports

### 5.5 Disaster-Recovery

**Policy-Dokument:** `CDB-POL-ES-005: Disaster Recovery & Backups`

**Backup-Strategie:**
1. **NATS-Snapshots:**
   - Täglich: Full-Backup des gesamten Event-Stores
   - Stündlich: Incremental-Backups
   - Retention: 30 Tage

2. **PostgreSQL-Backups:**
   - Continuous-Archiving (WAL-Shipping)
   - Point-in-Time-Recovery (PITR) bis 30 Tage zurück

3. **Off-Site-Replication:**
   - Event-Store repliziert zu Secondary-Region (AWS Multi-Region)
   - RTO (Recovery-Time-Objective): 15 Minuten
   - RPO (Recovery-Point-Objective): 1 Minute

**Testing:**
- Monatliche DR-Drills
- Annual Full-Failover-Test

### 5.6 Security & Access-Control

**Policy-Dokument:** `CDB-POL-ES-006: Event-Store Security`

**Anforderungen:**
1. **Verschlüsselung:**
   - At-Rest: AES-256 für alle persistierten Events
   - In-Transit: TLS 1.3 für NATS-Kommunikation

2. **Access-Control:**
   - RBAC (Role-Based-Access-Control) für Event-Publish/Subscribe
   - Prinzip der minimalen Rechte (Least-Privilege)
   - Service-Accounts mit Rotation alle 90 Tage

3. **Compliance:**
   - GDPR: Recht auf Vergessenwerden → Event-Anonymisierung
   - MiFID II: Vollständiger Audit-Trail aller Orders

---

## 6. Implementierungs-Checkliste

### 6.1 Phase 1 (Redis + PostgreSQL)
- [ ] PostgreSQL Event-Log-Schema erstellt
- [ ] Event-Logger-Bibliothek implementiert (Python)
- [ ] Batch-Write-Optimierung für PostgreSQL
- [ ] Snapshot-Mechanismus für schnelles Replay
- [ ] Monitoring: Event-Write-Latency
- [ ] Policy-Dokument CDB-POL-ES-001 ratifiziert
- [ ] Team-Training: Event-Sourcing-Basics

### 6.2 Phase 2 (Hybrid NATS)
- [ ] NATS JetStream Cluster (3 Nodes) deployed
- [ ] Migration `marketdata.*` zu NATS
- [ ] Migration `signals.*` + `risk.*` zu NATS
- [ ] Migration `orders.*` + `fills.*` zu NATS
- [ ] Dual-Write-Verification bestanden
- [ ] Latency-Benchmarks dokumentiert
- [ ] Replay-Engine mit NATS-Backend functional
- [ ] Policy-Dokumente CDB-POL-ES-002 bis CDB-POL-ES-004 ratifiziert
- [ ] Runbooks für NATS-Operations erstellt

### 6.3 Phase 3 (Full NATS + Optional Kafka)
- [ ] Redis Pub/Sub vollständig deaktiviert
- [ ] IaC-Templates für Production-Deployment
- [ ] Kafka-Integration (falls entschieden)
- [ ] Disaster-Recovery-Tests erfolgreich
- [ ] Automated-Backtest-Pipeline in CI/CD
- [ ] Compliance-Reports aus Event-Store
- [ ] SLAs für P99-Latencies erreicht (<2ms)
- [ ] Policy-Dokumente CDB-POL-ES-005 und CDB-POL-ES-006 ratifiziert
- [ ] Team vollständig trained auf NATS/Kafka-Operations

---

## 7. Zusammenfassung & Empfehlungen

### Warum NATS JetStream für CDB?
1. **Latenz:** Sub-2ms P99 ermöglicht HFT-Strategien
2. **Einfachheit:** Weniger operationale Komplexität als Kafka
3. **Flexibilität:** Replay by Time/Sequence/Count out-of-the-box
4. **Kosten:** Kein JVM-Overhead, effizient auf kleineren Maschinen

### Wann Kafka zusätzlich?
- Analytics-Pipeline mit >1M events/sec
- Integration mit bestehenden Kafka-Ökosystemen (Kafka Connect)
- Cold-Storage-Anforderungen >1 Jahr (billiger als NATS-Files)

### Kritische Erfolgsfaktoren
1. **Schema-Governance:** Ohne klare Schema-Verwaltung wird Event-Sourcing chaotisch
2. **Monitoring:** Sub-ms-Latencies erfordern hochauflösendes Monitoring (µs-Granularität)
3. **Team-Training:** Event-Sourcing ist paradigmenwechsel – Zeit für Lernen einplanen
4. **Incremental Rollout:** Strangler-Pattern nutzen, um Risiko zu minimieren

### Nächste Schritte (immediate)
1. **Proof-of-Concept:** 2-wöchiger Spike mit NATS JetStream
   - Single-Node Setup
   - Replay-Test mit historischen Market-Data
   - Latency-Benchmark gegen Redis Pub/Sub
2. **Architektur-Review:** Präsentation vor CDB-Team
3. **Policy-Stack-Integration:** CDB-POL-ES-001 als erstes Policy-Dokument
---


