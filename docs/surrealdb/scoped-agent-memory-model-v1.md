# CDB Context Intelligence — Scoped Agent Memory Model v1

**Status**: Draft (Wave 1 Reconcile)
**Authority**: Issue #1983 / Parent #1976
**Schema Implementation**: `infrastructure/surrealdb/context_intelligence_v0.surql` (`agent_memory` table)
**Dependencies**: #1977 (target vision), #1978 (ownership), #1981 (core schema)
**Ownership Reference**: `infrastructure/config/surrealdb/ownership.yaml` (domain `agent_memory`)
**Guardrail**: trade-capable is NOT a Live-Readiness-Go; Live-Readiness remains NO-GO.

---

## 1. Zweck

Dieses Dokument definiert das **kontrollierte Scoped Agent Memory Model** für das CDB Context
Intelligence System (CIS). Es legt Memory-Typen, Pflichtfelder, Write-/TTL-/Supersede-/Stale-Regeln
und Guardrails fest.

**Memory ist ein Hinweis, keine Wahrheit.** Kein Agent darf eine Runtime-Entscheidung allein
aus Memory ableiten. Memory-Einträge müssen mit Evidence-Referenzen belegt sein, um Vertrauen
zu beanspruchen.

---

## 2. Scope und Nicht-Ziele

**Scope**:
- Memory-Typen und deren Semantik
- Pflichtfelder pro Memory-Eintrag
- Write-, TTL-, Supersede- und Stale-Regeln
- Rules gegen unscoped global memory
- Abgrenzung `agent_memory` vs. `shared_memory`

**Nicht-Ziele**:
- Keine Memory-Write-Implementierung
- Kein produktives SurrealDB-Apply
- Keine Ingestion-Pipeline
- Keine MCP-Tool-Implementierung
- Kein Trading-State, keine Orders, keine Positions, keine Fills
- Keine Secrets, keine Broker-Credentials, keine API-Keys
- Keine Runtime-Entscheidungen aus Memory
- Kein Live-Readiness-Upgrade
- Kein Echtgeld-Go

---

## 3. Memory-Typen

Jeder Memory-Eintrag gehört zu genau einem `memory_type`. Typen sind orthogonal und nicht
als Hierarchie zu verstehen.

### 3.1 `working_memory`

**Semantik**: Kurzlebiger, aufgabenspezifischer Zustand innerhalb einer Session oder eines
Tasks. Wird nach Abschluss der Aufgabe obsolet.

**Typische Inhalte**: Aktuelle Aufgabenstellung, Zwischenergebnisse, offene Fragen, geladene
Dateilisten für laufende Session.

**Empfohlene TTL**: Kurz (< 4 Stunden). Kein dauerhaftes Retain ohne explizites Human-GO.

**Beispiel**: Geladene Issue-Liste für laufende Wave-1-Session.

---

### 3.2 `semantic_memory`

**Semantik**: Allgemeines Faktenwissen über das System, das über Sessions hinaus gilt.
Beschreibt, wie das System funktioniert, welche Komponenten existieren, welche Konventionen
gelten.

**Typische Inhalte**: Systemarchitektur-Fakten, Konventionen, kanonische Pfade, Board-Stage,
LR-Verdict (nur als read pointer, nicht als abgeleitetes Go).

**Empfohlene TTL**: Mittel bis lang (Tage bis Wochen). Aktualisierung wenn Source-Hash-Mismatch
erkannt wird.

**Beispiel**: "Das Working Repo ist kanonischer Pfad für Agenten-Doku."

---

### 3.3 `episodic_memory`

**Semantik**: Aufgezeichnete Ereignisse und Erfahrungen aus vergangenen Sessions oder Runs.
Enthält Kontext über was wann passiert ist.

**Typische Inhalte**: Session-Logs (Pointer), gemergte PRs, geschlossene Issues, beobachtete
Drift-Events, ausgeführte Validierungen.

**Empfohlene TTL**: Mittel (Tage). Stale nach Hash-/Issue-State-Mismatch.

**Beispiel**: "Wave 7 wurde über PRs #2224, #2225, #2226 gelandet und ist CLOSED."

---

### 3.4 `procedural_memory`

**Semantik**: Wissen darüber, wie Aufgaben ausgeführt werden. Verfahrensschritte, Skripte,
Workflows, Checklisten.

**Typische Inhalte**: Bootloader-Reihenfolge, CI-Commands, Session-Start/Close-Skills,
bekannte Fehlerbehandlungsschritte.

**Empfohlene TTL**: Lang (Wochen bis Monate). Aktualisierung wenn Skill-/Docs-Hash geändert.

