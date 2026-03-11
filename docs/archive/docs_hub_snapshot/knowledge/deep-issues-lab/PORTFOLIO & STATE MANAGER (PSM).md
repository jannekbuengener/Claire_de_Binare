# **🧠 DEEP RESEARCH – Portfolio & State Manager (PSM)**

---

## **1️⃣ Metadaten**

| Feld | Beschreibung |
| :---- | :---- |
| **Titel:** | Portfolio & State Manager (PSM): Eine Event-Sourcing-Architektur |
| **Autor:** | Gemini |
| **Datum:** | 16.12.2025 |
| **Phase:** | Decision |
| **Status:** | 🟢 Abgeschlossen |
| **Version:** | 1.0 |
| **Verknüpfte Dokumente:** | `007 PSM SHORT.md`, `008 PORTFOLIO & STATE MANAGER (PSM).tsx` |

---

## **2️⃣ Forschungsziel & Hypothese**

**Zielsetzung:**  
Design und Spezifikation einer robusten, auditierbaren und performanten State-Management-Architektur (PSM) für das Handelssystem *Claire de Binare (CDB)*, die als alleinige Quelle der Wahrheit (Single Source of Truth) für den gesamten Portfolio-Zustand dient.

**Hypothese:**  
Ein **hybrider Event-Sourcing-Ansatz** (Events als "Source of Truth", ergänzt durch Snapshots und Materialized Views zur Performance-Optimierung) ist einem rein zustandsbasierten CRUD/Snapshot-Ansatz überlegen. Diese Überlegenheit manifestiert sich in kritischen Bereichen wie **deterministischer Auditierbarkeit, präziser Backtesting-Fähigkeit** und der Erfüllung **regulatorischer Anforderungen** (z.B. MiFID II).

**Erfolgskriterium:**  
Die entworfene Architektur muss (1) ein deterministisches Replay beliebiger Handelsaktivitäten ermöglichen, (2) Lesezugriffe für die Risk-Engine im Sub-Sekunden-Bereich bereitstellen und (3) einen klaren Skalierungspfad von einem MVP (Docker-basiert) zu einer hochverfügbaren Produktionsumgebung (Kubernetes, Kafka) aufzeigen.

---

## **3️⃣ Kontext & Motivation**

Ein algorithmisches Handelssystem wie CDB benötigt eine absolut verlässliche und atomare Sicht auf seinen Zustand – offene Positionen, Margin, verfügbares Kapital und realisierte/unrealisierte Gewinne und Verluste. Jede Entscheidung der Risk-Engine oder des Order-Managements hängt von der Genauigkeit dieser Daten ab.

Traditionelle, zustandsbasierte Systeme (CRUD) überschreiben bei jeder Änderung den alten Zustand. Dadurch gehen wertvolle Informationen über den *Weg* zu diesem Zustand verloren. Für ein Trading-System ist dies fatal, da es Audits erschwert, die Fehlersuche verkompliziert und exaktes Backtesting unmöglich macht. Event Sourcing löst dieses Kernproblem, indem jede Zustandsänderung als unveränderliches, chronologisches Ereignis (Event) erfasst wird. Der aktuelle Zustand ist somit nur noch eine Konsequenz der abgespielten Ereignisse.

---

## **4️⃣ Forschungsfragen**

1.  **Event Sourcing vs. Snapshotting: Welcher Ansatz ist für ein Krypto-Trading-System besser geeignet?**  
    *Antwort: Ein Hybrid-Modell. Reines Event Sourcing ist ideal für Auditierbarkeit, aber zu langsam für schnelle Lesezugriffe. Ein reines Snapshot-Modell ist schnell, verliert aber die Historie. Die Kombination beider Ansätze ist optimal.*

2.  **Wie kann die Architektur schnelle Lese-Performance (für die Risk-Engine) und 100%ige Auditierbarkeit (für Compliance) vereinen?**  
    *Antwort: Durch die Trennung von Schreib- und Lesepfaden (CQRS-Pattern). Writes sind Append-Only in ein Event-Log. Reads greifen auf optimierte, periodisch erstellte Snapshots oder Materialized Views in PostgreSQL zu.*

3.  **Wie sieht eine konkrete Implementierung aus (Datenbank, Services, APIs)?**  
    *Antwort: PostgreSQL als Event Store, ein Python/FastAPI-Service als Core-Logik und REST-APIs für Event-Ingestion und State-Abfragen.*

