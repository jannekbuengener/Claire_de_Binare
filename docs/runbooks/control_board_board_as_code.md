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

- `Control Board Upsert` laeuft manuell per `workflow_dispatch`.
- Schedule-Run ist per Toggle geschuetzt.

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

## Smoke-Test (Toggle ON)

1. `CDB_CONTROL_BOARD_AUTOMATION_ENABLED=true` setzen.
2. Neues Issue erstellen, z. B. Titel `P1 Example`, Label `label:stage:proof`.
3. Pruefen:
   - Item ist im Project.
   - `Stage=proof`
   - `Priority=P1`
   - `Status=Backlog` (wenn leer)
   - Milestone `System ist beweisbar`

## Guardrails

- Keine Trading-Logic/Threshold/Decision-Logic Aenderungen.
- Keine Aenderungen unter `knowledge/governance/**`.
- Keine schema-breaking Migrationen.
