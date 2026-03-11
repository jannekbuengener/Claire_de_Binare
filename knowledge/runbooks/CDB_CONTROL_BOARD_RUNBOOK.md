# CDB Control Board Runbook

Operative Kurzreferenz fuer das GitHub Project v2 "CDB Control Board" im Repo "Claire_de_Binare".
Zweck: Steuerung von Issues/PRs entlang der Stages (Beweisbarkeit -> Stabilitaet -> Einsatzfaehig -> Validierung).

## Scope

- Gilt fuer alle aktiven Issues/PRs, die im CDB Control Board landen.
- Board ist "operational control": Ownership, Priorisierung, Evidence, Blocker, Routing.
- Guardrail: Keine Aenderungen an Trading-Logik/Thresholds/Decision-Logik durch dieses Runbook.

## Pflichtfelder (Issue-Standard)

Jedes aktive Issue im Board muss haben:

- `Priority`: `P0 | P1 | P2 | P3`
- `Stage`: `proof | stability | trade-capable | strategy-validated`
- `Owner`: verantwortliche Person ueber `Assignees` (oder aequivalentes People-Feld)
- `Evidence`: URL/Text auf Commit, PR, Run-ID oder Artefakt
- `Blocked`: `Yes | No`
- `Blocker Link`: Link auf blockierendes Issue/PR (wenn `Blocked=Yes`)
- `Effort` (optional): `S | M | L`

## Done-Regel (hart)

- `Done ohne Evidence = nicht done`.
- Beim Setzen auf `Done` muss `Evidence` bereits gesetzt sein.
- Evidence muss auditierbar sein (PR/Commit/Run-ID/Artefakt mit Bezug zum Issue).

## Routing-Regeln (automatisiert)

Board-Automation setzt/verifiziert:

- Issue/PR wird ins Project aufgenommen.
- `Stage` wird aus `label:stage:*` gesetzt.
- `Priority` wird aus Titelpraefix (`P0..P3`) oder `label:prio:*` gesetzt.
- Default `Status` = `Backlog` (falls leer).
- Milestone wird aus `Stage` gemappt:
  - `proof` -> `System ist beweisbar`
  - `stability` -> `System ist stabil`
  - `trade-capable` -> `System kann handeln`
  - `strategy-validated` -> `Strategie ist validiert`

## Betriebsmodus

- "Board-as-Code": Aenderungen an Feldern/Views/Routing sollen deterministisch und idempotent sein.
- Prefer: Dry-Run -> Review -> Apply.
- Keine manuellen Klick-Orgie, wenn es automatisiert werden kann.

## Troubleshooting

1) Issue fehlt im Board
- Check: Hat es ein `stage:*` Label?
- Fix: `label:stage:*` setzen oder Issue manuell ins Project adden (nur als Ausnahme).

2) Stage ist leer
- Ursache: Label fehlt oder Automation lief nicht.
- Fix: `label:stage:*` setzen und Automation rerun (oder Routing-Job triggern).

3) Priority ist leer
- Ursache: Kein Titelpraefix und kein `label:prio:*`.
- Fix: Titel mit `P0/P1/P2/P3` praefixieren oder `label:prio:*` setzen.

4) Done wird gesetzt, aber Evidence fehlt
- Das ist ein Prozessfehler. Status zurueck, Evidence nachziehen, dann Done.

5) Blocked = Yes, aber kein Blocker Link
- Das ist inkonsistent. Blocker Link setzen oder Blocked auf No.

## Guardrails

- Keine Aenderungen unter `knowledge/governance/**`.
- Keine Code-/Policy-Aenderungen durch diese Doku.
- Jede "Done"-Aussage braucht Evidence. Ohne Evidence kein Merge-Gate, kein "fertig".