4.  **Wie kann das System vom MVP zur Produktionsreife skaliert werden?**  
    *Antwort: Durch den definierten Erweiterungspfad: Migration von Redis Pub/Sub zu einem persistenten Event-Stream (Kafka/NATS) und Deployment auf Kubernetes mit GitOps-Praktiken (ArgoCD).*

---

## **5️⃣ Methodik**

**Vorgehen:**  
Die Untersuchung basiert auf einer **vergleichenden Analyse** (Comparative Analysis) der beiden führenden State-Management-Paradigmen (Event Sourcing vs. zustandsbasiertes CRUD) und dem anschließenden **Architekturentwurf** (Architectural Design) für eine hybride Lösung. Die Empfehlung stützt sich auf etablierte Best Practices aus der Hochfrequenz-Finanzindustrie und auf Open-Source-Implementierungen (z.B. Marten).

**Werkzeuge:**  
*   **MVP:** PostgreSQL, Redis, Python (FastAPI), Docker Compose
*   **Produktionsskala:** Kafka/NATS JetStream, Kubernetes, ArgoCD, Terraform/Helm, Prometheus, Grafana

---

## **6️⃣ Daten & Feature-Definition**

### Event-Schema Beispiele (JSONB in PostgreSQL)

**TradeExecuted:**
```json
{
  "event_id": "uuid-v4",
  "event_type": "TradeExecuted",
  "timestamp": "2025-12-12T10:30:00Z",
  "account_id": "acc_001",
  "symbol": "BTC-PERP",
  "side": "long",
  "quantity": 0.5,
  "price": 42000.00,
  "commission": 2.10
}
```

**FundingApplied:**
```json
{
  "event_id": "uuid-v4",
  "event_type": "FundingApplied",
  "timestamp": "2025-12-12T08:00:00Z",
  "account_id": "acc_001",
  "symbol": "ETH-PERP",
  "funding_rate": 0.0001,
  "funding_payment": -0.042
}
```

### Domain Model (Core Entities)
*   **Account**: `account_id`, `balance`, `margin_initial`, `margin_maintenance`, `leverage_limit`
*   **Position**: `symbol`, `side (long|short)`, `size`, `entry_price`, `mark_price`, `unrealized_pnl`, `liquidation_price`
*   **Order**: `order_id`, `symbol`, `side`, `type (market|limit|stop)`, `quantity`, `status`
*   **Fill**: `fill_id`, `order_id`, `price`, `quantity`, `commission`, `timestamp`

---

## **7️⃣ Architektur-Skizze**

### Service-Architektur
```
┌─────────────────────────────────────────────────────────────────┐
│                      EXECUTION SERVICE                          │
│  (Order Fills, Trade Confirmations)                             │
└────────────┬────────────────────────────────────────────────────┘
             │ Redis Pub/Sub: trade.filled
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PORTFOLIO & STATE MANAGER (PSM)                │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ Event Ingest │  │ State Engine │  │ Snapshot Mgr │           │
│  │   Handler    │  │  (Aggregate) │  │  (Optimizer) │           │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘           │
│         │                 │                  │                  │
│         ▼                 ▼                  ▼                  │
│  ┌─────────────────────────────────────────────────────┐        │
│  │          PostgreSQL Event Store + Snapshots         │        │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────┐   │        │
│  │  │   events     │  │  snapshots   │  │ mat_views│   │        │
│  │  │  (append)    │  │  (periodic)  │  │ (queries)│   │        │
│  │  └──────────────┘  └──────────────┘  └──────────┘   │        │
│  └─────────────────────────────────────────────────────┘        │
│                                                                 │
│  Redis Pub/Sub OUT: position.updated, margin.warning            │
└────────────┬────────────────────────────────────────────────────┘
             │
             ├─────────────► RISK ENGINE (Margin, Liquidation)
             ├─────────────► EXECUTION (Order Sizing)
             └─────────────► ANALYTICS (PnL, Reporting)
```

### API-Schnittstellen (MVP)
*   `POST /api/psm/events`: Nimmt neue Events entgegen (muss idempotent sein).
*   `GET /api/psm/state/:account_id`: Gibt den aktuellen Portfolio-Zustand zurück (rekonstruiert aus Snapshot + neuen Events).
*   `GET /api/psm/positions/:account_id`: Liefert alle offenen Positionen inkl. unrealisiertem PnL.
*   `GET /api/psm/replay/:account_id?from=timestamp`: Startet ein Replay für Backtesting/Shadow-Mode.

---

## **8️⃣ Ergebnisse & Erkenntnisse**

### **8.1. Quantitative Resultate (Vergleich der Ansätze)**

