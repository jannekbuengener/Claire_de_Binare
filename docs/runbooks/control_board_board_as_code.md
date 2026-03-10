# Runbook: CDB Control Board Automation (Board-as-Code)

## Ziel

Deterministische Automation fuer Project v2 `CDB Control Board` ohne manuelles Klicken.

## Komponenten

- Upsert-Script: `scripts/project/upsert_control_board.py`
- Routing-Script: `scripts/project/route_control_board.py`
- Workflow Upsert: `.github/workflows/control_board_upsert.yml`
- Workflow Routing: `.github/workflows/control_board_auto_routing.yml`

## Feature Toggle (default OFF)

Repository Variable:

- `CDB_CONTROL_BOARD_AUTOMATION_ENABLED=false` (Default)
- Auf `true` setzen, um Event-Routing zu aktivieren.

Hinweis:
- Bei `false` gibt es keine automatische Verhaltensaenderung bei `issues`/`pull_request` Events.
- Workflows loggen explizit `automation disabled` und beenden ohne Project-API Aufrufe.

## Token-Scopes (Least Privilege)

In Actions wird der Laufzeit-Token aus GitHub App (bevorzugt) oder `ADD_TO_PROJECT_PAT` (Fallback) aufgeloest.

### A) GitHub App (preferred)

Empfohlene Installation-Permissions (repo-scoped):

- `Metadata`: `Read-only`
- `Projects`: `Read and write`
- `Issues`: `Read and write` (nur fuer Routing)
- `Pull requests`: `Read-only` (nur fuer Routing)

Zuordnung pro Automation:

- `control_board_upsert.yml`: `Projects` + `Metadata`
- `control_board_auto_routing.yml`: `Projects` + `Issues` + `Pull requests` + `Metadata`

### B) PAT Fallback (`ADD_TO_PROJECT_PAT`)

Bevorzugt: Fine-grained PAT, nur fuer dieses Repo (`jannekbuengener/Claire_de_Binare`):

- `Metadata`: `Read-only`
- `Projects`: `Read and write`
- `Issues`: `Read and write`
- `Pull requests`: `Read-only`

Classic PAT nur als Legacy-Fallback:

- `project` (Project v2 GraphQL read/write)
- `repo` ist hier nur deshalb erforderlich, weil Routing folgende `/repos/...` Endpoints nutzt:
  - `GET /repos/{owner}/{repo}/milestones`
  - `GET /repos/{owner}/{repo}/issues/{number}`
  - `PATCH /repos/{owner}/{repo}/issues/{number}`
  - `GET /repos/{owner}/{repo}/pulls/{number}`

Empfehlung: Kein breit eingesetztes Classic-PAT mit pauschalem `repo` mehr verwenden, sondern auf Fine-grained PAT mit obigen Minimalrechten wechseln.

### Workflow permissions vs token scopes

- `permissions:` in den Workflow-Dateien steuert nur den automatisch bereitgestellten `GITHUB_TOKEN`.
- Die Control-Board-Mutationen laufen mit `CDB_AUTH_TOKEN` (App/PAT) und dessen Scopes.
- Beide Ebenen muessen getrennt least-privilege sein.

## Scope Verification (minimal)

Read-Test (Project v2 Query):

```bash
gh api graphql \
  -f query='query($owner:String!,$number:Int!){user(login:$owner){projectV2(number:$number){id title}}}' \
  -f owner='jannekbuengener' \
  -F number=8
```

Write-Test (nur in kontrollierter Umgebung / Test-Item ausfuehren):

```bash
gh api graphql \
  -f query='mutation($projectId:ID!,$itemId:ID!,$fieldId:ID!,$optionId:String!){updateProjectV2ItemFieldValue(input:{projectId:$projectId,itemId:$itemId,fieldId:$fieldId,value:{singleSelectOptionId:$optionId}}){projectV2Item{id}}}' \
  -f projectId='PVT_xxx' \
  -f itemId='PVTI_xxx' \
  -f fieldId='PVTSSF_xxx' \
  -f optionId='OPTION_xxx'
```

Troubleshooting:

- `403 Resource not accessible by integration`: Token zu klein berechtigt oder im falschen Kontext.
- Sicherstellen, dass der Workflow tatsaechlich `CDB_AUTH_TOKEN` (App/PAT) nutzt und nicht nur `GITHUB_TOKEN`.
- GitHub App Installation-Permissions und Repo-Zuordnung pruefen.

