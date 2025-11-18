# Konflikt-Dokumentation - Pipeline 2

**Analyst**: agata-van-data
**Datum**: 2025-11-14
**Scope**: Cross-Reference zwischen ARCHITEKTUR.md, Risikomanagement-Logik.md, docker-compose.yml, copilot-instructions.md

---

## 1. Validierte Konflikte (aus Hypothesen)

### ✅ Konflikt 1: Service-Namens-Dualität

**Status**: BESTÄTIGT

**Quellen**:
- docker-compose.yml: Container-Name `cdb_core` (Zeile 166-196)
- ARCHITEKTUR.md: Service als "Signal Engine" bezeichnet (Tabelle Abschnitt 3)
- docker-compose.yml: Aliasing `signal_engine` im Network (Zeile 195-196)

**Konflikt**: Inkonsistente Benennung - Container heißt `cdb_core`, aber DNS-Alias und Dokumentation verwenden `signal_engine`.

**Auswirkung**: Verwirrung beim Debugging (`docker ps` zeigt `cdb_core`, Logs referenzieren `signal_engine`).

**Empfehlung**: Entweder Container umbenennen zu `cdb_signal_engine` ODER Dokumentation durchgehend `cdb_core` verwenden.

---

### ✅ Konflikt 2: ENV-Präfix-Inkonsistenz

**Status**: BESTÄTIGT

**Quellen**:
- copilot-instructions.md: Empfehlung "Einheitliches Präfix `CDB_` für alle projekt-spezifischen Variablen" (DevOps-Anmerkungen, Zeile 39)
- Risikomanagement-Logik.md + extracted_knowledge.md: Alle ENV-Variablen OHNE Präfix (`MAX_POSITION_PCT`, `REDIS_PASSWORD`, etc.)

**Konflikt**: Empfehlung in copilot-instructions.md wird nirgends umgesetzt.

**Auswirkung**: Potenzielle Kollision mit System-ENV oder anderen Tools.

**Empfehlung**: ADR erstellen - entweder Migration zu `CDB_*` mit Breaking Change ODER Empfehlung als "nice-to-have" markieren, aber nicht verpflichtend.

---

### ❌ Konflikt 3: Prometheus-Port (FALSIFIZIERT)

**Status**: KEIN KONFLIKT

**Ursprüngliche Hypothese**: ARCHITEKTUR.md zeigt 19090, aber docker-compose.yml zeigt 9090.

**Realität**:
- docker-compose.yml Zeile 58: `ports: - "19090:9090"` (Host:Container Mapping)
- ARCHITEKTUR.md: "Prometheus Port 19090 gemappt auf Container-Port 9090 (Standard-Prometheus-Port)"

**Ergebnis**: Korrekt dokumentiert, kein Konflikt. Beide Quellen stimmen überein.

---

### 🔍 Konflikt 4: Risk-Parameter Defaults (TEILWEISE)

**Status**: MINOR - Dokumentations-Lücke

**Quellen**:
- Risikomanagement-Logik.md Zeile 58-61: Defaults angegeben (`MAX_POSITION_PCT` = 0.10, etc.)
- docker-compose.yml, .env: Keine expliziten Defaults sichtbar (Datei nicht committed)

**Konflikt**: Defaults in Doku, aber unklar, ob Code diese Defaults nutzt oder ENV-Variablen zwingend erforderlich sind.

**Validierung benötigt**: Prüfe `config.py` in Services - laden sie Defaults oder crashen sie bei fehlenden Werten?

**Empfehlung**: Explizit in `extracted_knowledge.md` Abschnitt 5.2 dokumentieren: "Defaults dienen als Referenz, Service crasht bei fehlenden Variablen" (bereits so dokumentiert, OK).

---

## 2. Neu identifizierte Konflikte

### 🆕 Konflikt 5: Timeout-Einheiten-Inkonsistenz

**Status**: NEU - Naming-Inkonsistenz

**Quellen**:
- extracted_knowledge.md Abschnitt 5.2: `DATA_STALE_TIMEOUT_SEC` (mit Suffix `_SEC`)
- Andere Timeouts fehlen: Retry-Intervall (60s), Exponential Backoff (max 5 Versuche) - keine ENV-Variablen

**Konflikt**: Nur ein Timeout hat Suffix, andere sind hardcoded.

**Auswirkung**: Inkonsistente Namenskonvention, schwer konfigurierbare Retry-Logik.

