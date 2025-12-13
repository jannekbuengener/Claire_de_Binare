# CDB_AGENT_POLICY
**KI-/Agenten-Regeln (Mini-Stack)**  
Version: 1.0.0 • Date: 2025-12-12 • Status: Canonical

---

## 1. Ziel
Regelt, wie KI-Modelle und Agent-Rollen im Projekt arbeiten dürfen, ohne:
- Blackbox-Risiko
- Tresor-Verletzung
- Repo-Chaos
- Vendor-Lock-In

---

## 2. Rollenlogik
- „Agent“ = Rolle/Scope, keine autonome Entität.
- Session Lead orchestriert; Peer-Modelle liefern Inputs.

---

## Mandated Autonomy (verbindlich)

Agenten sind **explizit beauftragt**, innerhalb definierter Autonomie-Zonen
eigenständig Entscheidungen zu treffen, **ohne Rückfrage**, solange alle
untenstehenden Bedingungen erfüllt sind.

Autonomie ist kein Privileg, sondern Teil des Systemdesigns.

---

### Autonomie-Zonen

**Zone A – Autonom (No-Ask)**  
Agent darf selbstständig handeln, dokumentiert aber seine Entscheidung.

Erlaubt sind u.a.:
- Architektur- und Design-Varianten vergleichen
- Refactor-Optionen vorschlagen
- Parameter-Tuning *innerhalb* bestehender Limits
- Risiko-, Performance- oder Wartbarkeitsanalysen
- Ableitung von Next-Steps aus bestehendem State

➡️ Keine Nachfrage erforderlich.  
➡️ Logging verpflichtend (Reason + Impact).

---

**Zone B – Autonom mit Review-Hinweis**  
Agent handelt selbstständig, markiert Ergebnis jedoch explizit zur späteren Review.

Erlaubt sind u.a.:
- größere strukturelle Vorschläge
- alternative Systempfade (ohne Aktivierung)
- Deaktivieren nicht-kritischer Komponenten
- Vorschläge zur Policy-Verbesserung (ohne Write)

➡️ Keine Vorab-Freigabe.  
➡️ Review-Flag erforderlich.

---

**Zone C – Vorschlagspflicht**  
Agent erstellt **keine Aktion**, sondern einen Vorschlag.

Pflicht bei:
- Grenzbereichen nahe Hard Limits
- Mehrdeutigen Governance-Interpretationen
- potenziell irreversiblen Entscheidungen

➡️ Klare Entscheidungsoptionen mit Pros/Cons.

---

### Sicherheitsbedingung (für alle Zonen A–C)

Autonome Entscheidungen sind nur zulässig, wenn sie:
- deterministisch sind
- reversibel sind
- auditierbar sind
- innerhalb der bestehenden Policy-Grenzen liegen

Bei Unsicherheit gilt:
➡️ Rückfall auf Zone C (Vorschlag), nicht Blockade.

---

**Zone D – Verboten**  
Unverändert:
- Tresor
- Hard Limits
- Canonical Policies
- Execution ohne Risk-Layer

---

### Beispielrollen
- system-architect
- risk-guardian
- infra-advisor
- rl-safety-officer

---

## 3. Write-Gates (hart)
KI darf persistent schreiben **nur** in:
- `CDB_KNOWLEDGE_HUB.md`
- `.cdb_agent_workspace/*` (lokal, gitignored)

KI darf **nicht** persistent schreiben in:
- `/core`, `/services`, `/infrastructure`, `/tests`
- `/governance/*`
- Tresor-Zone

---

## 4. Verbotene Aktionen (nicht verhandelbar)
KI/Agents dürfen niemals:
- Secrets / Keys / Custody anfassen
- Withdrawals oder Capital-Moves auslösen
- Hard Limits ändern
- Kill-Switch oder Safety umgehen
- Canonical Policies modifizieren
- Silent Changes durchführen

---

## 5. Analysis vs Delivery
- **Analysis:** Vorschläge, Pläne, Checks – keine Repo-Mutation
- **Delivery:** nur nach User-Go, nur als PR/Diff, mit Tests + Rollback

---

## 6. Dev-Freeze (KI-Ausfall)
Bei Ausfall vertrauenswürdiger Coding-KI:
- keine Änderungen an Code, Infra oder Policies
- Betrieb erlaubt, Mutation verboten
- Status im Knowledge Hub dokumentieren

---

## 7. Open-Source / Unabhängigkeit
- Keine KI-spezifischen Hardcodings im Kernsystem
- KI ist austauschbares Tooling
