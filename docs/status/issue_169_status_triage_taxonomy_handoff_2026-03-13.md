# Issue #169 Handoff - Status/Triage Taxonomy and Thin Issue-Progress Tracker

Status: analysis / handoff only
Date: 2026-03-13
Audience: Claude Code

## Ist-Analyse

- `#169` ist laut aktuellem Backlog-Audit weiter offen, aber nur mit reduziertem Scope als `status/triage taxonomy + optional thin issue-progress tracker`.
- Die offizielle Label-Taxonomie ist repo-seitig klar benannt:
  - `.github/LABELS.md`
  - `.github/workflows/labels.json`
  - dort sind als `status:*` heute nur `status:ready`, `status:blocked`, `status:in-review`, `status:wontfix` kanonisch beschrieben.
- Die operative Triage-/Board-Automation nutzt aber ein anderes Vokabular:
  - `.github/workflows/triage_guard.yml` arbeitet mit `TRIAGE_LABEL_NAME=triage:offen`
  - `.github/workflows/project_status_label_map.yml` und `.github/workflows/project_reconcile_daily.yml` mappen auf alte Status-Labels wie `status:idea`, `status:approved`, `status:in-progress`, `status:review`, `status:merged`, `status:descoped`, `status:rejected`
  - `.github/workflows/gemini-scheduled-triage.yml` sucht sogar `status/needs-triage`
- Die Runbook-/SOP-Doku spiegelt genau diese Drift:
  - `docs/runbooks/project_board_automation.md` dokumentiert `triage:offen`, `stage:*` und die alte Statusfamilie `status:idea` bis `status:rejected`
  - `knowledge/playbooks/08_ISSUE_TRIAGE_BACKLOG_HYGIENE.md` beschreibt sinnvolle Triage-Inhalte, aber nicht die heute kanonische GitHub-Labelsprache
- Weitere operative Labels existieren ausserhalb des offiziellen Manifestes:
  - `triage:offen`
  - `stage:*`
  - `report:weekly-fail` und implizit `report:weekly`
  - sie werden in Workflows und Runbooks verwendet, sind aber weder in `.github/LABELS.md` noch in `.github/workflows/labels.json` als Canon verankert.
- Zuspitzender Mismatch:
  - `.github/workflows/label-bootstrap.yml` erwartet `.github/labels.json`, obwohl der deklarierte Canon heute `.github/workflows/labels.json` ist
  - `.github/workflows/sync-labels.yml` synchronisiert nur `labels.json`
  - `prune: false` bedeutet: alte oder aussermanifestige Labels bleiben live, auch wenn der Repo-Canon sie nicht fuehrt
  - damit ist die Taxonomie aktuell nicht repo-seitig sauber erzwungen, sondern nur teilweise beschrieben.
- Ein duennes Progress-Signal existiert bereits, aber nicht issue-spezifisch:
  - Project-v2 Status-Sync ueber `project_status_sync.yml`, `project_status_label_map.yml`, `project_reconcile_daily.yml`
  - aggregierte Sicht ueber `weekly_digest.yml` und `weekly_digest_failure_alert.yml`
  - das ist Board-/Digest-Progress, aber kein eigener Issue-Progress-Tracker aus linked PRs oder Merge-Events.

## Minimaler Zielzustand

- Genau eine repo-kanonische `status:/triage:`-Sprache wird festgezogen.
- Die kanonische Labelquelle bleibt:
  - `.github/workflows/labels.json`
  - `.github/LABELS.md`
- Fuer `#169` sollte diese kanonische Taxonomie minimal bleiben:
  - `status:ready`
  - `status:blocked`
  - `status:in-review`
  - `status:wontfix`
  - plus `triage:offen` als explizites operatives Triage-Label
- Project-v2-Feldwerte bleiben davon getrennt:
  - `Backlog`
  - `Ready`
  - `In Progress`
  - `Review`
  - `Blocked`
  - `Done`
  - sie sind Board-Statuswerte und muessen nicht ueber eine zweite, konkurrierende Labelfamilie gespiegelt werden.
- Alte Status-Labelfamilien wie `status:idea`, `status:approved`, `status:review`, `status:merged`, `status:descoped`, `status:rejected` sollten fuer `#169` nicht weiter kanonisiert, sondern aus Doku-/Workflow-Source-of-Truth entfernt werden.
- `gemini-scheduled-triage.yml` sollte denselben Triage-Signalpfad nutzen wie der Rest des Repos und nicht `status/needs-triage`.

