# Context Intelligence — Agent Handoff Guide (Wave 7)

**Status**: Draft (Wave 7)
**Authority**: Issue #2040 / Parent #2034 / Epic #1976
**Scope**: Docs-only (kein Code, kein Schema, keine Runtime-Aenderung)

---

## 1. Zweck

Dieses Dokument ist das **verbindliche Handoff** fuer Agenten, die Context-Intelligence-Issues bearbeiten.
Es beschreibt Pflichtlektuere, erlaubte/verbote Aktionen, Live-Checks und Stop-Conditions.

Guardrail: Dieses Dokument autorisiert **kein Live-Go**, **kein Echtgeld-Go** und **keine** produktive SurrealDB-Aktivierung.

---

## 2. Wann MUSS ein Agent das lesen?

Ein Agent MUSS dieses Dokument lesen, bevor er:

- ein Issue in Epic #1976 / Parent #2034 startet
- Context-Intelligence-Dokumente unter `docs/surrealdb/` aendert
- ein Schema-Draft-Issue (#2037 oder Folge-Slices) bearbeitet
- PRs in Welle 7 (Issues #2034–#2043) erstellt oder merged

**STOPP**, wenn der Agent dieses Dokument nicht gelesen hat.

---

## 3. Einstiegspunkte (SSOT)

SSOT-Regel:

- **GitHub Issues/PRs** sind die Live-Wahrheit fuer Status.
- **Working Repo** ist Canon fuer Dateien.
- `CURRENT_STATUS.md` ist Ledger, nicht Live-Status.
- `docs/runbooks/CONTROL_REGISTER.md` ist Board-/Stage-SSOT.
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` ist LR-Go/No-Go-SSOT.

**DARF NICHT**:

- Board-Stage (`trade-capable`) als Live-Readiness-Go interpretieren.
- LR-Go/No-Go aus Stage ableiten.

---

## 4. Pflichtlektuere (Reihenfolge)

Der Agent MUSS vor jeder Mutation mindestens diese Pfade lesen:

1. `agents/AGENTS.md`
2. `knowledge/governance/CDB_AGENT_POLICY.md`
3. `CURRENT_STATUS.md` (nur als Ledger)
4. `docs/runbooks/CONTROL_REGISTER.md`
5. `docs/surrealdb/context-intelligence-system.md` (#2035)
6. `docs/surrealdb/context-intelligence-roadmap.md` (#2036)
7. `docs/surrealdb/context-ontology-v0.yaml` (#2038)
8. `docs/surrealdb/context-intelligence-validation.md` (#2039)

Wenn `agents/GEMINI.md` existiert, MUSS es ebenfalls gelesen werden.

---

## 5. Branch-/Worktree-Gate (Arbeitsmodus)

Regeln:

- Haupt-Working-Tree NICHT anfassen, wenn er nicht auf `main` ist.
- Pro Slice genau ein isolierter Worktree unter `.worktrees/`.
- Branch-Naming: `feat/<issue>-<short-slug>`.
- Worktree-Naming: `.worktrees/feat-<issue>-<short-slug>`.
- Basis ist immer `origin/main`.

Start-Gate (vor Beginn eines Slices):

- [ ] `git status -sb` im Haupt-Working-Tree (nur lesen)
- [ ] `git branch --show-current` im Haupt-Working-Tree (nur lesen)
- [ ] `git worktree list` im Haupt-Working-Tree (nur lesen)
- [ ] Ziel-Branch existiert nicht
- [ ] Ziel-Worktree-Pfad existiert nicht

**STOPP**, wenn Branch oder Worktree bereits existiert (keine Reparatur ohne Human-GO).

---

## 6. Issue-/PR-Live-Check (Pflicht)

Vor jeder Aenderung MUSS der Agent live pruefen:

- Issue state (OPEN/CLOSED)
- Parent/Epic state
- Dependencies state (merged/offen)
- vorhandene PRs (Nummer, Merge-Status)

Minimaler Live-Check (Beispiel):

```bash
gh issue view <ISSUE> --repo jannekbuengener/Claire_de_Binare
gh issue view 2034 --repo jannekbuengener/Claire_de_Binare
gh issue view 1976 --repo jannekbuengener/Claire_de_Binare
```

**STOPP**, wenn Live-Evidence fehlt oder widerspruechlich ist.

---

## 7. Evidence-Anforderungen

Alle Behauptungen ueber Status, Gates oder "fertig" MUESSEN auf Live-Evidence basieren.

Minimaler Evidence-Standard:

- PR/Issue-Links
- `gh pr view ...` / `gh issue view ...` Rohoutput (oder JSON-Auszug)
- `git status -sb` und `git diff` fuer Diff-Scope

**DARF NICHT**:

- Status aus statischen Docs ableiten.
- "merged" schreiben, wenn PR nicht gemergt ist.

---

## 8. Erlaubte Aktionen

Ein Agent DARF innerhalb eines Slice:

- genau die freigegebenen Datei(en) erstellen/aendern
- gezielt stagen (`git add <path>`, niemals `git add .`)
- committen, pushen, PR erstellen
- PR-Checks pruefen und bei slice-interner Ursache korrigieren
- PR-Branch mit `gh pr update-branch` aktualisieren
- nach gruener Gate-Lage normalen Squash-Merge versuchen

---

## 9. Verbotene Aktionen

Ein Agent DARF NICHT:

- Admin-Bypass oder Force-Push
- Rebase (egal ob lokal oder via GitHub)
- `git add .`
- Branch-Delete oder Worktree-Delete
- neue Issues erstellen oder Labels aendern
- Runtime umbauen oder produktive SurrealDB aktivieren
- Trading-State oder Secrets in Artefakte aufnehmen
- Board-Stage zu LR-Go mappen

---

## 10. Human-GO und Merge-Gate

Grundsatz:

- Agenten koennen PRs vorbereiten.
- Merge ist nur erlaubt, wenn GitHub nicht blockiert und alle Gates gruen sind.

Merge-Versuch ist nur erlaubt, wenn:

- `state = OPEN`
- `isDraft = false`
- `mergeStateStatus = CLEAN`
- keine failed/pending Checks
- Diff-Scope entspricht exakt dem Slice

**STOPP**, wenn GitHub Branch Protection (z. B. required formal review) den Merge blockiert.

---

## 11. Issue-Kommentar-Pflicht

Jeder Slice MUSS mindestens zwei Kommentare im Issue hinterlassen:

1. PR erstellt:
   - Datei(en), Branch, PR-Link, Validierung, Status `bereit fuer PR-Review / Merge-Gate`
2. Nach Merge:
   - Merge abgeschlossen, Diff-Scope, Checks, Guardrails, Status `gemergt / bereit fuer naechsten Slice`

Wenn Merge blockiert ist:

- Kommentar: `blockiert: formale Review/Approval erforderlich` (mit PR-Link und Rohoutput-Hinweis)

---

## 12. Stop-Bedingungen

Der Agent MUSS stoppen, wenn:

- Merge-Konflikt
- unklarer/fremder Diff
- Scope-Wachstum ueber den Slice hinaus
- rote Checks ohne klare slice-interne Ursache
- fehlende/widerspruechliche Live-Evidence
- Tool/Auth/Netzwerk-Blocker
- GitHub Branch Protection blockiert Merge

---

## 13. Umgang mit blockierten PRs

Wenn ein PR `BLOCKED` ist (z. B. required formal review):

- NICHT bypassen
- Issue mit Status und PR-Link kommentieren
- zum naechsten unabhaengigen Slice weitergehen

---

## 14. Umgang mit parallelen Agenten/Worktrees

- Worktrees anderer Agenten nicht anfassen.
- Unerwartete Aenderungen nicht zuruecksetzen.
- Bei Branch-/Worktree-Kollision: **STOPP** und Human-GO einholen.

---

## 15. Guardrails (Kurzliste)

- Kein Runtime-Umbau
- Keine produktive SurrealDB-Aktivierung
- Kein Trading-State
- Keine Secrets
- Kein Live-Go
- Kein Echtgeld-Go
- Kein Board-Stage-zu-LR-Go-Mapping
