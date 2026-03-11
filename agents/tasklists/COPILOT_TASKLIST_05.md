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

## Copilot Tasklist 05 — Dockerfile & Stack Hardening (Compose/Runtime)
**Ziel:** Hardening-Backlog + konkrete Diff-Vorschläge (ohne Merge).  
**Scope:** Working Repo

- Inventar: alle Dockerfiles + Compose-Dateien sammeln.
- Checks pro Dockerfile:
  - non-root user
  - pinned base image (Tag/Digest)
  - minimal packages
  - keine Secrets im Image
  - HEALTHCHECK (wo sinnvoll)
- Compose-Hardening Vorschläge:
  - `read_only: true` (wo möglich)
  - `cap_drop`, `security_opt`, `no-new-privileges`
  - Ressourcenlimits (cpu/mem)
  - Netzwerk-Segmentierung (separate networks)
- Findings als **MUST/SHOULD/NICE** ausgeben.
- Output: `DOCKER_HARDENING_REPORT.md` + „Diff-Vorschläge“ Abschnitt (copy/paste-ready).

**Stop-Regel:** Ohne Delivery-Gate keine mutierenden Änderungen—nur Report/Diff.