## Einschätzung zum optionalen thin issue-progress tracker

- Repo-belegt ist heute nur ein duennes Progress-Bild auf Board-/Digest-Ebene:
  - Project-v2 Status-Feld
  - Weekly Digest
  - Weekly Digest Failure Alert
- Ein eigener Issue-Progress-Tracker aus PR-Merges, linked PRs oder Lifecycle-Kommentaren ist im aktuellen Repo nicht sauber belegt.
- Deshalb sollte ein neuer Tracker fuer `#169` standardmaessig Nicht-Ziel bleiben.
- Wenn ueberhaupt etwas als `thin tracker` stehen bleiben soll, dann nur als Interpretation des bereits vorhandenen Board-/Digest-Pfads, nicht als neues Workflow-System.
- Der einzig spaeter denkbare ultra-duenne Zusatz waere eine enge Ableitung auf Basis des kanonischen `status:in-review` fuer Issues mit offenem verlinktem PR. Das ist aber fuer den Reduced Scope von `#169` nicht noetig und sollte ohne klare Repo-Belege nicht gestartet werden.

## Dateiliste fuer Claude Code

- Sollte angefasst werden:
  - `.github/LABELS.md`
  - `.github/workflows/labels.json`
  - `.github/workflows/label-bootstrap.yml`
  - `.github/workflows/triage_guard.yml`
  - `.github/workflows/project_status_label_map.yml`
  - `.github/workflows/project_reconcile_daily.yml`
  - `.github/workflows/gemini-scheduled-triage.yml`
  - `docs/runbooks/project_board_automation.md`
  - `knowledge/playbooks/08_ISSUE_TRIAGE_BACKLOG_HYGIENE.md`
- Nur falls eine kurze Einordnung des vorhandenen Progress-Bilds noetig ist:
  - `.github/workflows/weekly_digest.yml`
  - `.github/workflows/weekly_digest_failure_alert.yml`
- Fuer `#169` standardmaessig nicht anfassen:
  - `.github/workflows/control_board_auto_routing.yml`
  - `.github/workflows/control_board_upsert.yml`
  - `.github/workflows/add_to_project.yml`
  - `.github/workflows/auto-milestone*.yml`
  - `.github/MILESTONES.md`
  - breite Dashboard-/Visibility-Doku aus `#170`

## Risiken / Annahmen / offene Punkte

- `sync-labels.yml` nutzt `prune: false`; selbst nach einer Repo-Kanonisierung koennen alte Live-Labels in GitHub bestehen bleiben. Der eigentliche Gewinn von `#169` liegt deshalb in einer sauberen Source-of-Truth und konsistenten Workflow-Verbrauchern, nicht in einem automatischen Hard-Cleanup aller Altlabels.
- `triage:offen` ist heute operativ kritisch; solange es nicht im kanonischen Labelmanifest auftaucht, haengt `triage_guard.yml` an einem repo-seitig nicht sauber beschriebenen Label.
- `status:blocked` ist bereits aktiv an `stale.yml` gekoppelt; die heutige `status:*`-Taxonomie ist also nicht komplett tot, sondern nur unvollstaendig operationalisiert.
- Die Board-/Control-Board-Doku hat weitere Drift ausserhalb der engeren Taxonomie, zum Beispiel verteilte PR-/Issue-Pfade und `stage:*`-Labels. `#169` sollte das nicht zu einem Gesamtumbau der Project-v2-Automation aufblasen.
- Zwischen Milestone-/Board-Automation und Label-Doku gibt es weitere Widersprueche (`milestone:*`-Inputlabels, zwei Milestone-Modelle, feature-flagged PR-Routing). Diese Drifts sind real, sollten fuer `#169` aber nur als Kontext markiert und nicht als eigener Umbau aufgemacht werden.
- Auch die Canon-Pointer in der Doku sind nicht komplett sauber (`docs/meta/WORKING_REPO_CANON.md` vs. konkurrierende Aussagen in `knowledge/INDEX.md`). Das ist fuer `#169` nur Kontext und darf nicht in eine allgemeine Docs-IA-Bereinigung kippen.
- Wenn Maintainer auch `stage:*` oder `report:*` in denselben Canon ziehen wollen, waere das ueber den engen `status/triage`-Scope hinaus eine groessere Label- und Board-Bereinigung.

