# Control Cockpit #1445 Rebaseline — 2026-05-13

## Zweck

#1445 bleibt dauerhaftes operatives Cockpit und bestehender Workflow-Sink.

Diese Datei trennt aktuelle operative Wahrheit von historischer Kommentar-Telemetrie
und ersetzt die alte Startregel „neuesten Wochenkommentar lesen".

Repo-backed. Versioniert. Schlägt Kommentarhistorie.

## Live-Stand zum Rebaseline-Zeitpunkt

| Feld | Wert |
|---|---|
| Issue | #1445 |
| Title | `[CONTROL] Claire de Binare — Operatives Cockpit (dauerhaft offen)` |
| State | OPEN |
| URL | https://github.com/jannekbuengener/Claire_de_Binare/issues/1445 |
| Updated at | 2026-05-12T07:19:50Z |
| Kommentaranzahl | 142 |
| Autoren | github-actions: 103 / jannekbuengener: 39 |
| Zeitraum | 2026-04-06 bis 2026-05-12 |

## Produktentscheidung

- Kein neues Cockpit-Issue.
- Kein Workflow-Retargeting.
- Keine Änderung von `CONTROL_ISSUE_NUMBER = 1445`.
- Keine Änderung am Posting-Verhalten der Automation-Scripts.

#1445 bleibt:

- operativer Einstiegspunkt für Mensch und KI
- Workflow-Sink für Post-Merge, Daily-Delta, Weekly-Hygiene
- Ledger/Telemetry-Oberfläche

Die Leseregel wird geändert.

## Aktuelle operative Wahrheit

GitHub live und Repo live schlagen Kommentarhistorie.

### Primäre SSOTs

| Rang | Datei | Zuständigkeit |
|---:|---|---|
| 1 | `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` | LR-Verdikt; einzige Echtgeld-Go/No-Go-Quelle |
| 2 | `docs/runbooks/CONTROL_REGISTER.md` | Board-Stage, Operating-Focus |
| 3 | `CURRENT_STATUS.md` | Repo-/Engineering-Stand, Session-Ledger |
| 4 | `AGENTS.md` + `agents/AGENTS.md` | Agent-Registry, Skill-Surface |
| 5 | `knowledge/runbooks/CDB_CONTROL_BOARD_RUNBOOK.md` | Stage-Mapping, Board-Regeln |

### Live-Regeln

- GitHub live schlägt alte Kommentare. Immer via `gh issue view` oder MCP prüfen.
- Repo live schlägt Erinnerung. Dateien aus dem aktuellen Repo-Stand lesen.
- `CURRENT_STATUS.md` ist Ledger, nicht operative Live-Wahrheit.
- LR-SSOT ist ausschließlich `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`.
- Board-Stage `trade-capable` ist orthogonal zum LR-Verdikt.
- LR bleibt NO-GO.
- Board-Stage autorisiert kein Live-/Echtgeld-Go.

## Kommentar-Klassifikation

| Klasse | Anzahl | Bewertung |
|---|---:|---|
| `automation_telemetry` gesamt | 103 | Ledger/Signal; kein automatischer Handlungsauftrag |
| `cdb-post-merge-followup` | 76 | Bot; bei Bedarf gezielt nachschlagen |
| `cdb-daily-delta` | 19 | Bot; bei Bedarf gezielt nachschlagen |
| `cdb-weekly-hygiene` | 8 | Bot; bei Bedarf gezielt nachschlagen |
| `human_mixed` | 39 | Historische Operator-Entscheide, Snapshots, Statusnotizen |

Kein Kommentar darf als automatischer Handlungsauftrag gelesen werden.

Jeder Handlungsauftrag erfordert Live-Verifikation via GitHub API, `gh` CLI oder CDB-MCP.

## Noch relevante historische Anker aus #1445-Kommentaren

Diese Inhalte sind bereits in Repo/PRs/SSOTs verankert. Kommentare sind Ledger-Referenz, kein Live-Stand.

