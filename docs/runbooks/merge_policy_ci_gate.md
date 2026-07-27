# Merge Policy and CI Gate

## Verbindlicher Vertrag

Für Pull Requests auf `main` gilt genau ein merge-relevanter Required Context
(Branch Protection, live via `gh api`):

| Quelle | Context | Typ |
|---|---|---|
| Local CI Status Publisher | `cdb-local-ci` | Commit Status (`app_id` null) |

Die früheren Required Checks `ci (Unit/Integration + Lint gesammelt)` und
`policy-gate` sind **nicht mehr** branch-protection-required (Migration #4169).
`ci.yml` und `policy-gate.yml` bleiben als Workflow-Inhalt / Safety-Gates
nützlich, ersetzen aber den Required Context nicht.

## Merge-Gates

Vor einem Merge muss `cdb-local-ci` für den aktuellen PR-Head-SHA erfolgreich
gesetzt sein (Publisher nach validierter lokaler Evidence + Policy-Mirror).
Alte grüne GitHub-Actions-Runs, lokale Tests ohne Publish oder andere Actions
ersetzen diesen Context nicht.

Der on-demand Workflow `required-checks-audit.yml` kann die Konfiguration
prüfen, erzeugt selbst aber keinen merge-relevanten Ersatzcheck.

## Sicherheitsmodell

- Untrusted Fork-Code darf nicht auf privilegierten self-hosted Runnern laufen.
- `pull_request_target` darf keinen untrusted Checkout ausführen
  (`policy-gate.yml` prüft das weiterhin).
- Code-Owner- und Review-Signale bleiben wichtig, auch wenn die aktuelle Branch
  Protection keine Mindestzahl genehmigender Reviews erzwingt.
- Required-path Publish (`cdb-local-ci`) erzwingt `--pr-number > 0` und den
  lokalen Policy-Gate-Mirror (`tools/ci/policy_gate_local.py`).

## Diagnose

1. PR-Head-SHA ermitteln.
2. Commit Status `cdb-local-ci` für exakt diesen SHA prüfen.
3. Fehlenden Status von einem fehlgeschlagenen Status unterscheiden.
4. Publisher-Evidence und Policy-Mirror-Fail prüfen.
5. Erst nach grünem aktuellem `cdb-local-ci` mergen.

## Dokumentationspflicht

Änderungen an Check-Namen, Triggern oder Branch Protection müssen gemeinsam in
`docs/ci/index.md`, diesem Runbook, dem Workflow-Register und den
Required-Check-Contract-Tests aktualisiert werden.

## Local Docker CI + Status Publisher

Lokale Docker-CI unter `ci/` (siehe [`ci/README.md`](../../ci/README.md)) und
Publisher (siehe [`docs/ci/local-status-publisher.md`](../ci/local-status-publisher.md)):

- Lokale Evidence allein autorisiert keinen Merge; erst der published
  Commit Status `cdb-local-ci` ist der Required Context.
- Branch Protection required contexts: `["cdb-local-ci"]` (Commit Status).
- Dirty worktree ⇒ lokale Evidence `BLOCKED` und kein Publish.
- Publish-Pfad erzwingt Policy-Gate-Mirror (Parität zu
  `.github/workflows/policy-gate.yml`).
- Kein Fake-Green: dirty, stale, SHA-Mismatch, Hash-Mismatch, required SKIPPED,
  Anti-Replay, fehlende PR-Nummer oder Policy-Gate-Fails blockieren Publish.
- Lokales CodeQL/SARIF ersetzt nicht den GitHub Security-Tab.

Live Branch-Protection-Hinweis (reverify with `gh api`):
`required_status_checks.contexts == ["cdb-local-ci"]`, `checks[].app_id == null`.

Windows front door:

```powershell
pwsh -File ci/scripts/run_all.ps1 -Profile fast
pwsh -File ci/scripts/publish_status.ps1 -Command publish `
  -EvidenceDir ci/artifacts/<run_id> -StatusContext cdb-local-ci -PrNumber <n>
```
