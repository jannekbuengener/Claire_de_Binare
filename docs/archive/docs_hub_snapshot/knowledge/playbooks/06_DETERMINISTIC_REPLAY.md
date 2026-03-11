# Deterministic Replay Runbook (2025-12-25)

## TL;DR
Replay = reproduzierbare Session-Rekonstruktion aus `stream.fills`. Determinismus wird durch stable ordering + stable JSON + Hash-Proof erzwungen.

## Voraussetzungen
- Redis läuft
- `stream.fills` hat Daten

## Verify Input
```powershell
docker exec cdb_redis redis-cli XLEN stream.fills
docker exec cdb_redis redis-cli XREVRANGE stream.fills + - COUNT 3
```

## Replay Run (Beispiel)
```powershell
python -m tools.replay.replay --count 50 --out artifacts/replay.jsonl --verify-hash
```

## Determinism Proof (2 Runs, Hash muss gleich sein)
```powershell
python -m tools.replay.replay --count 50 --out artifacts/replay_run1.jsonl --verify-hash
python -m tools.replay.replay --count 50 --out artifacts/replay_run2.jsonl --verify-hash
```

## Wenn Hash driftet
- Input-Range fixieren (from-id/to-id) oder identische Stream IDs verwenden
- Keine wall-clock Werte ins Output schreiben
- JSON stable formatting (sorted keys) sicherstellen