| Kriterium | Event-Sourced PSM | Snapshot-basierter PSM |
| :--- | :--- | :--- |
| **Replay-Fähigkeit** | ✅ Vollständig | ⚠️ Eingeschränkt |
| **Audit Trail** | ✅ Perfekt | ⚠️ Gut, aber mit Lücken |
| **Backtesting** | ✅ Ideal | ⚠️ Begrenzt |
| **Read Performance** | ⚠️ Langsamer (ohne Optimierung) | ✅ Schnell |
| **Write Performance**| ✅ Sehr schnell (Append-Only) | ⚠️ Langsamer (Update + Log) |
| **Komplexität** | ⚠️ Höher | ✅ Niedriger |
| **Debugging** | ✅ Exzellent | ⚠️ Schwierig |
| **Regulatorik** | ✅ Perfekter Fit | ⚠️ Zusatzaufwand |

### **8.2. Qualitative Erkenntnisse**

Die Analyse zeigt klar, dass die Vorteile des Event-Sourcing-Ansatzes für ein Trading-System die höhere initiale Komplexität überwiegen.
*   **Auditierbarkeit ist kein Feature, sondern eine Notwendigkeit:** Ein lückenloser Event-Log ist die einzige Möglichkeit, regulatorische Anforderungen (MiFID II) zuverlässig zu erfüllen und Forensik nach einem Incident zu betreiben.
*   **Backtesting-Genauigkeit:** Nur durch das Replay eines exakten Event-Streams können Strategien unter realitätsnahen Bedingungen validiert werden.
*   **Performance-Optimierung ist zwingend:** Ein reines Event-Replay für jede Leseanfrage ist zu langsam. Die Kombination mit Snapshots (z.B. alle 100 Events) und Materialized Views für häufige Abfragen ist der Schlüssel zu einem performanten System.

---

## **9️⃣ Risiken & Gegenmaßnahmen**

| Risiko | Kategorie | Gegenmaßnahme |
| :--- | :--- | :--- |
| **Erhöhte Komplexität** | Architektur | Klare Event-Schema-Definition; Einführung einer Schema-Registry; Nutzung von Upcasting-Patterns für die Migration alter Events. |
| **Langsame Read-Performance** | Performance | Implementierung von Snapshotting (zeit- oder eventbasiert); Einsatz von Materialized Views für komplexe Queries. |
| **Event-Verlust (im MVP)** | Zuverlässigkeit | Redis Pub/Sub ist nicht persistent. Risiko wird akzeptiert für MVP. Gegenmaßnahme: Migration zu Kafka/NATS im Erweiterungspfad. |
| **Event-Ordering** | Korrektheit | Sicherstellung, dass Events pro Stream (z.B. pro `account_id`) geordnet verarbeitet werden. In Kafka durch Partition-Keys gewährleistet. |

---

## **🔟 Entscheidung & Empfehlung**

**Bewertung:**
*   ✅ **Go**

**Begründung:**  
Die vorgeschlagene hybride Event-Sourcing-Architektur ist die technisch überlegene und zukunftssichere Grundlage für den Portfolio & State Manager des CDB. Sie löst die Kernanforderungen an Auditierbarkeit, Testbarkeit und Performance auf elegante Weise und bietet einen klaren, schrittweisen Pfad von einem schnell umsetzbaren MVP zu einem hochskalierbaren Produktionssystem. Die Investition in die höhere Anfangskomplexität wird sich durch geringere Betriebskosten, einfacheres Debugging und bessere Compliance langfristig auszahlen.

**Empfohlene nächsten Schritte:**
1.  Umsetzung des **4-Wochen-MVP-Implementierungsplans**.
2.  Parallel dazu: Evaluierung von **NATS JetStream** als leichtgewichtige Alternative zu Kafka für Phase 2.
3.  Definition des initialen **Event-Schemas** für `TradeExecuted` und `FundingApplied`.

---

## **11️⃣ Deliverables**

*   Dieses Deep-Research-Dokument.
*   PostgreSQL-Schema für `events` und `snapshots` Tabellen.
*   `docker-compose.yml` für die MVP-Umgebung.
*   Ein 4-Wochen-Implementierungsplan für das MVP.

---

## **12️⃣ Quellen & Referenzen**

*   Interne Dokumente: `007 PSM SHORT.md`, `008 PORTFOLIO & STATE MANAGER (PSM).tsx`
*   Vergleichbare Open-Source-Projekte: Marten (PostgreSQL als Event Store)
*   Konzepte: CQRS (Command Query Responsibility Segregation), Event Sourcing Patterns.


