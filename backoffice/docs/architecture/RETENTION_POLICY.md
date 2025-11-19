# Retention-Policy – Claire de Binaire Event Store

**Version**: 1.0
**Status**: ✅ Definiert
**Erstellt**: 2025-11-19
**Basiert auf**: EVENT_SOURCING_RESEARCH.md

---

## Übersicht

Diese Policy definiert, wie lange Events im System gespeichert werden und wann sie archiviert oder gelöscht werden.

**Ziele**:
- ✅ Regulatorische Compliance (MiFID II: 7 Jahre Order-Daten)
- ✅ Performance-Optimierung (Alte MarketData belastet Redis)
- ✅ Kosten-Kontrolle (Storage-Kosten für historische Daten)
- ✅ Audit-Fähigkeit (Replay für Risk-Decisions)

---

## Retention-Tabelle

| Event-Type | Hot Storage (Redis) | Warm Storage (PostgreSQL) | Cold Storage (S3) | Deletion | Grund |
|-----------|---------------------|---------------------------|-------------------|----------|-------|
| **ClockEvent** | 1 Tag | - | - | Nach 1 Tag | Nur Debugging |
| **MarketData** | 7 Tage | 30 Tage | - | Nach 30 Tagen | Hohe Frequenz |
| **Signal** | 30 Tage | 90 Tage | 7 Jahre | Nach 7 Jahren | Backtests |
| **RiskDecision** | 90 Tage | 7 Jahre | Permanent | Niemals | Audit (Regulatorik) |
| **Order** | 90 Tage | 7 Jahre | Permanent | Niemals | MiFID II Compliance |
| **OrderResult** | 90 Tage | 7 Jahre | Permanent | Niemals | MiFID II Compliance |
| **Alert** | 30 Tage | 90 Tage | - | Nach 90 Tagen | Monitoring |

---

## Storage-Layers

### 1. Hot Storage (Redis)
**Zweck**: Schneller Zugriff für laufende Operationen
**Technologie**: Redis (In-Memory)
**Retention**: 1-90 Tage (je nach Event-Type)
**Performance**: <1ms Latency

**Verwendung**:
- Signal Engine liest MarketData der letzten 7 Tage
- Risk Manager liest Signals der letzten 30 Tage
- Execution Service liest Orders der letzten 90 Tage

**Eviction-Policy**:
```bash
# Redis Config (docker-compose.yml)
REDIS_MAXMEMORY=2gb
REDIS_MAXMEMORY_POLICY=allkeys-lru  # Least Recently Used
```

### 2. Warm Storage (PostgreSQL)
**Zweck**: Mittelfristige Speicherung für Analytics
**Technologie**: PostgreSQL
**Retention**: 30 Tage - 7 Jahre (je nach Event-Type)
**Performance**: 10-50ms Latency

**Verwendung**:
- Backtests über 90 Tage Signals
- Risk-Audits über 7 Jahre RiskDecisions
- Regulatorische Anfragen (Orders/OrderResults)

**Tabellen**:
```sql
-- Events-Tabelle (Generic Event Store)
CREATE TABLE events (
    event_id UUID PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    timestamp BIGINT NOT NULL,
    version VARCHAR(10) NOT NULL,
    source VARCHAR(50) NOT NULL,
    sequence_id BIGINT,
    correlation_id UUID,
    causation_id UUID,
    payload JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_event_type (event_type),
    INDEX idx_timestamp (timestamp),
    INDEX idx_correlation_id (correlation_id)
);

-- Partitionierung nach Monat (für Performance)
CREATE TABLE events_2025_01 PARTITION OF events
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
```

### 3. Cold Storage (S3 / Archive)
**Zweck**: Langfristige Archivierung (7+ Jahre)
**Technologie**: AWS S3 Glacier / Azure Archive Storage
**Retention**: Permanent (für regulatorische Events)
**Performance**: Stunden bis Tage (Retrieval)

**Verwendung**:
- Langfristige Compliance (Orders/OrderResults >7 Jahre)
- Historische Backtests (Signals >90 Tage)
- Disaster Recovery (Full Event Log)

**Format**:
```
s3://claire-de-binaire-events/
  └── year=2025/
      └── month=01/
          └── day=15/
              ├── market_data.parquet.gz
              ├── signals.parquet.gz
              ├── orders.parquet.gz
              └── order_results.parquet.gz
```

---

## Archivierungs-Strategie

### Automatische Archivierung (Cron Jobs)

**Daily Job** (täglich um 02:00 UTC):
```bash
# 1. ClockEvents älter als 1 Tag löschen
DELETE FROM events
WHERE event_type = 'clock'
AND timestamp < (EXTRACT(EPOCH FROM NOW() - INTERVAL '1 day') * 1000);

# 2. MarketData älter als 7 Tage aus Redis löschen
REDIS: DEL market_data:<keys_older_than_7_days>
```

**Weekly Job** (sonntags um 03:00 UTC):
```bash
# 1. MarketData älter als 30 Tage aus PostgreSQL löschen
DELETE FROM events
WHERE event_type = 'market_data'
AND timestamp < (EXTRACT(EPOCH FROM NOW() - INTERVAL '30 days') * 1000);

# 2. Signals älter als 90 Tage archivieren (PostgreSQL → S3)
pg_dump events WHERE event_type = 'signal' AND timestamp < ... | gzip > s3://...
DELETE FROM events WHERE event_type = 'signal' AND timestamp < ...;
```

**Monthly Job** (1. des Monats um 04:00 UTC):
```bash
# 1. Orders/OrderResults älter als 1 Jahr archivieren (PostgreSQL → S3)
pg_dump events WHERE event_type IN ('order', 'order_result') AND timestamp < ... | gzip > s3://...
DELETE FROM events WHERE event_type IN ('order', 'order_result') AND timestamp < ...;

# 2. Alerts älter als 90 Tage löschen
DELETE FROM events WHERE event_type = 'alert' AND timestamp < ...;
```

