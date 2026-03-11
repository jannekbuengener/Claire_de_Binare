# Canonical Golden State (2025-12-25)

## TL;DR
**Grün** heißt: Security baseline abgeschlossen, DB-Schema lädt deterministisch, E2E Shield aktiv, Replay deterministisch beweisbar. Nächster Sprint: Risk Guards (#230/#226).

## Canonical Components
### A) Security Baseline (Phase 1) – DONE
- Python Services pip Upgrade abgeschlossen (CVE-Fix).
- Base Images gepinnt (Redis/Postgres).
- CI Security Scan Gate vorhanden.

### B) DB Persistenz (#254) – DONE
- Schema + Migration in `/docker-entrypoint-initdb.d/` gemountet.
- Tabellen vorhanden: `orders`, `trades`, `signals`, `positions`, `portfolio_snapshots`, `schema_version`.
- Execution SQL aligned mit Schema.

### C) E2E Regression Shield (#255) – DONE
- E2E Suite existiert und ist CI-verdrahtet (gated via `E2E_RUN=1`).
- Artifacts/Logs werden bei Fail hochgeladen.

### D) Deterministic Replay MVP (#258) – DONE
- Contract dokumentiert: `docs/contracts/REPLAY_CONTRACT.md`
- Runner: `tools/replay/replay.py` schreibt stable JSONL + SHA256.
- E2E Test: `test_replay_determinism` beweist Hash-Gleichheit.

### E) Risk Guards (#230/#226) – IN PROGRESS
- Aktuell (laut Verification Report): **Model Layer fertig**, **Integration + E2E fehlt**.

## Fast Verify (PowerShell)
```powershell
git checkout main
git pull

# Stack
cd infrastructure/compose
docker compose -f base.yml -f dev.yml up -d
docker compose ps

# DB Tabellen
docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c "\dt"

# E2E (lokal gated)
E2E_RUN=1 pytest tests/e2e/test_paper_trading_p0.py -v --no-cov

# Replay (Beispiel)
python -m tools.replay.replay --count 50 --out artifacts/replay.jsonl --verify-hash
```