**Beispiel**: "Session-Start erfordert: AGENTS.md → agents/AGENTS.md → OPEN_CODE_AGENTS.md."

---

### 3.5 `preference_memory`

**Semantik**: Bekannte Präferenzen, Stil- und Verhaltensregeln für Agenten. Kann aus
Governance-Dokumenten oder expliziten Human-Instruktionen stammen.

**Typische Inhalte**: Formatierungsregeln, Sprach-Präferenzen, bevorzugte Commit-Stile,
bekannte Do/Don't-Regeln.

**Empfohlene TTL**: Lang (Wochen bis Monate). Nur mit Evidence-Referenz auf das Quell-Dokument.

**Beispiel**: "Kommentare auf GitHub nur nach explizitem GO GITHUB LIVE."

---

### 3.6 `risk_memory`

**Semantik**: Aufgezeichnete Risiken, Warnungen, Stop-Conditions, bekannte Drift-Vektoren.
Kein Live-Risk-State. Kein Trading-Risiko.

**Typische Inhalte**: Bekannte Drift-Vektoren aus CONTROL_REGISTER, dokumentierte
Stop-Conditions, offene Risiko-Issues, historische Fehler-Patterns.

**Empfohlene TTL**: Mittel bis lang. Stale wenn Referenced-Issue geschlossen oder Drift
aufgelöst wurde.

**Wichtige Einschränkung**: `risk_memory` enthält **kein** Trading-Risk-State (Drawdown,
Exposure, Margin). Nur Governance-/Process-Risiken.

**Beispiel**: "Issue #1372: Solo-Maintainer in SOPs — kein Mehrpersonen-Eskalationspfad."

---

## 4. Pflichtfelder

Jeder `agent_memory`-Eintrag MUSS folgende Felder enthalten:

| Feld | Typ | Regel |
|---|---|---|
| `namespace` | `string` | Pflicht. Namespace des Agenten (z. B. `session`, `project`, `governance`). Kein leerer String. |
| `scope` | `string` | Pflicht. Vollständiger Agent-Scope-Identifier (z. B. `agent:OPENCODE/copilot`). Kein unscoped write. |
| `memory_type` | `string` | Pflicht. Einer der 6 kanonischen Typen (siehe Abschnitt 3). |
| `content` | `string` | Pflicht. Memory-Inhalt. Kein leerer String. |
| `source_refs` | `array` | Pflicht. Mind. eine Quellreferenz. Git-Pfade müssen als content-adressierbarer Hash (`file_path@commit_sha`) angegeben werden wenn verfügbar; Issue/PR-URLs sind zulässig als sekundäre Referenz, aber nicht als alleiniger Nachweis. |
| `evidence_refs` | `array` | Pflicht. Mind. eine Evidenzreferenz (Evidence-ID, Commit-Hash oder CI-Run-URL). Kein Memory ohne provenance-backed Evidence. Entspricht `missing_source_hash`-Drift-Regel in `ownership.yaml`. |
| `confidence` | `float` | Pflicht. [0.0–1.0]. Unvollständige oder unverified Memory → niedrig (< 0.5). |
| `ttl` | `int` | Pflicht. Time-to-Live in Sekunden. 0 = kein automatisches Expire (nur mit Human-GO). |
| `created_by` | `string` | Pflicht. Agent ID des Erstellers. |
| `created_at` | `datetime` | Pflicht. Erstellungszeitpunkt (automatisch durch Schema gesetzt). |
| `expires_at` | `datetime` | Pflicht wenn `ttl > 0`. Expliziter Ablaufzeitpunkt. |
| `superseded_by` | `string` | Optional. ID des ersetzenden Eintrags. Gesetzt wenn der Eintrag durch neueren Eintrag ersetzt wird. |

---

## 5. Write-Regeln

### 5.1 Scoped Writes (Pflicht)

- Jeder Write **muss** `scope` + `namespace` enthalten.
- `scope` muss den Agent-Identifier des Schreibers enthalten.
- Kein Agent darf in den Scope eines anderen Agenten schreiben.
- Kein Agent darf ohne `namespace` schreiben (kein unscoped global write).

### 5.2 Scope-Änderungen

- Änderungen am `scope`-Modell (neue Scopes, neue Namespaces, Erweiterungen) erfordern
  ein explizites **Human-GO**.
- Agenten dürfen neue Einträge in bekannte Scopes schreiben, aber keine neuen Scope-Strukturen
  autonom einführen.

### 5.3 Source-Pflicht

- Kein Memory darf ohne `source_refs` entstehen.
- Jeder Memory-Eintrag muss mindestens einen Git-Pfad, Issue-URL oder PR-URL als Quelle haben.
- Memory ohne Quelle ist ungültig und muss vom Validator abgelehnt werden.

