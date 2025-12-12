# CDB_PSM_POLICY
**Portfolio & State Manager – Canonical Policy**  
Version: 1.0.0 • Date: 2025-12-12 • Status: Canonical

---

## 1. Ziel & Verbindlichkeit (Single Source of Truth)

Der **Portfolio & State Manager (PSM)** ist die **einzige autoritative Quelle**
für alle finanzrelevanten Zustände in CDB:

- Kontostände (Cash, Equity)
- Positionen (Size, Entry, Mark, PnL)
- Margin & Leverage
- Drawdown & Exposure
- Historische Zustände (Replay)

**Technische Erzwingung**
- Kein anderer Service speichert persistente finanzielle States.
- Downstream-Systeme sind **read-only Konsumenten**.
- Abweichungen zwischen PSM-State und Konsumenten gelten als Fehlerzustand.

---

## 2. Event-Sourcing-Kern (TECHNISCH DEFINIERT)

### 2.1 Events (Immutable)

- Events sind **append-only**.
- Keine Updates, Deletes oder Overwrites.
- Speicherung in persistentem Event-Store (PostgreSQL / NATS JetStream).
- Event-Hash (Payload + Metadata) zur Tamper-Erkennung.

---

### 2.2 Idempotenz

- Jedes Event besitzt:
  - `event_id` (UUID)
  - `stream_id` (Account / Portfolio)
  - `sequence_number`
- Doppelte Events werden verworfen.
- Handler sind deterministisch und zustandsfrei.

---

### 2.3 Ordnung & Streams

- Strikte Ordnung **pro Stream** (`stream_id`).
- Keine Parallelverarbeitung innerhalb eines Streams.
- Globale Parallelität nur über unterschiedliche Streams.

---

### 2.4 Snapshots

- Snapshots nach:
  - fester Event-Anzahl **oder**
  - Zeitintervall
- Snapshot + Event-Replay = vollständiger State.
- Snapshots sind versioniert und prüfbar.

---

### 2.5 Projections / Views

- Views sind **abgeleitet**, niemals kanonisch.
- Bei Inkonsistenz: Rebuild aus Events.
- Views dürfen gelöscht und neu erzeugt werden.

---

## 3. Verantwortlichkeiten & Garantien

PSM garantiert Downstream-Konsumenten:

- **Deterministische Daten**
- **Zeitlich konsistente Zustände**
- **Reproduzierbarkeit durch Replay**
- **Versionierte Schemas**

**Nachweis**
- Replay-Tests sind Pflicht.
- Hash-Vergleiche zwischen Replays.
- Abweichungen blockieren Releases.

---

## 4. Schnittstellen (KANONISCH)

### 4.1 Input (Events)

**Protokoll**
- Event-basierte Übergabe (JSON)
- Persistenter Bus (NATS JetStream / Kafka)

**Pflichtfelder**
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
```

---

### 4.2 Output

**APIs (Read-only)**
- `GET /psm/state/{account_id}`
- `GET /psm/positions/{account_id}`
- `GET /psm/margin/{account_id}`

**Events**
- `psm.state.updated`
- `psm.position.updated`
- `psm.margin.updated`

---

## 5. Qualitätsanforderungen (TECHNISCH GEPRÜFT)

### 5.1 Deterministische Replays
- Replay ab beliebigem Event.
- Ergebnis = identischer State.
- Abweichung = Fehler.

---

### 5.2 Schema-Versionierung
- SemVer für Events.
- Breaking Changes verboten ohne Migration.
- Alte Events bleiben gültig.

---

### 5.3 Auditability
- Vollständige Event-Historie.
- Revisionssichere Speicherung.
- Jeder State ist erklärbar.

---

## 6. Durchsetzung & Audit

- CI prüft:
  - Event-Schema-Konformität
  - Replay-Konsistenz
- Kein Merge bei Verstoß.
- Audit jederzeit reproduzierbar.

---

## 7. Gültigkeit

Diese Policy ist **kanonisch**.  
PSM ist die **Single Source of Truth**.

Abweichungen gelten als Governance-Bruch.
