# Chaos-Test: Risk-State Drift & Auto-Heal

Ziel: Verifizieren, dass der Risk Manager einen korrupten Redis-Risk-State erkennt und mit DB-Wahrheit resynchronisiert (Drift >5%).

## Voraussetzungen
- Services laufen (Risk Manager mit Postgres/Redis verbunden).
- Zugriff auf Redis CLI (`redis-cli -a $REDIS_PASSWORD`).

## Schritte
1) Drift injizieren:
   ```bash
   redis-cli -a $REDIS_PASSWORD set risk_state:persistence '{"total_exposure": 250000, "open_positions": 9}'
   ```
2) Risk Manager beobachten (Logs oder `/metrics`):
   - Erwartete Logline: `RESET REDIS - DB in control` (Startup) oder `State mismatch: triggering DB->Redis recovery`.
   - Metriken steigen: `risk_state_inconsistency_total`, `risk_state_recovery_total`.
3) Nachheilung prüfen:
   ```bash
   redis-cli -a $REDIS_PASSWORD get risk_state:persistence
   ```
   Exposure sollte wieder dem DB-Wert entsprechen.

## Erfolgskriterien
- Risk Manager blockiert nicht, sondern resynchronisiert automatisch.
- Redis-Key wird mit DB-Exposure überschrieben.
- Metriken/Logs reflektieren den Drift und die Recovery.
