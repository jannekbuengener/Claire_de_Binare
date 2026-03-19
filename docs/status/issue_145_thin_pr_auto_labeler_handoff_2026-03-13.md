# Issue #145 Handoff - Thin PR Auto-Labeler

Status: closed — decided against implementation (2026-03-15)
Date: 2026-03-13
Audience: Claude Code

## Ist-Analyse

- `#145` ist laut kanonischem Backlog-Audit weiter offen, aber nur mit reduziertem Scope als optionaler, duenner PR auto-labeler.
- Aktuell auf `main` vorhanden:
  - Issue-Labeling: `.github/workflows/auto-label.yml`
  - weitere Issue-Automation: `.github/workflows/comprehensive-issue-labeling.yml`, `.github/workflows/bulk-issue-labeling.yml`
  - Label-Sync: `.github/workflows/sync-labels.yml` + `.github/workflows/labels.json`
  - PR-Milestone-Automation: `.github/workflows/auto-milestone-pr-intent.yml` + `.github/workflows/auto-milestone-pr-apply.yml`
  - PR-Governance / Gatekeeping: `.github/workflows/policy-gate.yml`
- Nicht vorhanden auf `main`: ein aktueller PR-Auto-Labeler.
- `policy-gate` klassifiziert PRs bereits nach Diff/Form in `docs-only`, `workflows-only`, `infra-only` oder `core/service` und verbietet fuer Workflow-Aenderungen `pull_request_target`.
- Die aktuelle Label-Taxonomie in `.github/workflows/labels.json` enthaelt `type:*`, `scope:*`, `prio:*` und `ci:generated`, aber keine Definitionen fuer `docs-only` oder `workflows-only`.
- Live auf GitHub wurden am 2026-03-13 `manual-approval`, `allow-core-change` und `infra-only` bestaetigt; `docs-only` und `workflows-only` waren nicht auffindbar.

## Reduzierter Scope fuer #145

- Nur entscheiden, ob neben `policy-gate` ueberhaupt noch PR-Labels gebraucht werden.
- Falls ja: nur ein duennes `pull_request`-Metadata-Labeling auf heutiger Taxonomie.
- Keine Wiederbelebung der alten PR-299/PR-300-Komplettloesung.

## Minimaler Delta-Plan

1. Ein bewusst kleines Zielbild festziehen:
   - Standardfall: nur `scope:*`-Labels aus dem PR-Diff ableiten.
   - Optional: `type:*` nur aus PR-Titel ableiten, falls der Nutzen klar belegt ist.
2. Einen einzelnen PR-Workflow ergaenzen, metadata-only und mit expliziten `permissions`.
3. Nur dann Label-Definitionen erweitern, wenn der ausgewaehlte Label-Satz heute noch nicht existiert.
4. Validieren, dass der neue Workflow nicht mit `policy-gate` kollidiert und keine verbotenen Muster (`pull_request_target`, fehlende `permissions`) einfuehrt.

## Dateiliste fuer Claude Code

- Muss voraussichtlich angefasst werden:
  - `.github/workflows/pr-auto-label.yml`
- Nur falls der gewaehlte Label-Satz erweitert wird:
  - `.github/workflows/labels.json`
  - `.github/LABELS.md`
- Nicht standardmaessig fuer `#145` anfassen:
  - `.github/workflows/policy-gate.yml`
  - `.github/workflows/auto-label.yml`
  - `.github/workflows/comprehensive-issue-labeling.yml`
  - `.github/workflows/auto-milestone-pr-intent.yml`
  - `.github/workflows/auto-milestone-pr-apply.yml`

## Risiken / Annahmen / offene Punkte

- Unklar ist, ob `#145` ueberhaupt mehr braucht als die bestehende `policy-gate`-Klassifikation.
- `docs-only` und `workflows-only` sind im Gate dokumentiert, aber derzeit nicht Teil der versionierten Label-Taxonomie; ein Auto-Labeler darf diese Labels nicht stillschweigend voraussetzen.
- Historische Doku referenziert teils noch eine groessere PR-Labeling-Loesung; diese Altspuren sind kein Freibrief fuer mehr Scope.
- `delivery-gate` und allgemeine PR-Governance sind separate Themen und duerfen nicht mitgezogen werden.

## Klare Nicht-Ziele

- Kein Umbau von `policy-gate`, `delivery-gate` oder Branch-Protection.
- Keine Governance-Kommentare, keine Blocking-Logik, keine Review-/Size-Labels.
- Keine Issue-Labeling-Aenderungen.
- Kein Wiederaufmachen von `#784`, `#151`, `#170`.
- Kein Rueckgriff auf `#94`; das ist nur historischer Closeout.
- Keine Vermischung mit Folge-Issues `#659`, `#661`, `#785`, `#1138`, `#1139`, `#1142`.

## Claude-Code-Handoff

### Ziel

Optionalen thin PR auto-labeler fuer `#145` nur dann umsetzen, wenn der Mehrwert gegenueber `policy-gate` klar ist; andernfalls `#145` als bewusst schmalen Decision-Track belassen.

### Betroffene Dateien

- Primar: `.github/workflows/pr-auto-label.yml`
- Sekundaer nur bei Taxonomie-Erweiterung: `.github/workflows/labels.json`, `.github/LABELS.md`

### Minimale Aenderungen

- Einen einzigen `pull_request`-Workflow anlegen.
- Nur GitHub-Metadaten und PR-Dateiliste verwenden.
- Labels auf den aktuellen, bewusst kleinen Satz begrenzen.
- Keine weitere Script-/Config-Landschaft anlegen, wenn ein inline `github-script` ausreicht.

### Tests / Validierung

- Workflow muss explizite `permissions` deklarieren.
- Workflow darf kein `pull_request_target` verwenden.
- Dry validation ueber YAML-/Workflow-Pruefung und mindestens einen gedanklichen Testfall je Labelpfad.
- Nach Merge spaeter mit kleiner PR gegen `main` pruefen; nicht in `#145` selbst weitere Automation aufmachen.

### Rollback / Sicherheitsgrenzen

- Rollback muss nur das neue PR-Labeler-Workflow-File betreffen.
- Keine Aenderung an Merge-Gates oder bestehender Issue-/Milestone-Automation.
- Wenn fuer den Nutzen neue Labels noetig waeren, diese explizit benennen; nicht implizit ueber Nebenwege einfuehren.

## Entscheidung (2026-03-15)

**Kein zusaetzlicher PR-Auto-Labeler wird gebaut.**

Begruendung:
1. `policy-gate.yml` deckt PR-Klassifikation via File-Inference bereits ab (Zeilen 109-115: docs-only, workflows-only, infra-only, core/service).
2. Ein Auto-Labeler wuerde `pull-requests: write` Permission einfuehren, die heute nicht noetig ist.
3. Im Solo-Maintainer-/Haertungs-Setup ist der Mehrwert kosmetischer PR-Labels (`scope:*`/`type:*`) nicht ausreichend belegt.

Keine Dateien geaendert ausser diesem Handoff-Dokument. Der empfohlene GitHub-Abschluss fuer #145 ist "not planned", sofern Kommentar, Labels und Closeout wie geplant ausgefuehrt werden.
