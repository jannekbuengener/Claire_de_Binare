---
relations:
  role: policy
  domain: governance
  upstream:
    - knowledge/governance/CDB_POLICY_STACK_MINI.md
    - knowledge/governance/CDB_CONSTITUTION.md
    - knowledge/governance/CDB_GOVERNANCE.md
  downstream: []
  status: canonical
  tags: [psm, portfolio, state, event_sourcing, policy]
---
# CDB_PSM_POLICY
**Portfolio & State Manager (PSM) – Canonical Policy**

Version: 1.1  
Status: Canonical

---

## 1. Ziel (Single Source of Truth)

Der PSM ist die **einzige autoritative Quelle** für alle finanzrelevanten Zustände:

- Kontostände (Cash, Equity)
- Positionen (Size, Entry, Mark, PnL)
- Margin & Leverage
- Drawdown & Exposure
- Historische Zustände (Replay)

**Technische Erzwingung**
- Kein anderer Service speichert persistente finanzielle States.
- Downstream-Systeme sind **read-only** Konsumenten.
- Abweichung PSM vs. Konsument = Fehlerzustand.

---

## 2. Event-Sourcing-Kern (hart)

### 2.1 Events (immutable)
- append-only
- keine Updates/Deletes/Overwrites
- persistenter Event-Store (PostgreSQL / NATS JetStream)
- Event-Hash (Payload + Metadata) zur Tamper-Erkennung

### 2.2 Idempotenz
Pflichtfelder:
- `event_id` (UUID)
- `stream_id` (Account/Portfolio)
- `sequence_number`

Doppelte Events werden verworfen. Handler sind deterministisch.

### 2.3 Ordnung & Streams
- strikte Ordnung pro `stream_id`
- keine Parallelverarbeitung innerhalb eines Streams
- Parallelität nur über unterschiedliche Streams

### 2.4 Snapshots
- nach Event-Anzahl oder Zeitintervall
- Snapshot + Replay = vollständiger State
- Snapshots sind versioniert, prüfbar

### 2.5 Projections / Views
- Views sind abgeleitet, niemals kanonisch
- bei Inkonsistenz: Rebuild aus Events
- Views dürfen gelöscht und neu erzeugt werden

---

## 3. Garantien

PSM garantiert:
- deterministische States
- zeitlich konsistente Zustände
- Reproduzierbarkeit durch Replay
- versionierte Schemas

Nachweis:
- Replay-Tests sind Pflicht
- Hash-Vergleiche zwischen Replays
- Abweichung blockiert Releases

---

## 4. Schnittstellen (kanonisch)

### 4.1 Input (Events)
Protokoll: Event-basiert (JSON) über persistenten Bus.

Pflichtfelder:
```json
{
  "event_id": "uuid",
  "event_type": "TradeExecuted",
  "stream_id": "account_id",
  "sequence_number": 123,
  "timestamp": "ISO-8601",
  "schema_version": "1.x",
  "payload": {}
}
4.2 Output

Read-only APIs:

GET /psm/state/{account_id}

GET /psm/positions/{account_id}

GET /psm/margin/{account_id}

Events:

psm.state.updated

psm.position.updated

psm.margin.updated

5. Qualitätsanforderungen (enforced)

deterministische Replays (identischer Input → identischer Output)

SemVer für Event-Schemas

Breaking Changes nur via Migration, alte Events bleiben gültig

vollständige Auditability: jeder State ist erklärbar

6. Durchsetzung & Audit

CI prüft:

Event-Schema-Konformität

Replay-Konsistenz

Hash-Kohärenz

Kein Merge bei Verstoß.

7. Gültigkeit

PSM ist Single Source of Truth.
Abweichungen = Governance-Bruch.


---
