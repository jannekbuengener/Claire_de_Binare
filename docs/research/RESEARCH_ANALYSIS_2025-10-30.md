# Research-Dokumentation - Analyse & Integration

**Datum**: 2025-10-30
**Status**: ✅ Vollständig analysiert
**Quelle**: Externe Research-Dokumente (Desktop > Docker Server)

---

## 📋 Übersicht der analysierten Dokumente

Folgende Research-Dokumente wurden ins Repository integriert (`backoffice/docs/research/`):

1. **cdb_kubernetes.md** (595 Zeilen) - Kubernetes-Migration-Guide
2. **cdb_advisor.md** (448 Zeilen) - ML-basierter Signal-Advisor Konzept
3. **cdb_prometheus.md** (258 Zeilen) - Prometheus/Grafana Monitoring-Integration
4. **cdb_redis.md** - Redis/Docker-Deployment-Dokumentation
5. **cdb_signal.md** - Signal-Engine technische Dokumentation
6. **cdb_ws.md** - WebSocket-Screener Dokumentation

---

## 🔍 Neue Erkenntnisse & Wichtige Findings

### 1. **Kubernetes-Migration (Phase 8+)**

**Status**: Geplant, nicht urgent

**Kernerkenntnisse**:
- Claire de Binaire hat **9 Container** production-ready (bestätigt durch cdb_kubernetes.md)
- Docker Desktop Kubernetes als lokale Test-Umgebung vorgesehen
- Migration via **Kompose** (Docker Compose → Kubernetes YAML) geplant
- **Service-Dependencies**: WebSocket → Redis → Signal Engine → Risk Manager → Execution

**Wichtige Anforderungen**:
- Persistent Volumes für Postgres, Redis, Grafana, Prometheus
- Service Discovery via DNS (Kubernetes Services)
- Health Probes für alle Container (Readiness + Liveness)
- Secrets Management (REDIS_PASSWORD, POSTGRES_PASSWORD, MEXC_API_KEY)

**Empfehlung**:
- ⚠️ **Nicht vor Phase 7 (Paper-Trading) abgeschlossen** starten
- Docker Compose Setup bleibt primär für MVP
- Kubernetes als **Skalierungs-Option** für Multi-Instance-Deployment

---

### 2. **ML-basierter Signal-Advisor (Phase 9+)**

**Status**: Research-Phase, **hochkomplex**

**Kernkonzept**:
- Parallel zur deterministischen Signal-Engine laufen
- **Shadow Mode**: ML-Signale werden geloggt, aber nicht ausgeführt
- Ziel: Konfidenz-Erhöhung durch Mustererkennung
- **Explainability**: SHAP-Werte für jedes Signal (Nachvollziehbarkeit)

**Modell-Optionen** (aus cdb_advisor.md):

| Modell | Latenz | Erklärbarkeit | Einsatz |
|--------|--------|---------------|---------|
| XGBoost | **< 10ms** | ✅ Hoch (SHAP) | Favorit für Echtzeit |
| LSTM | Mittel | Mittel (IG) | Sequenzmodelle |
| TCN | Mittel | Mittel | Experimental |
| Transformer | Hoch | Niedrig | Zu komplex |

**Risk-Governance**:
- ML-Signale **müssen** durch Risk-Manager Filter
- **Confidence Gating**: Nur Signale > 0.7 Confidence
- **Outlier Detection**: Unrealistische Input-Daten blockieren
- **Four-Eyes-Prinzip**: ML + Regel-Engine müssen übereinstimmen (optional)

**Kritische Fragen**:
1. ❓ Wie weit darf ML gehen? (Unterstützer vs. autonome Signale)
2. ❓ Wie schützt man Risk-Layer vor ML-Ausreißern?
3. ❓ Hardware-Anforderungen (GPU ja/nein)?
4. ❓ Re-Training-Frequenz (täglich, wöchentlich)?

**Empfehlung**:
- 🔴 **NICHT vor Phase 10** implementieren
- Benötigt: 6-12 Monate Research + Testing
- Deliverables: 20-25 Seiten Forschungsbericht, Go/No-Go Entscheidung
- **Risiko**: Determinismus könnte kompromittiert werden

---

### 3. **Prometheus/Grafana Monitoring (Phase 7)**

**Status**: Teilweise implementiert, **refinement nötig**

**Aktuelle Situation**:
- Prometheus + Grafana Container **laufen bereits** (cdb_prometheus, cdb_grafana)
- `/metrics` Endpoints in Signal-Engine + Risk-Manager **vorhanden**
- Grafana Dashboard **existiert** (CLAIRE_DE_BINARE_DASHBOARD.json)

**Gaps identifiziert**:
1. ⚠️ Scraping-Konfiguration unvollständig (prometheus.yml)
2. ⚠️ Custom Metriken fehlen (z.B. `signals_generated_total`, `orders_rejected_total`)
3. ⚠️ Alert-Rules nicht definiert (z.B. bei Circuit-Breaker-Aktivierung)

**Forschungsfragen** (aus cdb_prometheus.md):
- **Q1**: Welche Metriken sind relevant? (CPU, Latenz, Event-Raten, Fehler)
- **Q2**: Beeinflusst Monitoring die Performance? (< 5% Overhead erwartet)
- **Q3**: Ist Monitoring deterministisch & sicher? (READ-ONLY, keine Secrets in /metrics)

**Empfehlung**:
- ✅ **Sofort umsetzbar** (Container laufen bereits)
- Nächster Schritt: `prometheus.yml` erweitern mit allen Service-Targets
- Custom Metriken hinzufügen (siehe Phase 7.1 in PROJECT_STATUS.md)