---

## Regulatorische Anforderungen

### MiFID II (EU-Richtlinie für Wertpapierfirmen)
**Retention**: 7 Jahre für Order-Daten
**Betroffene Events**: `order`, `order_result`, `risk_decision`

**Compliance-Kriterien**:
- ✅ Vollständige Order-Historie (alle Orders & Fills)
- ✅ Audit-Trail (RiskDecisions für jeden Order)
- ✅ Tamper-Proof (Append-Only Event Store)
- ✅ Retrieval-Fähigkeit (innerhalb von 5 Werktagen)

### Interne Audit-Anforderungen
**Retention**: 7 Jahre für Risk-Decisions
**Betroffene Events**: `risk_decision`

**Zweck**:
- Post-Mortem-Analyse bei Verlusten
- Replay von Risk-Blockierungen
- Optimierung der Risk-Engine

---

## Performance-Optimierung

### Partitionierung (PostgreSQL)
**Strategie**: Time-Based Partitioning (pro Monat)

**Vorteile**:
- ✅ Schnellere Queries (nur relevante Partitionen)
- ✅ Einfaches Archivieren (ganze Partition exportieren)
- ✅ Bessere Index-Performance

**Implementierung**:
```sql
-- Partitionen automatisch erstellen (pg_partman Extension)
CREATE TABLE events (
    ...
) PARTITION BY RANGE (timestamp);

-- Automatisches Cleanup alter Partitionen
SELECT partman.drop_partition_time('events', '30 days', 'market_data');
```

### Indexierung
**Wichtige Indices**:
```sql
-- Event-Type Queries (häufigste Query)
CREATE INDEX idx_event_type ON events (event_type);

-- Time-Range Queries (Backtests)
CREATE INDEX idx_timestamp ON events (timestamp);

-- End-to-End Tracing
CREATE INDEX idx_correlation_id ON events (correlation_id);

-- Compound Index für häufige Kombination
CREATE INDEX idx_type_timestamp ON events (event_type, timestamp);
```

---

## Monitoring & Alerts

### Storage-Metriken
**Überwachen**:
- Redis-Speicher-Auslastung (Warnung bei >80%)
- PostgreSQL-Tabellengröße (Alert bei >100GB)
- S3-Kosten (Budget-Alerts)

**Dashboards** (Grafana):
```yaml
Panels:
  - Event-Count pro Type (letzte 24h)
  - Event-Count pro Storage-Layer
  - Storage-Größe Trend (7 Tage)
  - Archivierungs-Job Status
```

### Retention-Compliance Checks
**Wöchentlicher Check**:
```sql
-- Prüfen: Sind Orders älter als 7 Jahre noch da?
SELECT COUNT(*)
FROM events
WHERE event_type = 'order'
AND timestamp < (EXTRACT(EPOCH FROM NOW() - INTERVAL '7 years') * 1000);

-- Sollte 0 sein (alle archiviert)
```

---

## Disaster Recovery

### Backup-Strategie
**Hot Storage (Redis)**:
- RDB Snapshots (täglich)
- AOF (Append-Only File) für Point-in-Time Recovery

**Warm Storage (PostgreSQL)**:
- Daily Full Backups (pg_basebackup)
- Continuous Archiving (WAL Shipping)
- Retention: 30 Tage

**Cold Storage (S3)**:
- Versioned Buckets (S3 Versioning aktiviert)
- Cross-Region Replication (S3 CRR)
- Glacier Deep Archive für >7 Jahre alte Daten

### Recovery Time Objectives (RTO)
| Layer | RTO | Grund |
|-------|-----|-------|
| Redis (Hot) | 5 Minuten | Kritisch für Live-Trading |
| PostgreSQL (Warm) | 1 Stunde | Analytics kann warten |
| S3 (Cold) | 5 Werktage | Regulatorische Anfragen |

---

## Testing

### Archivierungs-Tests
```python
@pytest.mark.integration
def test_archive_old_market_data():
    """Test: MarketData älter als 30 Tage wird archiviert"""
    # Erstelle alte Events
    old_event = MarketData(timestamp=30_days_ago)
    db.save(old_event)

    # Archivierungs-Job ausführen
    archive_job.run()

    # Assert: Event nicht mehr in DB
    assert db.get(old_event.event_id) is None

    # Assert: Event in S3
    assert s3.exists(f"market_data/{old_event.event_id}")
```

---

## Migration-Plan (v1 → v2)

**Phase 1** (Woche 1-2):
- [ ] PostgreSQL events-Tabelle erstellen
- [ ] Redis Retention-Policy konfigurieren
- [ ] Archivierungs-Jobs implementieren

**Phase 2** (Woche 3-4):
- [ ] Historische Events migrieren (v1 → v2 Schema)
- [ ] S3 Buckets konfigurieren
- [ ] Monitoring & Dashboards aufsetzen

**Phase 3** (Woche 5-6):
- [ ] Compliance-Tests durchführen
- [ ] Disaster Recovery testen
- [ ] Dokumentation finalisieren

---

## Offene Fragen

1. **S3 vs. Azure Blob Storage**: Welcher Cloud-Provider?
2. **Partitionierungs-Intervall**: Monat vs. Woche für hohe Volumen?
3. **Compression**: gzip vs. zstd für Cold Storage?
4. **Retrieval-SLA**: 5 Werktage zu lang für Regulatorik?

---

**Version**: 1.0
**Autor**: Claire de Binaire Team
**Review**: TBD
**Approval**: TBD
