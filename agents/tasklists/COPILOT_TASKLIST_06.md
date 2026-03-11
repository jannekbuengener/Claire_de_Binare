# CDB — Copilot Tasklists (Office Pack)
Stand: 2025-12-16

## Reihenfolge (Office Execution Order)
1. Prompt-Migration `.txt → .md`
2. Büro-Files Scan (Consistency Review)
3. Weekly Status Digest (1 Seite)
4. M7 Skeleton (Paper Trading Struktur)
5. Dockerfile & Stack Hardening (Compose/Runtime)
6. Papertrading Setup + Live-Daten + Execution Service Config

---

---

## Copilot Tasklist 06 — Papertrading Setup + Live-Daten + Execution Service Config
**Ziel:** Papertrading-Phase operational machen (Start/Stop/Health + Config Flags).  
**Scope:** Working Repo

- Betriebsmodi definieren (Flags/Profiles): `paper` vs `live` vs `dry-run`.
- Konfig-Check:
  - Quelle Live-Daten (market service / mock feed)
  - Execution-Service ENV: Mode, Endpoints, Risk-Gate, Timeouts
- `.env.example` erweitern:
  - paper/live flags
  - execution toggles
  - safe defaults
- Runbook erstellen: `knowledge/operating_rules/runbook_papertrading.md` (kurz, ausführbar)
  - Start/Stop
  - Healthcheck
  - Minimal Smoke-Test
- Validierungspfad notieren:
  - `make docker-up` → `make docker-health` → smoke
- Output: Runbook + `.env.example` Ergänzungen + kurze Testanleitung.

**Stop-Regel:** Keine echten Exchange-Keys, keine Secrets, keine Live-Execution aktivieren.

---

