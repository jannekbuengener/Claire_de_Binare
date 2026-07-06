# Infra / Compose / Stack Lifecycle Contract Tests

Static and fixture-backed guards for issues **#3856** (compose BLUE/RED) and **#3857**
(stack lifecycle scripts). Parent meta: **#3855**.

## What these tests prove

- Compose layer classification (`canonical_runtime` vs `legacy_ci` / overlays)
- BLUE/RED service canon, network/volume naming, healthcheck posture
- Legacy topology references remain visible (e.g. `stack_up.ps1` → `base.yml` + `dev.yml`)
- Stack lifecycle scripts expose operator gates (`-Force`, `Read-Host`, `-DeepClean`, skip flags)
- Failure paths fail closed; scripts do not echo secret payloads

## What these tests do **not** prove

- No `docker compose up/down` — not a runtime or stack-start proof
- No container health at execution time
- No operator authorization to mutate production stacks

Run targeted checks:

```bash
pytest -q tests/unit/infra -m contract
```
