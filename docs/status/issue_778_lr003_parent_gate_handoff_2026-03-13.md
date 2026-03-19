# Issue #778 Handoff - LR-003 Parent Gate Tightening

Status: analysis / handoff only
Date: 2026-03-13
Audience: Claude Code

## Ist-Analyse

- `#778` ist als Parent-Gate-Anchor offen, aber sein aktueller Tracker-Text ist breiter als der heute belastbar repo-seitig belegte Scope.
- Der wichtigste Naming-Drift ist explizit belegt:
  - `docs/live-readiness/LR-003-STATE.yaml` und `docs/live-readiness/LR-003-EVIDENCE.md` fuehren `LR-003` weiterhin als historischen `P0 Contract Drift Guard`.
  - `#778` verwendet `LR-003` dagegen fuer `Kill-Switch + Limit Controls Drill Test`.
  - `docs/governance/evidence/ISSUE-778-governance-gate-human-recovery-limits.md` benennt diesen Drift bereits offen und weicht deshalb bewusst auf issue-spezifische Evidence aus, statt die alte Live-Readiness-SSOT umzuschreiben.
- Repo-seitig bereits belastbar abgedeckt fuer `#778` ist nur der schmale, issue-spezifische Mechanik-/Drill-Slice:
  - Risk-seitige Kill-Switch-Gate-Logik
  - Execution-seitige defense-in-depth Blockierung
  - deterministische Limit-Control-Entscheidungen ueber bestehende Vektor-Fixtures
  - repo-lokaler, non-live Drill-Runner `scripts/drills/lr003_kill_switch_limit_controls_runner.py`
  - zugehoerige Tests `tests/unit/scripts/test_lr003_kill_switch_limit_controls_runner.py`
  - issue-spezifische Governance-Evidence unter `docs/governance/evidence/ISSUE-778-governance-gate-human-recovery-limits.md`
- Das Workspace enthaelt lokale Drill-Artefakte unter `reports/drills/lr003/`:
  - `lr003_summary.json`
  - `lr003_report.md`
  - `lr003_verdict.md`
  Diese Artefakte sind aktuell lokal vorhanden, aber im Arbeitsbaum untracked. Sie tauchen deshalb weder als committete Repo-Evidence noch als Run-URLs im Governance-Report auf.
- Der Governance-Core-Statusbericht bestaetigt die aktuelle Parent-Lage:
  - `#778` hat `PR 1 / Doc 1 / Run 0`
  - `#661` hat ebenfalls `Run 0`
  - der Bericht empfiehlt fuer operative Gates explizit das Nachpflegen belastbarer Run-URLs
- Die `#778`-Issue-Beschreibung selbst ist heute zu breit fuer das repo-backed Beweisniveau:
  - behauptet Kill-Switch stoppt Order-Submissions `<5 Sekunden`
  - fordert dokumentierten Drill mit Timestamps
  - fordert getestete Recovery-Prozedur
  - fordert definierten Human-Gate-Prozess
  Fuer diese Punkte gibt es im heutigen `#778`-Evidence-Slice keine belastbare, kanonische Repo-Evidence.
- Die Parent-/Child-Mapping im Tracker ist teilweise falsch oder veraltet:
  - `#661` als Child-Evidence ist plausibel und aktuell
  - `#658` ist nachweislich Branch-Protection-Reapply und damit fachlich kein Kill-Switch-/Limit-Control-Child
  - `#762` und `#748` sind policy-/contract-nahe, aber heute bereits geschlossen und eher historischer/upstream Kontext als aktive Child-Arbeit fuer `#778`
- `#661` wurde bereits schmal vorbereitet:
  - Operator-Drill-Runbook und Skeleton existieren
  - der Handoff fuer `#661` grenzt den Scope auf realen Alert-Trigger plus kanonische Kill-Switch-/Order-Flow-Verifikation samt Evidence-Pack ein
  - `#661` ist damit klar Child-Evidence/operativer Drill, nicht der Ort fuer Parent-Gate-Neudefinition
- Zusaetzliche Drift-Spur:
  - `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` behandelt `#778` weiter als offenes `LR-003`-Tracker-Item und fordert Tracker-Reconciliation.
  - `docs/operations/P5_CANARY_EXECUTION_CHECKLIST.md` referenziert fuer `LR-003` weiter die historische Contract-Drift-Evidence.
  Diese Dokumente zeigen den Drift, sollten aber nicht im Scope von `#778` bereinigt werden.

## Minimaler Zielzustand fuer #778

