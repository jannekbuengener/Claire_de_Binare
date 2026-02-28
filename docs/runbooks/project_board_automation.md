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
- Triage View (`EINGANG`): `https://github.com/users/jannekbuengener/projects/8/views/18`
  - Intake: neue Items landen standardmaessig in `INBOX`; `triage:offen` bleibt Fallback fuer Items ohne aufloesbaren Milestone
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
- Triage-Label:
  - `triage:offen` (offenes Item ohne Milestone)

## Automationen (Workflow-Dateien)

- `.github/workflows/add_to_project.yml`
  - Fügt neue/reaktivierte Issues und PRs automatisch dem Project #8 hinzu.
- `.github/workflows/project_status_sync.yml`
  - Setzt Default-Project-Status bei neuen/reopened Items:
    - Issues -> `Backlog`
    - PRs -> `Review`
- `.github/workflows/project_status_label_map.yml`
  - Setzt Project-Status anhand von `status:*` Labels (inkl. `closed -> Done`), idempotent.
- `.github/workflows/auto-milestone.yml`
  - Setzt bei neuen/reopened/labeled Issues und PRs einen Milestone, falls noch keiner gesetzt ist:
    - genau ein `milestone:<TITLE>` -> setzt den offenen Milestone `<TITLE>`
    - mehrere `milestone:<...>` Labels -> Warnung und keine Mutation
    - sonst Default `INBOX`, aber nur wenn ein offener Milestone `INBOX` existiert
    - unbekannter Titel oder fehlendes/geschlossenes `INBOX` -> nur Warnung, keine Mutation
    - Fork-PRs werden wegen read-only Token nur geloggt und uebersprungen
- `.github/workflows/milestone_stage_label_sync.yml`
  - Synchronisiert `stage:*` Labels aus Milestones (`milestoned`, `demilestoned`, `reopened`), mutually exclusive.
- `.github/workflows/triage_guard.yml`
  - Hält `triage:offen` für offene Issues/PRs synchron:
    - kein Milestone -> Label setzen
    - Milestone gesetzt -> Label entfernen
    - `demilestoned` -> Label wieder setzen
- `docs/runbooks/control_board_board_as_code.md`
  - Technische Kurz-Doku fuer Upsert/Routing (Dry-Run, Apply, Toggle default OFF, Smoke-Test).

## Triage-Prozess (Jannek)

- Öffne die View `EINGANG` und arbeite neue Items mit Default-Milestone `INBOX` zuerst ab; `triage:offen` bleibt nur der Fallback fuer nicht aufgeloeste Faelle.
- Ersetze `INBOX` im Triage-Schritt durch einen der 6 strategischen Milestones.
- Setze danach optional `status:*` Labels (z. B. `status:approved` / `status:in-progress`), damit das Board den Kanban-Status korrekt zieht.

## Milestone-Autofill

- Genau ein `milestone:<TITLE>` mappt 1:1 auf einen vorhandenen offenen Milestone mit exakt diesem Titel.
- Mehrere `milestone:<...>`-Labels gelten als mehrdeutig; der Workflow loggt eine Warnung und setzt keinen Milestone.
- Ohne `milestone:`-Label setzt die Automation den Default-Milestone `INBOX`, aber nur wenn ein offener Milestone `INBOX` existiert.
- `issue-governance.yml` stuft `INBOX` auf den passenden Phase-Milestone hoch, sobald der Titel eine gemappte Phase enthaelt; andere bereits gesetzte Milestones bleiben stabil und werden nicht ueberschrieben.
- Existiert `<TITLE>` nicht als offener Milestone oder ist `INBOX` nicht offen/vorhanden, bleibt das Item unveraendert und der Workflow loggt nur eine Warnung.
- Fork-PRs im `pull_request`-Trigger bleiben unveraendert; der Workflow loggt den read-only-Fall und beendet sich fail-soft.
- `INBOX` ist ein Intake-Milestone; im Triage-Schritt wird er spaeter durch einen der 6 strategischen Milestones ersetzt.

Report-Ausnahme:
- Issues mit `report:weekly` oder `report:weekly-fail` sind `triage:offen`-exempt.
- `triage_guard` überspringt diese Report-Issues deterministisch ohne Label-Mutation.

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
- In GitHub Actions wird `CDB_AUTH_TOKEN` deterministisch gewählt:
  - `APP` wenn `CDB_GH_APP_ID` + `CDB_GH_APP_PRIVATE_KEY` gesetzt sind (optional mit `CDB_GH_APP_INSTALLATION_ID`)
  - sonst `PAT` über `ADD_TO_PROJECT_PAT`

## Token Migration (#941)

Zweck:
- Vorbereitung auf Least-Privilege-Auth ohne Breaking Change; Legacy-PAT bleibt als Fallback aktiv.

Secrets (Reihenfolge der Nutzung):
- Legacy (bestehend): `ADD_TO_PROJECT_PAT`
- App (empfohlen): `CDB_GH_APP_ID`, `CDB_GH_APP_PRIVATE_KEY`, optional `CDB_GH_APP_INSTALLATION_ID`

Auth-Modi:
- Option A (empfohlen): GitHub App Token (runtime mint), genutzt wenn App-Secrets vollständig vorhanden sind.
- Option B (Fallback): Fine-grained/Classic PAT in `ADD_TO_PROJECT_PAT` (nur bis Migration abgeschlossen ist).

Minimal benötigte Rechte:
- Projects v2 lesen/schreiben (Item add/update, Status-Updates)
- Issues/PRs lesen/schreiben (Labels, Create/Update/Close von Digest- und Alert-Issues)
- Keine zusätzlichen repo-weiten Admin-Rechte

Umstellung (safe rollout):
1. App im Owner-Kontext installieren und App-Secrets im Repo setzen.
2. `workflow_dispatch` für `Weekly Project Digest` und `Weekly Digest Failure Alert` testen.
3. Prüfen, dass Logs `Auth mode selected: APP` zeigen.
4. Nach stabiler Laufzeit PAT rotieren/entfernen (`ADD_TO_PROJECT_PAT` als Break-glass nur temporär behalten).

Rollback (Break-glass):
1. App-Secrets entfernen oder leeren.
2. `ADD_TO_PROJECT_PAT` aktiv lassen.
3. Workflows fallen deterministisch auf `PAT` zurück.

Trigger-Safety:
- Secret-abhängige Board-Automationen laufen nur auf trusted Events (z. B. `issues`, `schedule`, `workflow_dispatch`) und nicht auf `pull_request`.
- PR-bezogene Board-Änderungen sind dadurch eventual consistent und werden über den täglichen Reconcile-Job nachgezogen.

## Quick Sanity Checks (gh CLI)

## Manual validation

- Ensure an open milestone `INBOX` exists (otherwise workflow warns and does nothing)
- New issue without milestone gets `INBOX`
- New issue with exactly one `milestone:<TITLE>` gets the matching open milestone
- New issue with multiple `milestone:<...>` labels only warns and stays unchanged
- Phase-based governance upgrades `INBOX` to the mapped phase milestone, but does not overwrite other milestones
- PR from the same repo gets a milestone via the Issues API
- `workflow_dispatch` backfill only touches open items without a milestone
- Missing or closed `INBOX` only warns and does not fail the workflow

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
