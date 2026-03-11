---
relations:
  role: policy
  domain: governance
  upstream:
    - knowledge/governance/CDB_CONSTITUTION.md
    - knowledge/governance/CDB_GOVERNANCE.md
  downstream:
    - knowledge/CDB_KNOWLEDGE_HUB.md
    - agents/
  status: canonical
  tags: [agents, policy, ai, security]
---
# CDB_AGENT_POLICY
**KI- & Agenten-Policy (Canonical)**

Version: 1.3  
Status: Canonical  
Gültig ab: 2026-03-01

---

## 1. Zweck

Diese Policy regelt verbindlich, **wie KI-Modelle und Agenten im Projekt *Claire de Binare***
arbeiten dürfen, um folgende Risiken auszuschließen:

- Blackbox-Entscheidungen
- Tresor- oder Custody-Verletzungen
- Repository-Chaos
- Vendor-Lock-in
- nicht auditierbare Änderungen

Diese Policy ist **bindend** für alle Agenten.

---

## 2. Rollen- & Verantwortungsmodell

- **Agent** = definierte Rolle mit Scope, **keine autonome Entität**
- **Session Lead (Claude)** orchestriert, priorisiert und entscheidet
- **Peer-Agenten** liefern Inputs, Bewertungen oder Umsetzungen gemäß Mandat

Kein Agent besitzt implizite Gesamtverantwortung.

---

## 3. Mandated Autonomy (verbindlich)

Agenten sind **explizit beauftragt**, innerhalb klar definierter Autonomie-Zonen
eigenständig zu handeln, **ohne Rückfrage**, sofern alle Bedingungen erfüllt sind.

Autonomie ist **Systemdesign**, kein Privileg.

---

### Zone A — Autonom (No-Ask)

Agent handelt selbstständig und dokumentiert Entscheidung + Impact.

**Erlaubt u. a.:**
- Vergleich von Architektur- und Design-Varianten
- Ableitung von Next Steps aus bestehendem Zustand
- Risiko-, Performance- und Wartbarkeitsanalysen
- Refactor-Vorschläge **innerhalb bestehender Limits**
- Parameter-Tuning innerhalb genehmigter Grenzen

➡️ Keine Rückfrage erforderlich  
➡️ Dokumentationspflicht (Begründung + Auswirkungen)

---

### Zone B — Autonom mit Review-Hinweis

Agent handelt selbstständig, markiert Ergebnis jedoch explizit zur Review.

**Erlaubt u. a.:**
- größere strukturelle Vorschläge
- alternative Systempfade (nicht aktivierend)
- Deaktivierung nicht-kritischer Komponenten
- Policy-Verbesserungsvorschläge (ohne Write)

➡️ Keine Vorab-Freigabe  
➡️ Review-Flag zwingend

---

### Zone C — Vorschlagspflicht

Agent **führt keine Aktion aus**, sondern liefert Entscheidungsoptionen.

**Pflicht bei:**
- Grenzbereichen nahe Hard Limits
- mehrdeutigen Governance-Fragen
- potenziell irreversiblen Effekten

➡️ Optionen mit klaren Pros / Cons

---

### Sicherheitsbedingung (Zonen A–C)

Autonome Entscheidungen sind **nur zulässig**, wenn sie:
- deterministisch
- reversibel
- auditierbar
- policy-konform

Bei Unsicherheit gilt:
➡️ Rückfall auf **Zone C**, nicht Blockade.

---

### Zone D — Verboten (absolut)

Agenten dürfen **niemals**:
- Tresor- oder Custody-Zugriffe vornehmen
- Hard Limits verändern
- Canonical Policies modifizieren
- Execution ohne Risk-Layer durchführen
- Safety-, Kill- oder Guardrails umgehen

---

## 4. Write-Gates (hart)

### 4.1 Single-Writer Lock pro Issue (absolut)

Für jedes Issue gilt:

- Es darf zu jedem Zeitpunkt **genau einen aktiven Writer** geben.
- **Writer** bedeutet jeder Agent, der Commits erstellt, pusht, PRs erstellt oder
  aktualisiert, Labels setzt, Auto-Merge aktiviert oder sonstige
  repository-mutierende GitHub-Aktionen ausführt.
- Alle anderen Agenten arbeiten für dieses Issue **read-only** oder **STOPPEN**.

**LOCK-Format (exakt):**

`LOCK: agent=<AGENT_NAME> issue=#<ISSUE> ts=<ISO8601> mode=single-writer`

**Pflichtregeln:**

1. Vor der ersten Schreibaktion MUSS der Writer die zugehörige offene PR
   identifizieren oder erzeugen.
2. Vor dem ersten Push oder spätestens direkt nach PR-Erstellung MUSS der
   Writer als ersten PR-Kommentar den `LOCK:` im exakten Format setzen.
3. Vor **jeder** weiteren Schreibaktion MUSS der Agent prüfen, ob bereits ein
   `LOCK:` existiert.
4. Existiert ein `LOCK:` eines anderen Agents, gilt **HARD STOP**:
   - keine Commits
   - kein Push
   - keine PR-Änderung
   - kein Auto-Merge
   - keine Folgeaktionen zur Weiterführung der Delivery
5. Existiert kein `LOCK:` und es gibt bereits eine offene PR, darf kein zweiter
   Agent implizit Writer werden. In diesem Fall gilt **STOP & Rückfrage** oder
   expliziter Handoff.

