# Repository Guidelines

# AGENTS.md – Provider-übergreifendes Rollen- & Governance-Register

## 0. Zweck

Dieses Dokument ist der **erste Bezugspunkt**, wenn ein Agent für Claire de Binare gespawnt wird –
egal, ob er über:

- den Codex Orchestrator,
- die MCP-Server,
- die CLI-Bridge (`CLinkTool` mit Clients wie `gemini`, `copilot`, `codex`),
- oder direkt über Claude Code (CLI/VS Code)

aktiviert wird.

Es definiert:

- die **Rollenfamilien** (Orchestrator, Governance, Architektur, Risk, DevOps, Tests, Alpha, Docs, Projekt/Roadmap),
- die **Provider-Zuordnung** (Claude, Gemini, OpenAI, Copilot, Codex, andere),
- die **Arbeitsmodi** (Analyse vs. Delivery),
- und verweist auf die relevanten Detailprompts (`AGENT_*.md`, `GEMINI.md`, `CLAUDE.md`, `GOVERNANCE_AND_RIGHTS.md`).

## 1. Spawn-Protokoll für Anbieter-Agenten

Wenn ein neuer Agent gespawnt wird (z. B. Codex-Agent, Gemini-CLI-Agent, Claude-Code-CLI-Agent),
läuft idealerweise folgendes Protokoll:

1. **AGENTS.md lesen**
   - Rolle identifizieren (z. B. `AGENT_Risk_Architect`, `AGENT_Gemini_Research_Analyst`).
   - Provider/Modellgruppe erkennen (Claude, Gemini, Copilot, OpenAI, Codex).

2. **Gemeinsames Wissensfundament laden**
   - `CLAUDE.md` → Projektstatus, Phase (z. B. N1 Paper-Trading), Risk- und Event-Flow-Regeln.:contentReference[oaicite:14]{index=14}  
   - `GEMINI.md` → Canonical Architecture & Cleanroom-Governance (falls Gemini-/Governance-Rolle).:contentReference[oaicite:15]{index=15}  
   - `GOVERNANCE_AND_RIGHTS.md` → Decision Rights, Safety Rules, Risk-Mode-/Live-Trading-Guardrails.:contentReference[oaicite:16]{index=16}  
   - `PROMPT_Analysis_Report_Format.md` → Standard-Reportstruktur.:contentReference[oaicite:17]{index=17}  

3. **Rollenprompt anwenden**
   - Das konkrete Verhalten, Inputs/Outputs und die Kollaborationsregeln stehen im jeweiligen `AGENT_*.md`.
   - Die dort beschriebenen „Modes“ (Analysis vs. Delivery) sind **verbindlich** und verknüpft mit den Governance-Regeln hier.

4. **Orchestrator-Einbindung**
   - Der Orchestrator (Codex, bzw. in der CLI `bernd-codex`) bleibt der einzige direkte Sprecher zum User.
   - Sub-Agenten antworten fachlich, aber **respektieren die Entscheidungshoheit** von User + Orchestrator.

Dadurch wird sichergestellt, dass alle Anbieter-Agenten – unabhängig von Modell oder CLI –
auf demselben Wissensstand operieren und denselben Governance-Rahmen teilen.

## Project Structure & Module Organization
- Python trading system; runtime modules in `services/` (risk_engine.py, position_sizing.py, execution_simulator.py, mexc_perpetuals.py) plus service wrappers in `backoffice/services/` (signal_engine, risk_manager, execution_service, db_writer, portfolio_manager, execution_simulator).
- Docs live in `backoffice/docs/` (architecture, runbooks, testing, security); ops helpers in `scripts/` and `backoffice/scripts/`; environment templates at `.env.example` and stack wiring in `docker-compose.yml`.
- Tests sit in `tests/` split into `unit/`, `integration/`, `e2e/`, and `local/` with shared fixtures in `tests/conftest.py`.

## Build, Test, and Development Commands
- Setup: `python -m pip install -r requirements-dev.txt` (use a venv). Copy `.env.example` to `.env` before running services.
- Lint/format: `ruff .` then `black .` or `pre-commit run --all-files` (runs Ruff + Black + basic hygiene).
- Local stack for E2E: `docker compose up -d`; stop with `docker compose down`.
- Tests:
  - CI-fast: `pytest -v -m "not e2e and not local_only"` or `make test` / `./run-tests.ps1 test`.
  - Unit only: `pytest -v -m unit`.
  - Integration (mocked services): `pytest -v -m "integration and not e2e and not local_only"`.
  - E2E: `pytest -v -m e2e` (requires running Docker stack).
  - Coverage: `pytest --cov=services --cov=backoffice/services --cov-report=term`.
  - Full local suite: `make test-full-system` or `./run-tests.ps1 test-full-system`.

## Coding Style & Naming Conventions
- Python 3.11, Black-formatted (88 chars, 4-space indent, LF, final newline per `.editorconfig`); Ruff enforces lint rules. Keep type hints and docstrings on service boundaries.
- Files/modules use `snake_case`; classes `PascalCase`; functions/vars `snake_case` (constants upper snake). Avoid emojis in source for Windows compatibility.

## Testing Guidelines
- Markers: `unit`, `integration`, `e2e`, `local_only`, `slow`, `chaos` (see `pytest.ini`). Only `unit`/`integration` run in CI; `local_only`/`chaos` are destructive and must stay local.
- Name tests `test_*.py`; prefer shared fixtures from `tests/conftest.py` and keep new fixtures isolated.
- E2E/local tests expect Docker health; wait ~10s after `docker compose up -d`. Keep coverage artifacts (`htmlcov/`, `.coverage`) out of commits.

## Commit & Pull Request Guidelines
- Use conventional commits as in history (e.g., `fix(env): complete ENV validation`). Keep scope small and message imperative.
- Before PRs: run Ruff + Black and the CI-fast pytest target; note whether E2E/local suites were executed.
- PR description should include: goal/approach, linked issue, configs touched (`.env`, compose), and test commands/results. For behavioral changes, attach logs/metrics from tests rather than screenshots.

## Security & Configuration Tips
- Never commit secrets. Populate `.env` from `.env.example`; MEXC keys are IP-bound—rotate if the host changes. Prefer local Docker networks and shut stacks down after tests (`docker compose down`) to avoid stale state.
