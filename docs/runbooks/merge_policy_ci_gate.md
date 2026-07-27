# Merge Policy and CI Gate

## Verbindlicher Vertrag

Für Pull Requests auf `main` gelten genau zwei merge-relevante Check-Kontexte:

| Workflow | Check |
|---|---|
| `.github/workflows/ci.yml` | `ci (Unit/Integration + Lint gesammelt)` |
| `.github/workflows/policy-gate.yml` | `policy-gate` |

Die frühere parallele Legacy-CI wurde am 2026-07-16 entfernt. Es gibt keinen
zweiten Push-/Dispatch-CI-SSOT mehr.

## Merge-Gates

Vor einem Merge müssen beide Checks erfolgreich und dem aktuellen PR-Head-SHA
zugeordnet sein. Alte grüne Runs, lokale Tests oder andere Actions ersetzen
diese Check-Kontexte nicht.

Der on-demand Workflow `required-checks-audit.yml` kann die Konfiguration
prüfen, erzeugt selbst aber keinen merge-relevanten Ersatzcheck.

## Sicherheitsmodell

- PR-Code läuft für die kanonischen Checks auf GitHub-hosted Runnern.
- Untrusted Fork-Code darf nicht auf privilegierten self-hosted Runnern laufen.
- `pull_request_target` darf keinen untrusted Checkout ausführen.
- Code-Owner- und Review-Signale bleiben wichtig, auch wenn die aktuelle Branch
  Protection keine Mindestzahl genehmigender Reviews erzwingt.

## Diagnose

1. PR-Head-SHA ermitteln.
2. Check-Runs für exakt diesen SHA prüfen.
3. Fehlenden Check von einem fehlgeschlagenen Check unterscheiden.
4. Workflow-Trigger und Path-Filter direkt in der YAML kontrollieren.
5. Erst nach grünen aktuellen Checks mergen.

## Dokumentationspflicht

Änderungen an Check-Namen, Triggern oder Branch Protection müssen gemeinsam in
`docs/ci/index.md`, diesem Runbook, dem Workflow-Register und den
Required-Check-Contract-Tests aktualisiert werden.

## Local Docker CI Phase 1 (advisory only)

Seit Phase 1 existiert eine lokale Docker-CI-Schicht unter `ci/`
(siehe [`ci/README.md`](../../ci/README.md)).

Verbindliche Regeln:

- Lokale Evidence (`ci/artifacts/<run_id>/manifest.json`) ist **kein** Ersatz für
  die Required Checks `ci (Unit/Integration + Lint gesammelt)` oder `policy-gate`.
- Branch Protection bleibt in Phase 1 unverändert.
- GitHub-Workflows bleiben in Phase 1 funktional unverändert.
- Dirty worktree ⇒ lokale Evidence `BLOCKED` und darf nicht als Merge-Evidence
  gelten.
- `policy-gate` bleibt GitHub-API-gebunden; der lokale Governance-Stage enthält
  nur einen Mirror-Hinweis ohne Paritätsanspruch.
- Lokales CodeQL/SARIF ersetzt nicht den GitHub Security-Tab.

Live Branch-Protection-Hinweis (reverify with `gh api`):
`required_conversation_resolution` war zum Audit-Zeitpunkt der Local-CI-Phase-1
Planung auf `false` gesetzt — Live-API schlägt ältere Runbook-Snapshots.

Windows front door:

```powershell
pwsh -File ci/scripts/run_all.ps1 -Profile fast
```
