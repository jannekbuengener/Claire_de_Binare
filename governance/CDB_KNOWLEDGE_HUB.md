# CDB_KNOWLEDGE_HUB – Shared Decisions & Agent Handoffs (v1.0)

Date: 2025-12-12  
Status: Active, Governance-aligned

---

## 0. Zweck

Der CDB_KNOWLEDGE_HUB ist der **zentrale, versionierte Notiz- und Decision-Hub** für alle KI-Sessions
im Projekt *Claire de Binare* (CDB).

Er ist ausdrücklich **kein**:
- Governance-Dokument,
- Memory-Interface,
- Log aller Roh-Outputs.

Sondern ein schlanker, stabiler Ort für:
- wichtige Entscheidungen,
- Agent-Handoffs (ToDos zwischen Agenten/Modellen),
- kurze strukturierte Session-Notizen.

Alle Einträge müssen so geschrieben sein, dass sie für spätere Sessions verständlich und nachvollziehbar sind.

---

## 1. Ground Rules

1. **Schreibrechte**
   - KI schreibt nur über explizit freigegebene Sessions (Claude, Gemini).
   - Copilot und Codex schreiben niemals direkt in diesen Hub.
   - Manuelle Edits durch den User sind jederzeit erlaubt.

2. **Governance & Memory**
   - Dieser Hub ist **kein Memory** im Sinne von `NEXUS.MEMORY.md`.
   - Dauerhafte Systemwahrheiten oder Invarianten werden ggf. später über NEXUS in echtes Memory überführt.
   - Keine automatischen Memory-Merges, keine Hidden-States.

3. **Inhaltliche Leitplanken**
   - Keine Secrets oder Zugangsdaten (ENV, Keys, Tokens, Passwörter).
   - Keine vollständigen Dumps von Logs oder Code – nur Referenzen.
   - Jede Notiz referenziert, wenn möglich, konkrete Artefakte (Dateipfade, Commits, Tickets).

4. **Stil**
   - Kurz, präzise, operativ.
   - „Wer → Was → Wo → Warum (optional).“
   - Deutsch oder Englisch – aber innerhalb eines Eintrags konsistent.

---

## 2. Agent Handoffs

> Offene Aufgaben, die ein Agent/Modell einem anderen hinterlässt.

Konvention:
- `OPEN`  = Aufgabe steht aus.
- `INPROGRESS` = gerade in Arbeit.
- `DONE`  = erledigt, mit Verweis auf Ergebnis.

Beispiel:

- [OPEN] Gemini → Claude: Governance-Review aus `CDB_GOVERNANCE.md` (Abschnitt 3.2) in Repo-Layout übertragen.
- [OPEN] Gemini → Codex: Migration-Skript von `/t1` nach `core/services/infrastructure/tests` vorbereiten.
- [INPROGRESS] Codex → Claude: Implementierung `scripts/cleanroom_migration.ps1` (siehe Branch `feature/cleanroom-migration`).
- [DONE] Claude → User: Repo-Struktur nach `CDB_REPO_STRUCTURE.md` aktualisiert; Validierungsbericht in `CDB_REPO_INDEX.md` ergänzt.

### 2.1 Aktuelle Handoffs

(Platzhalter, wird durch echte Sessions gefüllt.)

- [OPEN] – (noch keine Handoffs dokumentiert)

---

## 3. Decision Log

> Kurzprotokoll zentraler, projektweiter Entscheidungen.

Jeder Eintrag sollte enthalten:
- Datum,
- Beteiligte (User / Modelle),
- Kernentscheidung,
- Verweis auf Artefakte (Dateien, Commits, Tickets).

Beispiel:

- 2025-12-12 – User + Claude  
  **Entscheidung:** Canonical Repo-Layout auf `core/services/infrastructure/tests/governance` festgelegt.  
  **Referenzen:** `CDB_REPO_STRUCTURE.md` (v1), `CDB_REPO_INDEX.md` aktualisiert.

### 3.1 Aktuelle Entscheidungen

(Platzhalter, wird durch echte Sessions gefüllt.)

- 2025-12-12 – Initiale Anlage des CDB_KNOWLEDGE_HUB.md.  
  Zweck: Zentrale Drehscheibe für Entscheidungen und Agent-Handoffs.

---

## 4. Session Notes (Optional)

> Knappes Kontextprotokoll für zusammenhängende Arbeitsblöcke.

Strukturvorschlag:

```markdown
### Session 2025-12-12 – Repo-Initialisierung

- Ziel: Zielbild-Repo-Struktur definieren (Tier-1), Agentenrollen klären.
- Modelle: Claude (Session Lead), Gemini (Audit).
- Ergebnis (Kurzfassung):
  - Repo-Layout nach `CDB_REPO_STRUCTURE.md` bestätigt.
  - Agenten-Files (CLAUDE, GEMINI, COPILOT, CODEX) in `/governance` verankert.
  - `NEXUS.MEMORY.md` als reines Memory-Interface definiert (kein Log).
- Offene Punkte:
  - Vollständige CI-/Test-Pipeline für neue Struktur.
  - Ausarbeitung von MCP, sobald Multi-Model-Betrieb aktiv wird.
```

---

## 5. Beziehung zu NEXUS.MEMORY und Governance

- `NEXUS.MEMORY.md` definiert, **was** als dauerhaftes Memory gelten darf und **wie** es geschrieben wird.
- `CDB_KNOWLEDGE_HUB.md` hält fest, **was in der Praxis entschieden und beauftragt wurde.**
- Governance-Dateien (z. B. `CDB_CONSTITUTION.md`, `CDB_GOVERNANCE.md`, `CDB_AGENT_POLICY.md`) bleiben die einzige Quelle für Regeln.

Wenn ein Eintrag aus diesem Hub langfristig relevant wird, kann er später – nach expliziter User-Freigabe – als **Memory-Kandidat** markiert und über NEXUS in echtes System-Memory überführt werden.

Bis dahin gilt:
> „Alles im Hub ist wichtig – aber nichts davon ist automatisch Memory.“
