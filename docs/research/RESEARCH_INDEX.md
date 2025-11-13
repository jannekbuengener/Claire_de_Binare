# Research Documentation Index – Knowledge Base

**Version**: 1.2.0
**Status**: ✅ **COMPLETE** (10/10 Dokumente)
**Zweck**: Zentrale Übersicht aller technischen Deep-Dive-Dokumente für Agenten

---

## 📋 Übersicht

Die Research-Dokumentation ist das **Hauptwissens-Nachschlagewerk** für alle Agenten, die am Claire de Binaire Trading System arbeiten. Jedes Dokument folgt einer standardisierten Struktur und enthält Production-Ready-Beispiele.

**Gesamtumfang**: ~5.500 Zeilen technische Dokumentation
**Erstellungszeitraum**: 2025-01-11 bis 2025-10-30
**Wartung**: Kontinuierlich aktualisiert bei Architektur-Änderungen

---

## 🗂️ Dokumenten-Übersicht

### **Infrastruktur & Kommunikation** (4 Dokumente)

| # | Dokument | Zweck | Zeilen | Status | Letzte Aktualisierung |
|---|----------|-------|--------|--------|-----------------------|
| 1 | `cdb_ws.md` | WebSocket Integration (MEXC Market Data) | 450 | ✅ | 2025-01-11 |
| 2 | `cdb_redis.md` | Redis Pub/Sub & Event-Bus | 380 | ✅ | 2025-01-11 |
| 3 | `cdb_postgres.md` | PostgreSQL Schema V1.1 & Performance | 850 | ✅ | 2025-10-30 |
| 4 | `cdb_prometheus.md` | Prometheus Metrics & Monitoring | 420 | ✅ | 2025-01-11 |

---

### **Core Services** (4 Dokumente)

| # | Dokument | Zweck | Zeilen | Status | Letzte Aktualisierung |
|---|----------|-------|--------|--------|-----------------------|
| 5 | `cdb_signal.md` | Signal Engine Logic & Thresholds | 520 | ✅ | 2025-01-11 |
| 6 | `cdb_risk.md` | Risk Manager (5-Layer Checks, Bug Fixes) | 500 | ✅ | 2025-10-30 |
| 7 | `cdb_execution.md` | MEXC API Integration & Order Execution | 650 | ✅ | 2025-10-30 |
| 8 | `cdb_advisor.md` | ML Advisor Concept (Post-MVP) | 380 | ✅ | 2025-01-11 |

---

### **Deployment & Monitoring** (2 Dokumente)

| # | Dokument | Zweck | Zeilen | Status | Letzte Aktualisierung |
|---|----------|-------|--------|--------|-----------------------|
| 9 | `cdb_kubernetes.md` | K8s Migration Plan (Phase 8+) | 620 | ✅ | 2025-01-11 |
| 10 | `GRAFANA_DASHBOARD_GUIDE.md` | Dashboard-Interpretation für Phase 7 | 550 | ✅ | 2025-10-30 |

---

## 🔍 Quick Reference – Wann welches Dokument?

### **Ich arbeite an...**

#### **WebSocket-Feed-Problemen** → `cdb_ws.md`
- Reconnect-Logic verstehen
- Error-Handling-Strategien
- Rate-Limiting-Implementierung
- Heartbeat-Monitoring

#### **Signal-Generierung** → `cdb_signal.md`
- Threshold-Berechnung (0.5% - 2.5%)
- Confidence-Score-Algorithmus
- Redis-Publishing-Flow
- Multi-Symbol-Support

#### **Risk-Checks oder Position-Limits** → `cdb_risk.md`
- 5-Layer Risk-Check-Hierarchie
- Circuit-Breaker-Implementierung
- P&L-Berechnung (Realized + Unrealized)
- 4 kritische Bug-Fixes (P0)

#### **Order-Execution oder MEXC-API** → `cdb_execution.md`
- HMAC-SHA256 Signature-Generierung
- Order-Types (MARKET, LIMIT, STOP_LOSS_LIMIT)
- Error-Code-Handling (-1003, -2010, etc.)
- Test-Mode vs Live-Mode