- `#778` wird als schmaler Parent-Gate-Anchor beschrieben, nicht als Sammelbecken fuer alle denkbaren Kill-Switch-, Recovery-, Human-Gate- oder Runtime-Themen.
- Der Parent beschreibt nur den heute repo-backed Kern:
  - fail-closed Kill-Switch-Blockierung auf Risk-/Execution-Ebene
  - deterministische Limit-Control-Nachweise
  - issue-spezifische Governance-Evidence
  - offener Child-Evidence-Pfad fuer den echten Operator-Drill via `#661`
- `#778` bleibt offen bzw. explizit `PARTIAL/OPEN`, solange die operative Drill-Evidence aus `#661` nicht belastbar vorliegt oder solange der Parent noch unbewiesene Gate-Claims enthaelt.
- Der Parent sollte nicht mehr so tun, als waere er identisch mit der historischen `docs/live-readiness/LR-003-*`-SSOT. Stattdessen braucht er einen klaren Drift-Hinweis und issue-spezifische Evidence als bewussten Sonderpfad.
- Die Child- und Related-Mapping muessen gestrafft werden:
  - `#661` = aktives Child fuer operatorische Evidence
  - `#658` = aus dem Parent-Mapping entfernen
  - `#762` und `#748` hoechstens als historische/verwandte Kontexte belassen, nicht als laufende Child-Deliverables

## Parent-Gate vs Child-Work vs Evidence

### Parent-Gate (`#778`)

- Aufgabe: Gate-Anchor, der den aktuellen Nachweisstand der Kill-Switch-/Limit-Control-Faehigkeit zusammenfasst.
- Darf: Scope, aktuellen Beweisstand, offene Luecken, Child-Zuordnung und Gate-Verdict sauber dokumentieren.
- Darf nicht: selbst zum neuen Drill-Programm, Incident-System oder Runtime-Design werden.

### Child-Work

- `#661`:
  - operatorischer Drill-Track
  - realer Alert-Trigger
  - kanonische Kill-Switch-/Order-Flow-Verifikation
  - Timeline-/Evidence-Pack
- Nicht in `#778` absorbieren:
  - `#785`
  - `#659`
  - Runtime-/Compose-/Legacy-Themen `#1139`, `#1142`, `#1145`, `#1146`
- `#658` ist kein Child fuer `#778`.
- `#762` und `#748` sind kein aktiver Rest-Scope fuer den Parent, sondern nur historischer/verwandter Technik-Kontext.

### Evidence

- Aktuelle Parent-Evidence:
  - `docs/governance/evidence/ISSUE-778-governance-gate-human-recovery-limits.md`
  - repo-lokaler LR-003 Drill-Runner plus Tests
  - lokale, derzeit untracked Artefakte unter `reports/drills/lr003/`
- Offene Evidence:
  - keine kanonische Run-URL im Parent
  - keine belastbare repo-publizierte Operator-Drill-Evidence
  - keine repo-backed Response-Time-, Recovery- oder Human-Gate-Beweise fuer die im Issue-Text behaupteten Kriterien
- Historische `docs/live-readiness/LR-003-*`-Artefakte bleiben davon getrennt.

## Konkrete Dateiliste fuer Claude Code

- Sollte angefasst werden:
  - `docs/governance/evidence/ISSUE-778-governance-gate-human-recovery-limits.md`
- Sollte nicht als Teil von `#778` umgebaut werden, nur als Referenz dienen:
  - `docs/status/issue_661_operator_drill_handoff_2026-03-13.md`
  - `scripts/drills/lr003_kill_switch_limit_controls_runner.py`
  - `tests/unit/scripts/test_lr003_kill_switch_limit_controls_runner.py`
  - `reports/drills/lr003/lr003_summary.json`
  - `reports/drills/lr003/lr003_report.md`
  - `tools/test_pack/runbooks/kill_switch_checklist.md`
  - `tools/test_pack/tools/drills/trigger-operator-drill.ps1`
  - `docs/live-readiness/LR-003-STATE.yaml`
  - `docs/live-readiness/LR-003-EVIDENCE.md`
  - `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
  - `docs/operations/P5_CANARY_EXECUTION_CHECKLIST.md`
- Zusaetzlich ausserhalb des Repo-Dateisets:
  - GitHub-Issue `#778` selbst: Body/Kommentar-Metadaten sollten auf den gestrafften Parent-Scope gezogen werden

## Risiken / Annahmen / offene Punkte