| Datum | Inhalt | Einordnung |
|---|---|---|
| 2026-05-03 | Discovery-Surface-Drift-Fix PR #2275 | Historisch/repo-verankert |
| 2026-04-24 | ARVP Product Intent PR #1926 | Historisch/repo-verankert |
| 2026-04-20 | Replay Smoke PASS Run 24693431243 | Historischer Replay-Stand; kein LR-Go |
| 2026-04-20 | LR-021 Deterministic Replay Stack PRs #1808/#1810 | Historisch/repo-verankert |
| 2026-04-19 | Cockpit-Triage: kein Reset, #1725 parked | Historische Entscheidung; live prüfen bei Security-Scope |
| 2026-04-19 | Human-Dismiss Trivy Alert #2888 | Auditierbare historische Security-Entscheidung |
| 2026-04-19 | Security-Snapshot: Trivy 609 open, Grafana 121 | Historisch; nicht Live-Wahrheit |
| 2026-04-19 | PRs #1767/#1768 Prometheus/Redis | Historisch/repo-verankert |

## Watch-only

| Item | Einordnung |
|---|---|
| Replay Smoke `gate_status=FAIL` intern aus Run 24693431243 | Historisch; nicht LR-Go; live prüfen, wenn Replay-Scope aktiv wird |
| #1725 upstream-blocked / parked | Nur live prüfen, wenn Security-Scope wieder aktiv wird |
| #1905 parked/active label drift | Bot-Finding; kein automatischer Handlungsauftrag |
| Weekly-Hygiene W19 Doppelpost | Möglicher Script-Bug; kein Blocker |

## Repo-Referenzen auf #1445

Script-Konstanten bleiben bewusst unverändert:

```python
CONTROL_ISSUE_NUMBER = 1445
```

Betroffene Dateien:

- `.github/scripts/post_merge_followup_scanner.py`
- `.github/scripts/daily_delta_triage.py`
- `.github/scripts/weekly_control_hygiene_classifier.py`

Runbooks, README und Workflow-Register referenzieren #1445 weiterhin als Cockpit.

## Agentenregel ab Rebaseline

Diese Regel ersetzt „neuesten Wochenkommentar lesen".

1. `AGENTS.md` lesen.
2. `agents/AGENTS.md` lesen.
3. Falls OpenCode: `agents/OPEN_CODE_AGENTS.md` lesen.
4. Komplette Read Order aus `agents/AGENTS.md` abarbeiten.
5. #1445 Body lesen.
6. Diese Rebaseline-Datei lesen.
7. GitHub live ziehen:
   - `gh issue view 1445 --json state,updatedAt`
   - offene Issues mit `prio:must` und `prio:should`
   - offene PRs
   - konkret referenzierte Issues/PRs live prüfen
8. Alte #1445-Kommentare nicht automatisch als Live-Wahrheit lesen.
9. Kommentare nur gezielt suchen, wenn konkrete historische Evidenz benötigt wird.
10. Bei Unsicherheit über Datum, Fokus oder Priorität stoppen.

## Monatlicher Audit

Der monatliche Audit bleibt Pflicht.

Bis zur separaten Body-Rebaseline bleibt das Audit-Template im #1445-Issue-Body die operative Vorlage.

Falls der #1445-Body später gekürzt wird, muss das vollständige Audit-Template entweder in dieser Datei
ergänzt oder in einem klar referenzierten Runbook erhalten bleiben. Kein Body-Update darf das
Audit-Template ersatzlos entfernen.

## Nicht-Ziele

- Kein neues Issue.
- Kein Retargeting.
- Kein Kommentar-Löschen oder -Verbergen.
- Keine Änderung am Workflow-Schreibverhalten.
- Kein Live-/LR-/Echtgeld-Go.

## Restunsicherheiten

- Kommentarflut wächst technisch weiter. Lesbarkeit wird über Body + diese Rebaseline-Datei gelöst,
  nicht über Kommentarvolumen.
- Weekly-Hygiene W19 Doppelpost kann separat geprüft werden, wenn relevant.
- Falls Kommentarpolitik-Änderung später gewünscht ist: separater Slice, nicht mit dieser Rebaseline mischen.

## Status

`cockpit-rebaseline-archived`
