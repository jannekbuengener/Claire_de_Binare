# MCP Navpack (Working Repo)

Kompakte Navigations- und Evidence-Hilfe für Agents/MCP — ergänzt, ersetzt nicht `README.md` oder `agents/AGENTS.md`.

## Files

| File | Zweck |
|---|---|
| [`ENTRYPOINTS.yaml`](ENTRYPOINTS.yaml) | Maschinenlesbare Read-Order (15 Steps) |
| [`CHEATSHEET.md`](CHEATSHEET.md) | Menschliche Kurzreferenz, Top-Commands |
| [`REPO.map.json`](REPO.map.json) | Repo-Map / discovery hints |

## Recommended read order (summary)

1. `README.md` — Projekt-Front-Door, LR NO-GO framing  
2. `docs/index.md` — kurzer Docs-Index  
3. `DEVELOPER_ONBOARDING.md` — lokales Setup  
4. `Makefile` + `.github/workflows/ci.yml` — Test/Lint-Gates  
5. `infrastructure/compose/README.md` — BLUE+RED  
6. MCP: `claire-de-binare.mcp.json`, `tools/validate_mcp_config.py`  
7. Safety: `core/config/trading_mode.py`  
8. `services/README.md`, `tests/README.md`, `agents/AGENTS.md`

## SSOT boundary

- Live GitHub > Repo files > Ledger (`CURRENT_STATUS.md`).
- Board stage `trade-capable` ≠ Live-Go.
- Navpack listet Pfade; Verdikt steht in kanonischen SSOT-Dateien.
