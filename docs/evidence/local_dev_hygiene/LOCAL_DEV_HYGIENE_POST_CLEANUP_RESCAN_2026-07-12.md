# Local Dev Hygiene — Post-Cleanup Rescan (redacted)

Refs: #3999 · #4001 · PR #4002
Scan as of (UTC): `2026-07-12T19:48:38.1614490Z`

## Post-Cleanup Gesamtbaseline

- Total: **21.79 GB** / 194,058 files / 33,297 directories
- Completeness: partial
- Raw inventory (gitignored): `artifacts/local-dev-hygiene/post-cleanup-rescan-2026-07-12/workspace_inventory.json`

## Baseline-Vergleich

| Baseline | GB | Files | Directories | Completeness |
|----------|---:|------:|------------:|--------------|
| Explorer screenshot | 134.27 | 414,174 | 71,093 | n/a |
| Pre-cleanup scan (2026-07-12T18:10:49Z) | 120.06 | 207,113 | 45,542 | partial |
| **Post-cleanup scan** | **21.79** | **194,058** | **33,297** | partial |

**Gemessene Änderung Pre→Post:** −98.27 GB (105,512,084,429 bytes), −13,055 files, −12,245 directories.

## npm-cache (#4001)

- Pfad vorhanden: ja
- Gemessen: 290,025,160 bytes (0.27 GB)
- #4001 Nachher-Baseline: 290,025,604 bytes
- Match: ja

## Ollama

- `D:\Dev\AI\Ollama` existiert: nein (live Test-Path + Scan)
- `ollama_models` Pattern-Hits: 0
- Manuelle Entfernung per Scan bestätigt: ja (Pfad fehlt, keine Pattern-Hits)

## Root-Completeness

| Root | Status | GB | Δ vs Pre | Reparse skip | Access err |
|------|--------|---:|---------:|-------------:|-----------:|
| `D:\Dev\AI` | partial | 0.39 | 39.83 | 0 | 3 |
| `D:\Dev\Backups` | partial | 8.02 | 0.0 | 0 | 50 |
| `D:\Dev\Workspaces\Repos` | partial | 7.4 | 0.0 | 20 | 50 |
| `D:\Dev\Tools` | partial | 5.98 | 58.44 | 0 | 27 |

## Top-Verbraucher (Post-Cleanup)

### D:\Dev\AI (0.39 GB)
- `D:\Dev\AI\Claude` — 0.388 GB
- `D:\Dev\AI\OpenAI` — 0.006 GB
- `D:\Dev\AI\AgentMemory` — 0.0 GB

### D:\Dev\Backups (8.02 GB)
- `D:\Dev\Backups\extensions` — 7.913 GB
- `D:\Dev\Backups\docker_reinstall_20251231_075507` — 0.109 GB
- `D:\Dev\Backups\Claude` — 0.0 GB

### D:\Dev\Workspaces\Repos (7.4 GB)
- `D:\Dev\Workspaces\Repos\Claire_de_Binare` — 6.556 GB
- `D:\Dev\Workspaces\Repos\sample-brain` — 0.129 GB
- `D:\Dev\Workspaces\Repos\Claire_de_Binare-wt-diag-telemetry-preflight` — 0.103 GB
- `D:\Dev\Workspaces\Repos\Claire_de_Binare-p1-telemetry` — 0.103 GB
- `D:\Dev\Workspaces\Repos\Claire_de_Binare__arvp-3912-closeout` — 0.103 GB

### D:\Dev\Tools (5.98 GB)
- `D:\Dev\Tools\PowerShell` — 2.966 GB
- `D:\Dev\Tools\GitHub` — 2.4 GB
- `D:\Dev\Tools\npm-cache` — 0.27 GB
- `D:\Dev\Tools\trivy` — 0.16 GB
- `D:\Dev\Tools\Node` — 0.086 GB

## Git-Repositories & Worktrees

- Git repositories: 21
- Worktrees (all PROTECTED): 21

## Restunsicherheiten

- Partial scan completeness on all four roots (access errors and/or reparse skips).
- Pre-cleanup byte total derived from GB aggregate; minor rounding vs exact bytes.
- Ollama system uninstall not verified; only D:\Dev\AI\Ollama path absence.
- No further cleanup recommendations in this slice.

Aggregated metadata only; no secret paths, full file lists, or file contents.