#### **Database-Queries oder Schema-Änderungen** → `cdb_postgres.md`
- PostgreSQL Schema V1.1 (4 Core-Tabellen)
- Performance-Optimierungen (37-45x schneller)
- CHECK Constraints & Trigger
- Migration V1.0 → V1.1

#### **Redis Pub/Sub oder Event-Flow** → `cdb_redis.md`
- Channel-Struktur (market_data, signals, orders, order_results)
- Event-Schema (JSON-Format)
- Connection-Pool-Management
- Debugging mit redis-cli

#### **Monitoring oder Metrics** → `cdb_prometheus.md`
- Prometheus-Exporter-Implementierung
- Metrics-Typen (Counter, Gauge, Histogram)
- Grafana-Integration
- Alert-Rules

#### **Dashboard-Interpretation oder Troubleshooting** → `GRAFANA_DASHBOARD_GUIDE.md`
- Panel-Interpretation (15+ Panels)
- Threshold-Tabelle (Normal/Warning/Critical)
- 3 Troubleshooting-Szenarien
- Täglicher Check-Workflow (Phase 7)

#### **Kubernetes-Deployment planen** → `cdb_kubernetes.md`
- K8s-Migration-Roadmap (3 Sprints)
- Helm-Charts-Struktur
- Service-Mesh-Integration
- Auto-Scaling-Policies

#### **ML-Advisor-Konzept verstehen** → `cdb_advisor.md`
- Reinforcement-Learning-Architektur
- Feature-Engineering (20+ Features)
- Training-Pipeline
- Post-MVP-Roadmap

---

## 📊 Dokumenten-Statistiken

### **Zeilen pro Kategorie**:
```
Infrastruktur & Kommunikation:  2.100 Zeilen (38%)
Core Services:                  2.050 Zeilen (37%)
Deployment & Monitoring:        1.170 Zeilen (21%)
## Sonstiges (Wishlist, Index):     230 Zeilen (4%)

TOTAL:                          ~5.550 Zeilen
```

### **Erstellungs-Timeline**:
```
2025-01-11: 6 Dokumente erstellt (cdb_ws, cdb_redis, cdb_prometheus, cdb_signal, cdb_advisor, cdb_kubernetes)
            → 2.770 Zeilen, Grundlagen-Research abgeschlossen

2025-01-11: 2 Meta-Dokumente (KNOWLEDGE_BASE_INTEGRATION, DEEP_RESEARCH_WISHLIST)
            → 1.150 Zeilen, Wissenslücken identifiziert

2025-10-30: 4 Dokumente erstellt (cdb_risk, cdb_execution, GRAFANA_DASHBOARD_GUIDE, cdb_postgres)
            → 2.550 Zeilen, alle kritischen Lücken geschlossen

2025-10-30: Index & Statusupdate (RESEARCH_INDEX.md, DEEP_RESEARCH_WISHLIST.md)
            → 80 Zeilen, Dokumentation finalisiert
```

---

## 🎯 Nutzungsrichtlinien für Agenten

### **Beim Starten einer neuen Session**:
1. Lies `PROJECT_STATUS.md` → Aktuelle Phase & Ziele
2. Lies `RESEARCH_INDEX.md` (dieses Dokument) → Verfügbare Ressourcen
3. Identifiziere relevante Research-Docs für deine Aufgabe
4. Nutze Quick Reference oben für schnellen Zugriff

### **Beim Debuggen von Problemen**:
1. Identifiziere betroffenen Service (signal_engine, risk_manager, execution_service)
2. Lies entsprechendes Research-Doc (cdb_signal, cdb_risk, cdb_execution)
3. Prüfe Troubleshooting-Section im Dokument
4. Nutze `GRAFANA_DASHBOARD_GUIDE.md` für Monitoring-Kontext

### **Beim Implementieren neuer Features**:
1. Prüfe `ARCHITEKTUR.md` → Passt Feature in bestehende Architektur?
2. Lies relevante Research-Docs → Best Practices & Patterns
3. Prüfe `EVENT_SCHEMA.json` → Event-Format korrekt?
4. Dokumentiere Änderungen in `DECISION_LOG.md`

