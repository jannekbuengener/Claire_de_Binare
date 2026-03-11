# LOGS_CONCEPT_ANALYSIS

Date: 2025-12-19
Scope: Docs Hub analysis of logs/ vs knowledge/logs/ (no decisions)

## Current usage (observed)

logs/ (Docs Hub root):
- logs/README.md (guidance)
- logs/paper_trading_20251213.log (runtime log)
- logs/systemcheck_20251214_212322.log (system check output)
- logs/daily_reports/report_20251214.md (daily report)

knowledge/logs/:
- knowledge/logs/sessions/session_2025-12-17_rehydration.md
- knowledge/logs/sessions/session_2025-12-17_continuation.md

## Comparison

| Aspect | logs/ | knowledge/logs/ |
|---|---|---|
| Purpose | Generated operational logs and reports | Session logs and knowledge artifacts |
| Canon Status | Non-canonical (per README) | Knowledge (non-governance) |
| Target Audience | Operators / maintainers | Agents / reviewers |
| Typical Contents | Runtime logs, system checks, daily reports | Session summaries, rehydration notes |

## Target Models (decision-ready, not decided)

### Model A: Clear separation (runtime vs knowledge)
Description:
- logs/ stays for generated operational logs and reports.
- knowledge/logs/ stays for session and knowledge logs.

Advantages:
- Clear boundary for runtime vs knowledge artifacts.
- Keeps session logs with other knowledge assets.

Risks:
- Two locations can confuse contributors.
- Requires strong rules in README and index.

Impact on agents:
- Agents must route runtime logs to logs/ and session logs to knowledge/logs/.

### Model B: Consolidation (single logs root)
Description:
- Move knowledge/logs/ into logs/ (or vice versa) and use subfolders.

Advantages:
- Single entrypoint for logs.
- Simpler discovery.

Risks:
- Mixing canonical knowledge with raw logs may blur governance boundaries.
- Requires reindexing and migration.

Impact on agents:
- Agents write all logs to one place with subfolder rules.

### Model C: Status quo + explicit rules
Description:
- Keep both locations and document explicit routing rules.
- Add references in DOCS_HUB_INDEX.md and README.

Advantages:
- Minimal changes.
- Aligns with current usage.

Risks:
- Ambiguity persists if rules are not enforced.

Impact on agents:
- Agents must consult rules before writing logs.

## Notes
- No recommendation made. This document is analysis only.