## Klare Nicht-Ziele

- Kein neues grosses Workflow-System fuer Issue-Management.
- Kein neues PM-/Dashboard-/Critical-Path-System.
- Kein Rebuild der Project-v2-Board-Architektur.
- Kein Agent-Routing-, Dashboard- oder Visibility-Programm aus `#170`.
- Kein generisches Issue-Labeling oder PR-Labeling aus `#145`.
- Kein Weekly-Digest-/Governance-Review-Redesign.
- Kein Nachziehen von `#659`, `#661`, `#785`, `#1138`, `#1139`, `#1142`.
- Kein Bulk-Cleanup aller historischen Labels, Milestone-Labels, Epics oder Archiv-Dateien.

## Claude-Code-Handoff

### Ziel

Die vorhandene GitHub-Status-/Triage-Sprache auf einen kleinen, repo-kanonischen Satz vereinheitlichen und klar entscheiden, dass kein neuer grosser Issue-Progress-Tracker gebaut wird.

### Betroffene Dateien

- `.github/LABELS.md`
- `.github/workflows/labels.json`
- `.github/workflows/label-bootstrap.yml`
- `.github/workflows/triage_guard.yml`
- `.github/workflows/project_status_label_map.yml`
- `.github/workflows/project_reconcile_daily.yml`
- `.github/workflows/gemini-scheduled-triage.yml`
- `docs/runbooks/project_board_automation.md`
- `knowledge/playbooks/08_ISSUE_TRIAGE_BACKLOG_HYGIENE.md`
- optional: `.github/workflows/weekly_digest.yml`
- optional: `.github/workflows/weekly_digest_failure_alert.yml`

### Minimale Aenderungen

- `.github/LABELS.md` und `.github/workflows/labels.json` als harte Source-of-Truth angleichen:
  - kanonische `status:*`-Menge klar benennen
  - `triage:offen` explizit aufnehmen
  - keine zweite konkurrierende alte Statusfamilie weiterfuehren
- `label-bootstrap.yml` auf denselben kanonischen Labelpfad ziehen wie `sync-labels.yml`, damit Label-Bootstrap und Label-Source-of-Truth nicht weiter auseinanderlaufen.
- `triage_guard.yml` und `gemini-scheduled-triage.yml` auf denselben Triage-Signalpfad bringen.
- `project_status_label_map.yml` und `project_reconcile_daily.yml` von der alten Statuslabel-Familie auf den kanonischen Satz umstellen und Project-Statuswerte als Board-Feldlogik statt Label-Folklore behandeln.
- `project_board_automation.md` und `08_ISSUE_TRIAGE_BACKLOG_HYGIENE.md` auf dieselbe Taxonomie festziehen.
- Keinen neuen Progress-Workflow einfuehren. Falls das Repo an irgendeiner Stelle den Tracker-Aspekt erwaehnen soll, dann nur als knappe Einordnung des bestehenden Board-/Digest-Pfads als bereits vorhandener `thin tracker`.

### Validierung

- `.github/LABELS.md` und `.github/workflows/labels.json` muessen dieselbe kanonische `status:/triage:`-Menge fuehren.
- Kein kanonischer Workflow fuer Triage/Status darf noch `status:idea`, `status:approved`, `status:review`, `status:merged`, `status:descoped`, `status:rejected` oder `status/needs-triage` als Source-of-Truth verwenden.
- `triage_guard.yml` und `gemini-scheduled-triage.yml` muessen auf denselben Triage-Begriff zeigen.
- Doku und Workflow-Logik muessen klar zwischen Labels und Project-v2-Statusfeld unterscheiden.
- Es duerfen keine neuen Workflow-Dateien oder neuen grossen Automationspfade entstehen.

### Rollback / Sicherheitsgrenzen

- Rollback ist docs/workflow-only.
- Keine Project-v2-Strukturmigration, keine neuen Views, keine neuen Boards.
- Keine neuen Merge-/PR-/Issue-Kommentierungsautomatismen als Teil von `#169`.
- Wenn fuer die Kanonisierung aendereungen an Project-Feldoptionen, Board-Architektur oder groesseren Lifecycle-Automationen noetig waeren, STOP und als Out-of-Scope fuer den Reduced Scope markieren.
