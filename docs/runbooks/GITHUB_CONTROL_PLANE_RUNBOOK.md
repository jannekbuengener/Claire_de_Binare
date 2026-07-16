# GitHub Control Plane Runbook

**Stand:** 2026-07-16

Dieses Runbook beschreibt ausschließlich die aktuell vorhandenen Workflows.
Vollständiges Inventar: [GITHUB_WORKFLOW_REGISTER.md](GITHUB_WORKFLOW_REGISTER.md).

## Workflow prüfen

1. Datei im Register auflösen.
2. Trigger und Berechtigungen direkt in der YAML prüfen.
3. Zugehörige Skripte, Prompts und Manifeste ermitteln.
4. Run-History und konkrete Job-Logs in GitHub Actions prüfen.
5. Bei Änderungen Register, generierten Agent-Workflow-Map und Tests gemeinsam aktualisieren.

## Merge-relevante CI

| Workflow | Verbindlicher Check |
|---|---|
| `ci.yml` | `ci (Unit/Integration + Lint gesammelt)` |
| `policy-gate.yml` | `policy-gate` |

Andere Workflows sind keine Branch-Protection-Ersatzchecks. Fehler dort werden
separat triagiert und dürfen nicht als grüner Merge-Gate-Nachweis umgedeutet
werden.

## Typische Störungen

### Label-Kaskade

`issues:labeled` kann mehrere Pfade auslösen, insbesondere
`auto-milestone.yml`, `auto-milestone-label-dispatch.yml`,
`project_status_label_map.yml` und `project_status_sync.yml`. Zuerst die
auslösende Label-Quelle prüfen, dann Downstream-Runs.

### workflow_run-Drift

`weekly_digest_failure_alert.yml` und `auto-milestone-pr-apply.yml` hängen
von exakten Upstream-Workflow-Namen ab. Nach Umbenennungen Trigger und
Contract-Tests synchron aktualisieren.

### Project-Board-Drift

Aktive Pfade sind `control_board_upsert.yml`,
`project_reconcile_daily.yml`, `project_status_sync.yml`,
`project_status_label_map.yml` und `add_to_project.yml`. Es existiert kein
separater Per-Event-Board-Router mehr.

### Manuelle Workflows

Manual-only bedeutet „gezielt per `workflow_dispatch` nutzbar“, nicht
„ungenutzt“. Vor einem Dispatch Inputs, Schreibrechte und erwartete Outputs im
Register prüfen.

## Entfernen eines Workflows

Eine Entfernung ist erst vollständig, wenn:

- die YAML gelöscht ist;
- ausschließlich dafür vorhandene Support-Dateien gelöscht sind;
- aktive Doku und Diagramme keine operative Referenz mehr enthalten;
- generierte Inventare aktualisiert sind;
- workflow-spezifische Tests entfernt oder auf den neuen Contract umgestellt sind;
- historische Evidence nicht nachträglich verfälscht wurde.

Placeholder- oder Deprecation-Stubs werden nicht als dauerhafte
„Sicherheitsreserve“ behalten. Wenn kein operativer Pfad existiert, wird die
Datei entfernt.

## Sicherheitsgrenzen

- Keine Secrets oder Tokens in Logs, Artefakte oder Kommentare schreiben.
- Schreibrechte auf den kleinsten benötigten Scope begrenzen.
- Keine Live-, LR- oder Echtgeldfreigabe aus einem grünen Workflow ableiten.
- `pull_request_target` bleibt für untrusted PR-Code unzulässig.