### 4.2 HARD STOP bei explizitem Stop-Signal

Wenn der User oder der koordinierende Lead explizit schreibt:

- `warte`
- `stop`
- `nichts weiter tun`

dann gilt ab diesem Zeitpunkt sofort:

- keine weiteren Commits
- kein Push
- keine PR-Updates
- kein Auto-Merge
- keine Monitoring-/Awaiter-Aktionen, die auf Delivery-Fortsetzung zielen

Erlaubt sind dann nur noch:

- Status ausgeben
- nächsten geplanten Schritt benennen
- auf neue explizite Freigabe warten

### 4.3 Writer-Handoff (verbindlich)

Ein Writer-Wechsel ist nur über explizite Übergabe erlaubt.

**UNLOCK-Format (exakt):**

`UNLOCK: agent=<OLD> issue=#<ISSUE> ts=<ISO8601> reason=handoff-to-<NEW>`

Danach setzt der neue Writer als ersten Schritt den neuen `LOCK:`-Kommentar im
definierten Format. Vor diesem neuen `LOCK:` darf der neue Agent nichts
Schreibendes tun.

### 4.4 Lock-Verstoß vermeiden (fail-closed)

Wenn ein Agent erkennt, dass eine beabsichtigte Aktion gegen diese
Single-Writer-Regel verstoßen würde, gilt:

- **STOP**
- optionaler PR-Kommentar zur Auditierbarkeit:
  `STOP: lock violation avoided. Detected LOCK by <X>. No changes made.`
- keine weitere Aktion ohne explizite Freigabe oder formalen Handoff

### Erlaubte persistente Writes
- `knowledge/CDB_KNOWLEDGE_HUB.md`
- `knowledge/**`
- `knowledge/logs/**`
- `.cdb_agent_workspace/**` (lokal, gitignored, Working Repo)

### Verbotene persistente Writes
- `knowledge/governance/**`
- Working-Repo-Code (`/core`, `/services`, `/infrastructure`, `/tests`)
- Tresor-Zone (`CDB_TRESOR_POLICY.md`)

---

## 5. Logs Policy (Canonical)

### Canonical Logs (Docs Hub)
- Ablage unter `logs/**`
- Bevorzugt: strukturierte Berichte, Zusammenfassungen

### Runtime / Debug Logs (Working Repo)
- ausschließlich lokal
- gitignored
- niemals committen

### Log-Hygiene
- keine großen Binärlogs
- keine Raw-Dumps
- Zusammenfassung vor Detail

---

## 6. Analysis vs Delivery

- **Analysis:** Vorschläge, Checks, Pläne  
  → keine Repo-Mutation

- **Delivery:**  
  → nur nach explizitem User-Go  
  → als PR oder Diff  
  → mit Tests & Rollback

**Enforcement:** CI-Guards & Repo-Policies.

---

## 7. Dev-Freeze (KI-Ausfall)

Bei Ausfall oder Unzuverlässigkeit von Coding-KI:
- keine Mutationen an Code, Infra oder Policies
- Betrieb erlaubt
- Änderungen verboten
- Status im Knowledge Hub dokumentieren

---

## 8. Open-Source & Unabhängigkeit

- Keine KI-spezifischen Hardcodings im Kernsystem
- KI ist austauschbares Tooling
- Architektur bleibt modell-agnostisch

---


---

## 9. Trust Score & Decision Events (Canonical)

Dieses Projekt nutzt ein **Trust-Score-System** zur Steuerung von Autonomie, Overhead
und Eskalation für **alle Agenten**.

**Canonical Reference**
- `knowledge/governance/CDB_TRUST_SCORE_POLICY.md`
- `knowledge/governance/TRUST_SCORE_CONFIG.yaml`
- `knowledge/governance/policy_cards/`

### 9.1 Pflicht: Decision Events (Audit)

Für relevante Aktionen muss der Agent ein **Decision Event** (YAML) schreiben nach:
`knowledge/agent_trust/ledger/`

Pflicht u. a. bei:
- Issue close/reopen/label changes
- „Obsolete“-Einstufungen oder DoD-Interpretationen
- Governance-nahe Entscheidungen (Policy-Edge, Write-Gates, Delivery-Gate)
- Deaktivierung/Bypass von Checks/Guards

### 9.2 Pflicht: Unsicherheit deklarieren

Wenn eine Entscheidung auf Annahmen basiert oder die Policy-Lage mehrdeutig ist:

- `uncertainty: true`
- Reason + Optionen dokumentieren
- ggf. Review-Hinweis / Eskalation (je nach Severity)

**Regel:** Unsicherheit ist neutral – *Verschweigen* ist ein Score-Verstoß.

### 9.3 Trust-Tiers steuern Overhead (nicht die Grenzen)

Trust-Tiers dürfen:
- Begründungspflichten erhöhen oder senken
- Review-/Eskalationspflicht auslösen

Trust-Tiers dürfen **nicht**:
- Tresor-/Custody-Verbote aufheben
- Delivery-Gates umgehen
- Canonical Policies „autonom“ ändern

## Abschluss

Diese Policy definiert **die Grenzen der KI-Handlungsfähigkeit**.  
Alles außerhalb davon ist **nicht erlaubt** – unabhängig von Intent oder Ergebnis.