### 5.4 No Cross-Agent Bypass

- Kein Agent darf `agent_memory`-Einträge anderer Agenten überschreiben.
- Cross-Agent-Zugriff auf Memory ist **read-only**; Cross-Agent-Writes sind verboten.
- Ausnahme: explizites Human-GO für koordinierte Memory-Transitions.

### 5.5 No Backflow

- Memory-Inhalte dürfen **nicht** automatisch in Git, Postgres oder die Trading-Runtime
  zurückgeschrieben werden.
- Memory ist ein **Hinweis**, kein Auftrag.

---

## 6. TTL-Regeln

| Memory-Typ | Empfohlene TTL | Maximale TTL ohne Human-GO |
|---|---|---|
| `working_memory` | 1–4 Stunden | 24 Stunden |
| `episodic_memory` | 24–72 Stunden | 7 Tage |
| `semantic_memory` | 7–30 Tage | 90 Tage |
| `procedural_memory` | 30–90 Tage | 180 Tage |
| `preference_memory` | 30–90 Tage | 180 Tage |
| `risk_memory` | 7–30 Tage | 90 Tage |

**TTL-Regeln**:
- TTL = 0 bedeutet kein automatisches Expire. Nur mit explizitem Human-GO erlaubt.
- `expires_at` muss gesetzt sein wenn `ttl > 0`.
- Abgelaufene Einträge sind **stale** — sie dürfen gelesen, aber nicht mehr als
  aktuelle Wahrheit behandelt werden.
- TTL-Überschreitung führt nicht zu automatischem Löschen; der Eintrag bleibt im Audit-Trail.

---

## 7. Supersede-Regeln

### 7.1 Supersede-Prozess

Wenn ein Memory-Eintrag durch neues Wissen ersetzt wird:

1. Neuen Eintrag mit aktueller `source_refs` und `evidence_refs` erstellen.
2. Neuen Eintrag mit erhöhter oder angepasster `confidence` versehen.
3. Alten Eintrag **nicht löschen** — `superseded_by` auf die ID des neuen Eintrags setzen.
4. Alter Eintrag bleibt als historischer Audit-Trail erhalten.

### 7.2 Supersede-Kette

- `superseded_by` ist ein String-Verweis auf die ID des nachfolgenden Eintrags.
- Ketten sind erlaubt (A → B → C), aber zirkuläre Referenzen sind verboten.
- Beim Lesen ist immer der Endknoten der Supersede-Kette der gültige Eintrag.

### 7.3 Automatische Supersedes

- Agenten dürfen innerhalb ihres Scopes Supersede-Ketten anlegen.
- Supersedes über Scope-Grenzen hinweg erfordern Human-GO.

---

## 8. Stale-Memory-Regeln

Memory wird als **stale** behandelt, wenn einer der folgenden Fälle eintritt:

| Bedingung | Aktion |
|---|---|
| `expires_at` ist überschritten | Eintrag als stale lesen; nicht als Wahrheit behandeln |
| `stale_after` (Sekunden) seit `created_at` überschritten | Eintrag als stale markieren |
| Quelle in `source_refs` hat Hash-Mismatch (Datei geändert) | Eintrag als stale markieren |
| Referenced Issue/PR in `source_refs` ist geschlossen/merged | Confidence reduzieren; ggf. Supersede anlegen |
| `superseded_by` ist gesetzt | Stale; Endknoten der Kette lesen |

**Stale-Memory-Regeln**:
- Stale Memory darf nicht als aktuelle Wahrheit an Downstream-Entscheidungen weitergegeben werden.
- Stale Memory muss als `unverified` oder `stale` markiert werden, bevor es in einem Briefing erscheint.
- Stale Memory wird nicht automatisch gelöscht; es verbleibt im Audit-Trail.

---

## 9. Rules gegen Unscoped Global Memory

| Verstoß | Beschreibung | Konsequenz |
|---|---|---|
| Leeres `scope` | Write ohne Agent-Scope-Identifier | Ablehnen; ungültig |
| Leerer `namespace` | Write ohne Namespace | Ablehnen; ungültig |
| Scope `global` oder `*` | Globaler unscoped Write | Verboten; kein Default-Global-Namespace |
| Cross-Scope-Write | Agent schreibt in fremden Scope | Ablehnen ohne Human-GO |
| Memory ohne `source_refs` | Kein Quellennachweis | Ablehnen; ungültig |
| Memory ohne `evidence_refs` | Kein provenance-backed Nachweis | Ablehnen; ungültig (ownership.yaml: `missing_source_hash`) |

---

## 10. Abgrenzung: `agent_memory` vs. `shared_memory`

