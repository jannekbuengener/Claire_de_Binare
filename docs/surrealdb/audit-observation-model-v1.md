# Audit Observation Model v1

**Issue:** #2011  
**Parent:** #2004 (Wave-4)  
**Epic:** #1976  
**Status:** Draft (Wave-4 Reconcile)  
**Schema:** `infrastructure/surrealdb/context_intelligence_v0.surql` (`audit_observation` table)  
**Guardrail:** LR = NO-GO. Kein Live-Trading-Go, kein Echtgeld-Go aus Observations ableitbar.

---

## 1. Zweck und Grenzen

`audit_observation` ist ein **Beobachtungssignal**, kein Freigabemechanismus.

Beobachtungen werden erzeugt, wenn das Kontext-Inspektionssystem Qualitätsmängel,
Lücken, Konflikte oder Risiken im Wissensbestand erkennt. Sie sind Signale für
menschliche Review oder gesteuerte Agenten-Folgearbeit — **keine autonomen Aktionen**.

**Nicht-Ziele:**
- Keine Live-/Echtgeld-Freigabe.
- Keine Runtime-Writes.
- Keine Memory-Writes.
- Keine automatische Issue-Erzeugung.
- Kein autonomes Stoppen anderer Agenten ohne Human-Gate.

---

## 2. `audit_observation` Objektfelder

| Feld | Typ | Pflicht | Beschreibung |
|---|---|---|---|
| `observation_id` | string | ✅ REQUIRED | Stable identifier. Format: `obs:<uuid>` |
| `observation_type` | string | ✅ REQUIRED | Einer der 8 Typen aus §3 |
| `subject_ref` | record | ✅ REQUIRED | Betroffenes Objekt (z.B. `claim:xyz`, `decision_event:abc`) |
| `severity` | string | ✅ REQUIRED | Einer der 3 Schweregrade aus §4 |
| `message` | string | ✅ REQUIRED | Menschenlesbare Beschreibung der Beobachtung |
| `evidence_refs` | array | — | Verweise auf `evidence_ref`-Records (Begründung) |
| `related_claims` | array | — | Verweise auf `claim`-Records |
| `related_decisions` | array | — | Verweise auf `decision_event`-Records |
| `related_memory` | array | — | Verweise auf `agent_memory`-Records |
| `confidence` | float | — | Konfidenzwert [0.0–1.0] |
| `observed_by` | string | ✅ REQUIRED | Agent-ID oder Tool, das die Observation erzeugt hat |
| `observed_at` | datetime | ✅ REQUIRED | Zeitpunkt der Beobachtung |
| `status` | string | ✅ REQUIRED | Einer der 4 Status-Werte aus §5 |
| `comment` | string | — | Optionaler freier Kommentar |
| `created_at` | datetime | ✅ REQUIRED | Automatisch gesetzt: `VALUE $value OR time::now()` |

---

## 3. Typ-Katalog (`observation_type`)

Exakt 9 kanonische Typen. Kein freier String außerhalb dieses Katalogs.

| Typ | Beschreibung | Typischer Severity |
|---|---|---|
| `missing_evidence` | Evidence fehlt für einen Claim oder eine Decision | `warning` / `blocking` |
| `stale_evidence` | Evidence vorhanden, aber abgelaufen oder hash-veraltet | `warning` |
| `weak_claim` | Claim hat evidence_refs, aber Konfidenz unter Threshold | `info` / `warning` |
| `disputed_claim` | Zwei oder mehr Evidence widersprechen dem Claim-Statement | `warning` / `blocking` |
| `memory_without_source` | `agent_memory`-Eintrag ohne `source_refs` | `warning` |
| `decision_without_evidence` | `decision_event` ohne `evidence_refs` und ohne `human_go` | `warning` / `blocking` |
| `conflicting_decision` | Zwei `decision_event`-Records mit widersprüchlichen Antworten ohne Supersession-Chain | `warning` / `blocking` |
| `scope_risk` | Erkannte Scope-Drift oder Scope-Überschreitung ohne autorisierte Erweiterung | `warning` / `blocking` |
| `memory_write_gate_evaluation` | Human-GO memory write gate evaluation (dry-run or blocked) | `info` / `blocking` |

---

## 4. Severity-Katalog

| Severity | Bedeutung | Agenten-Verhalten |
|---|---|---|
| `info` | Beobachtung dokumentiert, kein akuter Handlungsbedarf | Weiterarbeiten erlaubt |
| `warning` | Qualitätslücke erkannt, menschliche Überprüfung empfohlen | Weiterarbeiten mit Hinweis |
| `blocking` | Kritische Lücke. Agenten-Arbeit soll pausieren bis Human-Review | Agenten führen **keine** weiteren Writes in betroffenen Scope aus |

**Wichtig:** `blocking` ist ein Signal durch Konvention, kein technischer Lock.
Kein autonomes Gate, kein automatischer Runtime-Stop.

---

## 5. Status-Katalog

| Status | Bedeutung |
|---|---|
| `open` | Observation aktiv, noch nicht adressiert |
| `accepted_risk` | Menschliche Entscheidung: Risiko akzeptiert, kein Fix geplant |
| `resolved` | Ursache behoben, Observation geschlossen |
| `superseded` | Durch neuere Observation oder Policy überschrieben |

---

## 6. Pflichtfelder (Zusammenfassung)

Folgende Felder sind für jeden `audit_observation`-Record zwingend:

`observation_id`, `observation_type`, `subject_ref`, `severity`, `message`,
`observed_by`, `observed_at`, `status`, `created_at`

Für v0-draft: Validierung ist Dokumentations-Konvention, nicht DB-enforced.
Enforcement kommt in einem späteren Schema-Version (v1+).

---

## 7. Guardrails

| # | Guardrail |
|---|---|
| A1 | `audit_observation` ist Signal, keine Freigabe. |
| A2 | `blocking`-Observations stoppen Agenten-Arbeit durch Konvention, nicht durch technischen Lock. |
| A3 | Kein Live-/Echtgeld-Go aus Observation ableitbar. |
| A4 | Kein Runtime-Write als direkte Folge einer Observation. |
| A5 | Kein Memory-Write als direkte Folge einer Observation. |
| A6 | Keine automatische Issue-Erzeugung auf GitHub. |
| A7 | `observation_type` muss aus dem 9-Typen-Katalog (§3) stammen. |
| A8 | `severity` muss aus dem 3-Werte-Katalog (§4) stammen. |
| A9 | `status` muss aus dem 4-Werte-Katalog (§5) stammen. |
| A10 | Observations werden nicht gelöscht — `status: superseded` oder `resolved` für Ablösung. |

---

## 8. Schema-Referenz

Schema-Definition: `infrastructure/surrealdb/context_intelligence_v0.surql`, Tabelle `audit_observation`.

Verwandte Dokumente:
- `docs/surrealdb/scoped-agent-memory-model-v1.md` — Memory Write Rules (Wave-4 #2009)
- `docs/surrealdb/context-core-schema-v1.md` — Core Schema Conventions
- `infrastructure/surrealdb/context_intelligence_v0.surql` — Vollständiges Schema