## Manual Follow-up (required)

1. GitHub App Installation-Permissions in GitHub UI auf die oben genannten Minimalrechte setzen.
2. `ADD_TO_PROJECT_PAT` (falls noch genutzt) auf Fine-grained PAT mit Minimalrechten umstellen/rotieren.
3. Secret-Name `ADD_TO_PROJECT_PAT` unveraendert lassen (kein Breaking Change fuer Workflows).
4. Danach `control_board_upsert.yml` per `workflow_dispatch` im Dry-Run testen.

## Board-Upsert ausfuehren

Dry-Run (lokal):

```bash
python scripts/project/upsert_control_board.py --dry-run --owner jannekbuengener --project-number 8
```

Apply (lokal):

```bash
python scripts/project/upsert_control_board.py --apply --owner jannekbuengener --project-number 8
```

Workflow:

- `Control Board Upsert` kann per `workflow_dispatch` gestartet werden.
- Mutationen laufen nur bei `CDB_CONTROL_BOARD_AUTOMATION_ENABLED=true`.
- Schedule-Run ist ebenfalls per Toggle geschuetzt.

## Enforced Felder (Upsert)

- `Priority`: `P0 | P1 | P2 | P3`
- `Stage`: `proof | stability | trade-capable | strategy-validated`
- `Evidence`: Text
- `Blocked`: `Yes | No`
- `Blocker Link`: Text
- `Effort` (optional): `S | M | L`

## Routing-Regeln (Automation)

Trigger:

- `issues`: `opened`, `labeled`
- `pull_request`: `opened`, `closed`

Aktionen:

- Issue/PR wird ins Project aufgenommen.
- `Stage` wird aus `label:stage:*` gesetzt (legacy `stage:*` wird weiterhin akzeptiert).
- `Priority` wird aus Titelprefix `P0..P3` oder `label:prio:*` gesetzt.
- `Status` Default = `Backlog` (wenn leer).
- Milestone-Mapping aus `Stage`:
  - `proof` -> `System ist beweisbar`
  - `stability` -> `System ist stabil`
  - `trade-capable` -> `System kann handeln`
  - `strategy-validated` -> `Strategie ist validiert`

Konfliktregeln (deterministisch):

- Mehrere Stage-Labels gleichzeitig: Stage wird nicht geaendert (Warn-Log, kein Overwrite).
- Priority-Konflikt Titel vs Label: Label gewinnt.
- Mehrere unterschiedliche Priority-Labels: Priority wird nicht geaendert (Warn-Log).
- Milestone wird nur gesetzt, wenn leer oder bereits ein automation-managed Mapping-Milestone.

## Smoke-Test (Toggle ON)

1. `CDB_CONTROL_BOARD_AUTOMATION_ENABLED=true` setzen.
2. Neues Issue erstellen, z. B. Titel `P1 Example`, Label `label:stage:proof`.
3. Pruefen:
   - Item ist im Project.
   - `Stage=proof`
   - `Priority=P1`
   - `Status=Backlog` (wenn leer)
   - Milestone `System ist beweisbar`

## Smoke-Test Protokoll (minimal)

A) Toggle OFF:

1. `CDB_CONTROL_BOARD_AUTOMATION_ENABLED=false`.
2. Issue Event (`opened` oder `labeled`) ausloesen.
3. Erwartung: Workflow-Log enthaelt `automation disabled`, keine Project-Write-Aktion.

B) Toggle ON:

1. `CDB_CONTROL_BOARD_AUTOMATION_ENABLED=true`.
2. Issue erstellen (`P1 ...`) + `label:stage:proof`.
3. Erwartung: Item im Project, Stage/Priority gesetzt, Status nur wenn leer gesetzt, Milestone nur leer/managed ueberschrieben.

Wenn E2E lokal nicht moeglich:

- `Control Board Upsert` per `workflow_dispatch` ausfuehren.
- Mit Token/Scopes gemaess Abschnitt `Token-Scopes (Least Privilege)` gegen Project v2 verifizieren.

## Guardrails

- Keine Trading-Logic/Threshold/Decision-Logic Aenderungen.
- Keine Aenderungen unter `knowledge/governance/**`.
- Keine schema-breaking Migrationen.