---

### 4. **Service-Dokumentation Alignment**

**Erkenntnisse aus cdb_signal.md, cdb_ws.md, cdb_redis.md**:

Diese Dokumente sind **redundant** zu existierenden READMEs:
- `cdb_signal.md` → bereits in `backoffice/services/signal_engine/README.md`
- `cdb_ws.md` → Screener-Dokumentation fehlt in Repo (⚠️ Gap)
- `cdb_redis.md` → Deployment-Dokumentation (teilweise im Runbook `../ops/RUNBOOK_DOCKER_OPERATIONS.md`)

**Neue Details**:
- WebSocket-Screener **limitiert auf 200 Symbole** pro Verbindung (MEXC-Limit)
- Signal-Engine nutzt **Momentum-Strategie** (3% Schwelle, 15min Intervall)
- Redis läuft mit **AppendOnly Log** (AOF Persistenz)

**Empfehlung**:
- Screener-README erstellen: `backoffice/services/screener/README.md`
- Redundante Inhalte entfernen, nur neue Erkenntnisse integrieren

---

## 🎯 Handlungsempfehlungen (Priorisierung)

### Sofort (Phase 7 - Laufend)

1. **Prometheus Scraping optimieren**
   - `prometheus.yml` erweitern: Alle Service-Targets hinzufügen
   - Custom Metriken in Services hinzufügen
   - Alert-Rules definieren

2. **Screener-Dokumentation erstellen**
   - WebSocket-Screener README schreiben
   - REST-Screener README schreiben

### Mittelfristig (Phase 8)

3. **Kubernetes-Vorbereitung**
   - Kompose-Test durchführen (docker-compose.yml → K8s YAML)
   - PV/PVC-Konzept für Persistenz erarbeiten
   - Secrets Management testen

### Langfristig (Phase 9+)

4. **ML-Advisor Research**
   - Forschungsprojekt initiieren (6-12 Monate)
   - Backtest-Daten sammeln (min. 6 Monate historische Daten)
   - XGBoost-Prototyp in Shadow Mode testen

---

## 📊 Neue Metriken für Monitoring

Basierend auf cdb_prometheus.md sollten folgende Metriken hinzugefügt werden:

**Signal-Engine**:
```python
signals_generated_total = Counter('signals_generated_total', 'Total signals generated', ['symbol', 'side'])
signals_rejected_total = Counter('signals_rejected_total', 'Total signals rejected', ['reason'])
signal_confidence_avg = Gauge('signal_confidence_avg', 'Average signal confidence', ['symbol'])
signal_processing_latency_ms = Histogram('signal_processing_latency_ms', 'Signal processing time')
```

**Risk-Manager**:
```python
orders_validated_total = Counter('orders_validated_total', 'Total orders validated', ['symbol'])
orders_rejected_total = Counter('orders_rejected_total', 'Total orders rejected', ['reason'])
circuit_breaker_triggers = Counter('circuit_breaker_triggers', 'Circuit breaker activations')
exposure_current = Gauge('exposure_current', 'Current exposure', ['symbol'])
```

**Execution-Service**:
```python
trades_executed_total = Counter('trades_executed_total', 'Total trades executed', ['symbol', 'side'])
trades_failed_total = Counter('trades_failed_total', 'Total failed trades', ['reason'])
execution_latency_ms = Histogram('execution_latency_ms', 'Order execution time')
```

---

## 🔐 Security-Findings

**Aus cdb_redis.md + cdb_kubernetes.md**:

1. ✅ Redis läuft mit Passwort-Authentifizierung (REDIS_PASSWORD)
2. ✅ Postgres verwendet Non-Root-User (cdb_user)
3. ✅ Secrets via ENV-Variablen (nicht hardcoded)
4. ⚠️ `/metrics` Endpoints exponieren keine sensiblen Daten (zu verifizieren)
5. ⚠️ Kubernetes Secrets Management fehlt (bei Migration relevant)

**Empfehlung**:
- Security-Audit für `/metrics` Endpoints durchführen
- Kubernetes Secrets vorbereiten (verschlüsselte ConfigMaps)

---

## 📚 Neue Referenzen

**Externe Tools/Frameworks erwähnt**:
- **Freqtrade/FreqAI**: ML-Integration in Trading-Bot (Referenz für Feature Engineering)
- **Kompose**: Docker Compose → Kubernetes Converter
- **SHAP**: Explainability für ML-Modelle (XGBoost, LSTM)
- **Prometheus Flask Exporter**: Auto-Instrumentierung für Flask

**Literatur-Hinweise**:
- Robust Perception: Prometheus Client Memory Usage (konstant, < 5% Overhead)
- Better Stack: Prometheus Python Metrics Integration Guide
- Kubernetes Pod Security Standards

---

## ✅ Status Summary

**Integration abgeschlossen**: ✅ Alle Dokumente in `backoffice/docs/research/` kopiert

**Neue Erkenntnisse**:
- ✅ Kubernetes-Migration geplant (Phase 8+)
- ✅ ML-Advisor Konzept detailliert (Phase 9+, hochkomplex)
- ✅ Prometheus Monitoring teilweise aktiv (Refinement nötig)
- ✅ Service-Details vervollständigt (Screener, Redis, Signal-Engine)

**Nächste Schritte**:
1. Prometheus-Metriken erweitern (sofort)
2. Screener-READMEs erstellen (kurzfristig)
3. Kubernetes-Test vorbereiten (mittelfristig)
4. ML-Advisor Research-Projekt initiieren (langfristig, nach Phase 7)

---

**Maintainer**: Claire de Binaire Research Team
**Last Update**: 2025-10-30 11:15 UTC