- Solange `#778` weiter das Label `LR-003` traegt, bleibt Naming-Drift zur historischen Live-Readiness-SSOT bestehen. Das ist tolerierbar, solange der Drift explizit dokumentiert wird und keine SSOT-Umschreibung fuer dieses Issue gestartet wird.
- Die lokalen `reports/drills/lr003/*`-Artefakte sind heute keine kanonische Repo-/Issue-Evidence. Wenn Claude Code sie im Parent referenziert, muss ihr Status als lokale/untracked Supporting Evidence klar benannt werden.
- `#661` ist fuer den echten Operator-Drill vorbereitet, aber noch kein repo-backed Abschluss. Parent und Child duerfen deshalb nicht denselben offenen Scope doppelt beanspruchen.
- Der aktuelle `#778`-Text verspricht Response-Time, Recovery und Human-Gate. Wenn diese Claims im Parent bleiben, ohne dass belastbare Evidence verlinkt wird, bleibt das Gate inhaltlich ueberdehnt.
- Ein zu aggressiver Cleanup von `docs/live-readiness/*` oder `docs/operations/*` wuerde Scope-Drift ausloesen und historische Governance-Spuren ueberschreiben.

## Klare Nicht-Ziele

- Kein neues Drill-System bauen.
- Kein neues Incident- oder Recovery-System bauen.
- Kein Monitoring- oder Runtime-Rewrite.
- Kein Umbau der historischen `docs/live-readiness/LR-003-*`-SSOT.
- Kein Cleanup von `P5_CANARY_EXECUTION_CHECKLIST.md`, `LR-AUDIT-STATUS-2026-03-05.md` oder anderen Folge-Dokumenten als Teil von `#778`.
- Kein Wiederaufmachen von `#658`, `#762`, `#748` oder Runtime-/Compose-Folgethemen.
- Kein Nachziehen anderer Issues oder Programme in den Parent.

## Claude-Code-Handoff

### Ziel

`#778` als Parent-Gate-Anchor entschlacken und auf den realen repo-backed Rest-Scope reduzieren: bestaetigte Kill-Switch-/Limit-Control-Mechanik plus issue-spezifische Evidence sauber dokumentieren, falsche Child-Mappings entfernen, offene operatorische Evidence klar an `#661` auslagern.

### Betroffene Dateien

- `docs/governance/evidence/ISSUE-778-governance-gate-human-recovery-limits.md`
- GitHub-Issue `#778` Body/Kommentar

### Minimale Aenderungen

- `docs/governance/evidence/ISSUE-778-governance-gate-human-recovery-limits.md`
  - als primaere Repo-Evidence fuer den Parent behalten
  - den bereits vorhandenen Drift-Hinweis explizit staerken
  - klar trennen zwischen:
    - heute belegtem Mechanik-/Drill-Slice
    - offener operatorischer Evidence aus `#661`
    - nicht belegten Parent-Claims
  - falls lokale `reports/drills/lr003/*` referenziert werden, ihren nicht-kanonischen Status klar markieren
- GitHub-Issue `#778`
  - Parent-Text auf den minimalen Gate-Scope ziehen
  - falsches Child `#658` entfernen
  - `#661` als aktives Evidence-Child klar benennen
  - `#762`/`#748` allenfalls als Related Context, nicht als aktuelles Child-Work
  - Response-Time-/Recovery-/Human-Gate-Claims nur dann stehen lassen, wenn konkrete Evidence verlinkt wird; sonst als offen/gap markieren oder aus dem Parent entfernen
  - Gate-Verdict konservativ halten: `OPEN/PARTIAL`, bis die offene operatorische Evidence wirklich belastbar ist

### Validierung

- Repo-Seite:
  - `docs/governance/evidence/ISSUE-778-governance-gate-human-recovery-limits.md` muss nach der Anpassung eindeutig sagen, dass historische `LR-003-*`-SSOT nicht umgeschrieben wird
  - Der Parent darf nur repo-backed Claims als umgesetzt darstellen
  - `#661` muss als Child-Evidence klar abgegrenzt sein
- Tracker-Seite:
  - `#778` darf `#658` nicht mehr als Child/Mechanism fuehren
  - `#778` darf keine offenen Parent-Claims als bereits bewiesen darstellen
  - Kommentar/Body muessen denselben Scope wie die Repo-Evidence-Datei tragen
- Negativ-Validierung:
  - keine Aenderung an `docs/live-readiness/LR-003-STATE.yaml`
  - keine Aenderung an `docs/live-readiness/LR-003-EVIDENCE.md`
  - keine Aenderung an `tools/test_pack/*` als Teil dieses Parent-Cleanup

### Rollback / Sicherheitsgrenzen

- Rollback bleibt auf die Parent-Dokumentation und den Issue-Text begrenzt.
- Keine Aenderung an Kill-Switch- oder Limit-Control-Code.
- Keine Aenderung an Drill-Implementierungen.
- Keine Aenderung an Runtime-/Monitoring-/Compose-Strukturen.
- Wenn ein sauberer Parent-Text nur mit breiter Dokumenten-Reconciliation moeglich waere, STOP und den Drift explizit benennen statt Folgedokumente aufzureissen.
