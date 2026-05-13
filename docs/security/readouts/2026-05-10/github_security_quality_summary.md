# GitHub Security and Quality Readout

- Repo: `jannekbuengener/Claire_de_Binare`
- Reference now (UTC): `2026-05-10T22:04:47Z`
- Overall status: **PARTIAL**
- Readable surfaces: `2/3`
- Total normalized alerts: `2823`

## Surface Coverage

| Source | Status | Alerts | Note |
|--------|--------|--------|------|
| `code_scanning` | readable | 2823 | — |
| `dependabot` | unavailable | 0 | gh: Resource not accessible by integration (HTTP 403) |
| `secret_scanning` | redacted | redacted | payload-redacted: secret scanning details excluded from artifacts |

## Counts by Source

| Value | Count |
|-------|-------|
| `code_scanning` | 2823 |

## Counts by Severity

| Value | Count |
|-------|-------|
| `medium` | 947 |
| `low` | 879 |
| `high` | 560 |
| `note` | 327 |
| `critical` | 55 |
| `warning` | 47 |
| `error` | 8 |

## Counts by State

| Value | Count |
|-------|-------|
| `dismissed` | 1047 |
| `open` | 928 |
| `fixed` | 848 |

## Top Subjects

| Value | Count |
|-------|-------|
| `py/clear-text-logging-sensitive-data` | 213 |
| `py/unused-import` | 135 |
| `CVE-2026-27456` | 79 |
| `CVE-2022-0563` | 72 |
| `CVE-2025-14104` | 72 |
| `CVE-2026-3184` | 72 |
| `actions/missing-workflow-permissions` | 54 |
| `py/incomplete-url-substring-sanitization` | 41 |
| `CVE-2018-5709` | 34 |
| `CVE-2024-26458` | 34 |

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
| `grafana/grafana` | 125 |
| `usr/local/bin/gosu` | 98 |

## Coverage Notes

Dieses Bild ist partiell. Mindestens eine GitHub-Surface war nicht lesbar:

- `dependabot`: gh: Resource not accessible by integration (HTTP 403)

Secret-Scanning bleibt in der Surface-Coverage sichtbar; payload-abgeleitete Counts und Breakdowns werden dafuer bewusst nicht persistiert.

## Scope Note

- Read-only GitHub-Readout; kein Auto-Fix, kein Dismiss, kein Close.
- Secret-Scanning-Detailfelder werden im Artefakt absichtlich redigiert, damit keine GitHub-seitigen Secret-Kontexte als Klartext persistiert werden.
- `severity=not_provided` bedeutet: GitHub liefert fuer diese Surface keine native Severity.
- `branch=not_provided` bedeutet: GitHub liefert fuer diese Alert-Surface keinen Branch-Kontext.