**Empfehlung**:
1. Zusätzliche ENV-Variablen: `RETRY_INTERVAL_SEC` (Default: 60), `MAX_RETRY_ATTEMPTS` (Default: 5, 10)
2. ODER: Suffix `_SEC` entfernen und Einheit in Doku klären

---

### 🆕 Konflikt 6: Secrets-Validierung vs. Startup-Verhalten

**Status**: NEU - Widerspruch in Fehlerbehandlung

**Quellen**:
- extracted_knowledge.md Abschnitt 5.1: "Fehlerhafte Secrets → Retry-Loop mit exponential backoff (max. 5 Versuche, dann Crash)"
- extracted_knowledge.md Abschnitt 5.2: "Fehlende Pflicht-Variablen → Container crasht mit Exit Code 1"

**Konflikt**: Fehlende Secrets = sofortiger Crash, ABER fehlerhafte Secrets = Retry-Loop.

**Frage**: Wie unterscheidet der Code zwischen "fehlend" und "fehlerhaft"? Beide sollten konsistent behandelt werden.

**Empfehlung**: Klarstellen - entweder beides Retry ODER beides Crash. Retry macht nur bei Netzwerk-Timeouts Sinn, nicht bei Config-Fehlern.

---

## 3. Redundanzen (eliminierbar)

### Redundanz 1: Port-Listen

**Quellen**:
- ARCHITEKTUR.md Tabelle (Services & Ports)
- docker-compose.yml (Port-Mappings)
- extracted_knowledge.md Abschnitt 1.1 & 1.2 (dupliziert beide Quellen)

**Empfehlung**: In Template NUR auf docker-compose.yml als Single Source of Truth verweisen, nicht in mehreren Dokumenten wiederholen.

---

### Redundanz 2: Event-Schema-Beschreibungen

**Quellen**:
- EVENT_SCHEMA.json (vollständige Payload-Spezifikation)
- ARCHITEKTUR.md (Event-Topics mit Payload-Elementen)
- extracted_knowledge.md (Event-Topics Tabelle)

**Empfehlung**: In Doku nur Topic-Namen und Quelle (`EVENT_SCHEMA.json`) referenzieren, nicht Payload-Felder wiederholen.

---

### Redundanz 3: Code-Skeleton

**Quellen**:
- SERVICE_TEMPLATE.md (vollständiges Code-Beispiel)
- extracted_knowledge.md Abschnitt 3.3 (1:1 Kopie)

**Empfehlung**: In Template als separate Datei auslagern (`templates/service_skeleton.py`), nicht inline.

---

## 4. Fehlende Werte (aus Extraktion)

### Fehlend 1: Prometheus Alert-Manager Integration

**Status**: OFFEN in Pipeline 1 & 2

**Quelle**: Audit-Log Pipeline 1 (DevOps-Anmerkungen, Zeile 41)

**Lücke**: Keine Dokumentation, ob CRITICAL-Alerts automatisch an Alert-Manager weitergeleitet werden.

**Empfehlung**: Als "TODO" in Template markieren oder explizit als Out-of-Scope dokumentieren.

---

### Fehlend 2: Admin-Befehl für Drawdown-Freigabe

**Status**: REFERENZ FEHLT

**Quelle**: extracted_knowledge.md Abschnitt 2.4: "manuelle Freigabe via Admin-Befehl erforderlich"

**Lücke**: Kein Verweis, wo dieser Befehl dokumentiert ist, wie er aussieht, oder welches Tool ihn ausführt.

**Empfehlung**: Entweder Runbook-Referenz hinzufügen ODER als "TO BE IMPLEMENTED" markieren.

---

### Fehlend 3: Minimum Order Size

**Status**: RISIKO (aus Pipeline 1 Audit)

**Quelle**: Pipeline 1 Audit-Log, Zeile 65

**Lücke**: "Order trimmen auf Limit (nicht ablehnen)" - was wenn Signal-Mindestgröße unterschritten wird?

**Empfehlung**: ENV-Variable `MIN_ORDER_SIZE` einführen ODER explizit dokumentieren, dass Trimming keine Mindestgröße prüft.

---

## Zusammenfassung

**Validierte Konflikte**: 2 (Service-Namen, ENV-Präfix)
**Neu identifiziert**: 2 (Timeout-Einheiten, Secrets-Verhalten)
**Redundanzen**: 3 (Ports, Event-Schema, Code-Skeleton)
**Fehlende Werte**: 3 (Alert-Manager, Admin-Befehl, Min Order Size)

**Nächster Schritt**: software-jochen konsolidiert `extracted_knowledge.md` basierend auf diesen Findings.
