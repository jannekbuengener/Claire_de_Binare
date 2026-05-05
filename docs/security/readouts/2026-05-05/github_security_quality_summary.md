# GitHub Security and Quality Readout

- Repo: `jannekbuengener/Claire_de_Binare`
- Reference now (UTC): `2026-05-05T13:54:39Z`
- Overall status: **PASS**
- Readable surfaces: `3/3`
- Total normalized alerts: `3247`

## Surface Coverage

| Source | Status | Alerts | Note |
|--------|--------|--------|------|
| `code_scanning` | readable | 2744 | — |
| `dependabot` | readable | 503 | — |
| `secret_scanning` | redacted | redacted | payload-redacted: secret scanning details excluded from artifacts |

## Counts by Source

| Value | Count |
|-------|-------|
| `code_scanning` | 2744 |
| `dependabot` | 503 |

## Counts by Severity

| Value | Count |
|-------|-------|
| `low` | 1120 |
| `medium` | 1112 |
| `high` | 598 |
| `note` | 322 |
| `warning` | 47 |
| `critical` | 41 |
| `error` | 7 |

## Counts by State

| Value | Count |
|-------|-------|
| `open` | 1104 |
| `fixed` | 1096 |
| `dismissed` | 1047 |

## Top Subjects

| Value | Count |
|-------|-------|
| `aiohttp` | 434 |
| `py/clear-text-logging-sensitive-data` | 213 |
| `py/unused-import` | 130 |
| `CVE-2026-27456` | 79 |
| `CVE-2022-0563` | 72 |
| `CVE-2025-14104` | 72 |
| `CVE-2026-3184` | 72 |
| `actions/missing-workflow-permissions` | 54 |
| `py/incomplete-url-substring-sanitization` | 41 |
| `CVE-2018-5709` | 34 |

## Top Components or Paths

| Value | Count |
|-------|-------|
| `library/cdb_allocation` | 222 |
| `library/cdb_market` | 222 |
| `library/cdb_regime` | 222 |
| `library/cdb_risk` | 222 |
| `library/cdb_signal` | 222 |
| `library/cdb_ws` | 222 |
| `library/cdb_execution` | 211 |
| `library/cdb_db_writer` | 133 |
| `grafana/grafana` | 121 |
| `usr/local/bin/gosu` | 90 |

## Coverage Notes

Alle angefragten GitHub-Surfaces waren lesbar.

Secret-Scanning bleibt in der Surface-Coverage sichtbar; payload-abgeleitete Counts und Breakdowns werden dafuer bewusst nicht persistiert.

## Scope Note

- Read-only GitHub-Readout; kein Auto-Fix, kein Dismiss, kein Close.
- Secret-Scanning-Detailfelder werden im Artefakt absichtlich redigiert, damit keine GitHub-seitigen Secret-Kontexte als Klartext persistiert werden.
- `severity=not_provided` bedeutet: GitHub liefert fuer diese Surface keine native Severity.
- `branch=not_provided` bedeutet: GitHub liefert fuer diese Alert-Surface keinen Branch-Kontext.