Diese Abgrenzung basiert auf `infrastructure/config/surrealdb/ownership.yaml` und
`docs/surrealdb/data-ownership-matrix.md`.

| Dimension | `agent_memory` | `shared_memory` |
|---|---|---|
| **Canonical Source** | SurrealDB (primary) | SurrealDB (primary) |
| **SurrealDB Role** | `primary_scoped` | `primary_scoped` |
| **Writer** | Agents (per-agent scoped) | Agents (scoped) |
| **Reader** | Agents (per-agent scoped) | Agents (cross-agent) |
| **Scope** | `agent_id` + `namespace` | `namespace` + TTL |
| **Lebensdauer** | Mittelfristig bis langfristig; audit-trailed | Kürzer; leichter |
| **Audit-Trail** | Pflicht: source-hash-backed evidence refs | Optional; lighter |
| **Isolation** | Per-Agent — kein Cross-Agent-Write | Cross-Agent-Interchange erlaubt |
| **Typische Nutzung** | Langfristige Agent-Erfahrungen, Semantic/Procedural Memory | Session-Koordination zwischen Agenten |

**Abgrenzungsregel**: Wenn ein Memory-Eintrag für einen spezifischen Agenten dauerhaft
evidence-trailed sein soll, gehört er in `agent_memory`. Wenn er kurzlebig zwischen
mehreren Agenten ausgetauscht werden soll, gehört er in `shared_memory`.

Die genaue technologische Verzahnung zwischen `agent_memory` und `shared_memory` ist aktuell
noch nicht final spezifiziert (siehe `context-intelligence-system.md` Abschnitt 6).

---

## 11. Guardrails

| # | Guardrail | Begründung |
|---|---|---|
| M1 | Memory ist Hinweis, keine Wahrheit | Memory kann stale oder inaccurate sein; Entscheidungen müssen auf Evidence basieren |
| M2 | Keine Runtime-Entscheidung aus Memory ableiten | Memory kann nicht die Rolle von Live-State-Quellen (Postgres, Redis) übernehmen |
| M3 | Keine Secrets in Memory | API-Keys, Passwörter, Credentials gehören nicht in Memory-Felder |
| M4 | Kein Trading-State in Memory | Orders, Positions, Fills, Balances, Live-Risk gehören nicht in CIS-Memory |
| M5 | Kein unscoped global write | Kein Agent darf ohne Scope und Namespace schreiben |
| M6 | Kein Memory ohne Quelle | `source_refs` ist Pflicht; sourceless Memory ist ungültig |
| M7 | Human-GO für Scope-Änderungen | Neue Scope-Strukturen und Cross-Scope-Writes erfordern Human-GO |
| M8 | Stale Memory kennzeichnen | Stale Memory muss sichtbar sein, bevor es an Downstream weitergegeben wird |
| M9 | Superseded Memory nicht löschen | Audit-Trail muss erhalten bleiben |
| M10 | Keine LR-/Live-/Echtgeld-Ableitung aus Memory | Memory-Inhalte über LR-Status o. ä. ersetzen nie das LR-SSOT |

---

## 12. Review gegen `ownership.yaml`

Review-Ergebnis (2026-05-07):

| Domain in `ownership.yaml` | Relevant für dieses Doc | Befund |
|---|---|---|
| `agent_memory` | ✅ Primär | Vorhanden: `primary_scoped`, `agents` als Writer/Reader, Hinweis auf `agent_id + namespace + TTL`, Abgrenzung zu `shared_memory`. **Konsistent.** |
| `shared_memory` | ✅ Abgrenzung | Vorhanden: `primary_scoped`, `agents_scoped` als Writer, Cross-Agent-Interchange, Hinweis auf `Distinct from agent_memory`. **Konsistent.** |
| `context_intelligence` | Referenz | `mirror_read_only`, Context Indexer als Writer. Kein direkter Agent-Write. **Keine Konflikt.** |

Befund: `ownership.yaml` ist konsistent mit diesem Memory-Model-Doc.

---

## Quellen / Provenance

| Quelle | Typ | Status |
|---|---|---|
| `infrastructure/surrealdb/context_intelligence_v0.surql` | Schema Draft | PRESENT |
| `infrastructure/config/surrealdb/ownership.yaml` | Ownership YAML | PRESENT |
| `docs/surrealdb/context-intelligence-system.md` | Architektur | PRESENT |
| `docs/surrealdb/data-ownership-matrix.md` | Ownership Narrative | PRESENT |
| `docs/surrealdb/context-core-schema-v1.md` | Schema Narrative | PRESENT |
| Issue #1983 | Authority | OPEN |
| Issue #1981 | Dependency | OPEN |
| Epic #1976 | Parent | OPEN |
