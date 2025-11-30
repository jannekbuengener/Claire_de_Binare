# Dry/Wet Smoke Test (Redis + Params)

Ziel: Dry/Wet-Score auf "WET" (~80) setzen und prüfen, dass die dynamischen Parameter in Redis landen und von Services gelesen werden.

## Schnellsprung
```bash
python scripts/dry_wet_push_mock.py --score 80 --publish --ttl 300
redis-cli -a $REDIS_PASSWORD get adaptive_intensity:current_params
```

## Details
- Script: `scripts/dry_wet_push_mock.py`
  - Default score: 80 (WET), TTL: 300s
  - Key: `adaptive_intensity:current_params`
  - Optional Publish auf `adaptive_intensity:updates`
- Erwartete Parameter (abhängig von ENV-Bounds):
  - `max_exposure_pct` nahe `ADAPTIVE_EXPOSURE_MAX` (standard 0.80)
  - `max_position_pct` nahe `ADAPTIVE_POSITION_MAX` (standard 0.12)
  - `signal_threshold_pct` nahe `ADAPTIVE_THRESHOLD_MAX` (aggressiver Wert)
- Überprüfung:
  - Risk Manager liest dynamische Params (log/metrics)
  - /metrics (dry_wet_service) zeigt Score/Trades, sofern Service läuft

## Rollback
```bash
redis-cli -a $REDIS_PASSWORD del adaptive_intensity:current_params
```