---

## 📝 Wartung & Updates

### **Wann muss ein Dokument aktualisiert werden?**

| Trigger | Betroffene Dokumente | Beispiel |
|---------|---------------------|----------|
| **Service-Code geändert** | Entsprechendes Research-Doc | `risk_manager.py` geändert → `cdb_risk.md` updaten |
| **DB-Schema geändert** | `cdb_postgres.md` | Neue Tabelle `alerts` → Schema-Section updaten |
| **API-Endpoint geändert** | Service-spezifisches Doc | `/health` → `/status` rename → alle Docs updaten |
| **Neue Metrik hinzugefügt** | `cdb_prometheus.md`, `GRAFANA_DASHBOARD_GUIDE.md` | `circuit_breaker_resets_total` → beide Docs updaten |
| **Deployment-Änderung** | `cdb_kubernetes.md` | Neue Ingress-Rule → K8s-Doc updaten |

### **Update-Prozess**:
1. Öffne betroffenes Research-Doc
2. Suche relevante Section (Ctrl+F)
3. Update Inhalt + Code-Beispiele
4. Update "Änderungsprotokoll" am Ende des Dokuments
5. Update "Letzte Aktualisierung" in diesem Index

---

## 🔗 Verwandte Dokumente

### **Außerhalb von `/research`**:

| Dokument | Pfad | Zweck |
|----------|------|-------|
| PROJECT_STATUS.md | `backoffice/PROJECT_STATUS.md` | Aktuelle Phase, Ziele, Blocker |
| ARCHITEKTUR.md | `backoffice/docs/ARCHITEKTUR.md` | System-Architektur-Übersicht |
| DEVELOPMENT.md | `backoffice/docs/DEVELOPMENT.md` | Coding-Standards & Styleguide |
| EVENT_SCHEMA.json | `backoffice/docs/EVENT_SCHEMA.json` | Event-Payload-Definitionen |
| DECISION_LOG.md | `backoffice/docs/DECISION_LOG.md` | Architektur-Entscheidungen (historisch) |
| SERVICE_TEMPLATE.md | `backoffice/docs/SERVICE_TEMPLATE.md` | Template für neue Services |

---

## 🎉 Completion-Status

**Stand 2025-10-30 20:30 UTC**:
- ✅ Alle 10 geplanten Research-Dokumente erstellt
- ✅ DEEP_RESEARCH_WISHLIST.md auf "COMPLETED" aktualisiert
- ✅ RESEARCH_INDEX.md (dieses Dokument) erstellt
- ✅ Knowledge Base vollständig für Phase 7 (Paper Trading)
- ✅ **2025-10-30_RECOVERY_REPORT.md erstellt** (Container Infrastructure Stabilisierung) ⭐

**Phase 6.7 Recovery (NEU)**:
- 📄 **Dokument**: `../../audits/2025-10-30_RECOVERY_REPORT.md` (850+ Zeilen)
- 🚨 **Problem gelöst**: 3 Python Services Restart-Loops (90min Downtime)
- 🔧 **Root Cause**: Doppelte Compose-Configs (compose.yaml + docker-compose.yml)
- ✅ **Recovery**: <2 Minuten nach compose.yaml Removal
- 🎓 **5 Lessons Learned**: Docker Compose Precedence, Network Syntax, env_file, Health Checks, Troubleshooting
- 📋 **Related ADR**: ADR-005 (compose.yaml Removal) in DECISION_LOG.md

**Nächste Schritte**:
- [ ] Risk Manager Bug-Fixes (4 P0 Bugs aus cdb_risk.md)
- [ ] 7-Day Paper Trading Test (Phase 7)
- [ ] Kontinuierliche Wartung bei Code-Änderungen
- [ ] Feedback-Loop: Agenten berichten fehlende Infos → Docs updaten
- [ ] Post-MVP: Erweitern um `cdb_portfolio.md` (Portfolio-Optimierung)

---

**Ende des Dokuments** | **Letzte Aktualisierung**: 2025-10-30 20:30 UTC | **Version**: 1.3.0 | **Maintainer**: Copilot Agents
