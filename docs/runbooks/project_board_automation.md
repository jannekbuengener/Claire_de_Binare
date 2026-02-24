# Runbook: GitHub Project / Board Automation (CDB)

## Zweck

Kurzer Betriebsleitfaden für die Repo-Organisation über Milestones, Labels und GitHub Project v2 (`CDB Control Board`).

## Zielbild (10 Zeilen)

1. Die 6 Milestones bilden die strategischen Phasen des Repos.
2. Jedes offene Issue/PR hat genau 1 Milestone.
3. `stage:*` Labels spiegeln den Milestone 1:1 (mutually exclusive).
4. Pro Item gibt es also maximal ein `stage:*` Label.
5. `status:*` Labels steuern den gewünschten Kanban-Status im Board.
6. Project v2 #8 ist das visuelle Cockpit für Priorisierung und Fluss.
7. Neue Issues/PRs werden automatisch in das Project importiert.
8. Neue Issues/PRs erhalten automatisch einen Default-Status (Issue=`Backlog`, PR=`Review`).
9. `status:*` Labels überschreiben/setzen den Project-Status per Label-Mapping.
10. Milestone-Änderungen synchronisieren automatisch das passende `stage:*` Label.

## Hard Facts

- Project URL: `https://github.com/users/jannekbuengener/projects/8`
- Owner / Number: `jannekbuengener / 8`
- Milestones:
  - `System ist beweisbar`
  - `System ist stabil`
  - `System kann handeln`
  - `Strategie ist validiert`
  - `System verdient Geld`
  - `Skaliert`
- `stage:*` Labels (mutually exclusive):
  - `stage:proof`
  - `stage:stability`
  - `stage:trade-capable`
  - `stage:strategy-validated`
  - `stage:monetization`
  - `stage:scale`
- `status:*` Labels (Kanban-Status):
  - `status:idea`
  - `status:approved`
  - `status:in-progress`
  - `status:review`
  - `status:merged`
  - `status:descoped`
  - `status:rejected`

## Automationen (Workflow-Dateien)

- `.github/workflows/add_to_project.yml`
  - Fügt neue/reaktivierte Issues und PRs automatisch dem Project #8 hinzu.
- `.github/workflows/project_status_sync.yml`
  - Setzt Default-Project-Status bei neuen/reopened Items:
    - Issues -> `Backlog`
    - PRs -> `Review`
- `.github/workflows/project_status_label_map.yml`
  - Setzt Project-Status anhand von `status:*` Labels (inkl. `closed -> Done`), idempotent.
- `.github/workflows/milestone_stage_label_sync.yml`
  - Synchronisiert `stage:*` Labels aus Milestones (`milestoned`, `demilestoned`, `reopened`), mutually exclusive.

## Troubleshooting (Klassiker)

### 1) Actions Minutes / Billing blockiert

Symptome:
- Viele PR-Checks failen gleichzeitig nach wenigen Sekunden.
- Jobs starten nicht wirklich (kaum/keine Steps, keine normalen Logs).
- Check-Annotation enthält sinngemäß: Billing/Spending limit blockiert GitHub Actions.

Fix:
1. GitHub `Billing & plans` prüfen/fixen (Zahlung / Spending Limit).
2. Danach betroffene Runs neu starten:
   ```bash
   gh run rerun <RUN_ID>
   ```
3. PR-Checks erneut beobachten:
   ```bash
   gh pr checks <PR_NR> --watch
   ```

### 2) `required_conversation_resolution` blockiert Merge

Symptome:
- Alle Checks grün, aber `gh pr view` zeigt `mergeStateStatus=BLOCKED`.
- Häufig durch offene Bot-Review-Threads.

Fix:
1. Runbook nutzen: `docs/runbooks/resolve_review_threads_via_graphql.md`
2. Offene Review-Threads per GraphQL resolve.
3. Merge erneut setzen:
   ```bash
   gh pr merge <PR_NR> --auto --squash --delete-branch
   ```

### 3) Project-Scopes fehlen / falscher Token aktiv (`GH_TOKEN` vs `GITHUB_TOKEN`)

Symptome:
- `gh project ...` oder `gh api graphql` auf Project v2 schlägt fehl.
- Meldungen wie `missing required scopes [read:project]` oder fehlendes `project`.

Fix (lokal):
1. Auth prüfen:
   ```bash
   gh auth status
   ```
2. Wenn ein Env-Token ohne `project` aktiv ist, temporär entfernen (Shell-Session):
   ```powershell
   Remove-Item Env:GITHUB_TOKEN -ErrorAction SilentlyContinue
   Remove-Item Env:GH_TOKEN -ErrorAction SilentlyContinue
   ```
3. Auf Keyring-Login mit Classic PAT umschalten:
   ```bash
   gh auth switch --hostname github.com --user jannekbuengener
   ```
4. Scopes prüfen (`repo`, `project` erforderlich für Project-v2-Write).

Hinweis:
- In GitHub Actions nutzen die Workflows explizit `GH_TOKEN: ${{ secrets.ADD_TO_PROJECT_PAT }}` (Classic PAT mit `repo` + `project`).

## Quick Sanity Checks (gh CLI)

### Auth / Scopes

```bash
gh auth status
```

### PR Checks (inkl. Watch)

```bash
gh pr checks <PR_NR>
gh pr checks <PR_NR> --watch
```

### Offene Issues / PRs mit Milestones + Labels prüfen

```bash
gh issue list --state open --limit 500 --json number,title,milestone,labels,url
gh pr list --state open --limit 500 --json number,title,milestone,labels,url
```

### Sehen, ob `add-to-project` läuft

```bash
gh run list --workflow "Add issues and PRs to CDB Control Board" --limit 10
gh run view <RUN_ID>
```

### Project-Board grob prüfen (optional)

```bash
gh project list --owner jannekbuengener --limit 20
```

## Betriebsregeln (kurz)

- Keine manuellen Doppel-Statussysteme pflegen: Milestone -> `stage:*`, Kanban über `status:*`.
- `stage:*` Labels sind exklusiv (genau 0 oder 1, je nach Milestone-Zustand).
- Board-Status ist idempotent automatisiert; bei Sonderfällen zuerst Labels/Milestone prüfen.
