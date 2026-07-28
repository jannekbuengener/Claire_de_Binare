# Redis compose digest — `8.8.0-alpine` → `8.8.1-alpine`

**Date:** 2026-07-28  
**Scope:** `infrastructure/compose/compose.blue.yml` image pin only  
**Supersedes Dependabot:** #4161  
**Tool:** Trivy 0.72.0, severity HIGH+CRITICAL, scanners=vuln  

## Images compared

| Role | Ref |
|---|---|
| Old | `redis:8.8.0-alpine@sha256:9d317178eceac8454a2284a9e6df2466b93c745529947f0cd42a0fa9609d7005` |
| New | `redis:8.8.1-alpine@sha256:8096655e437712b07503796fb64d81359256cfcff0ab29d95a7da72863786efb` |

## Vulnerability delta (HIGH/CRITICAL CVE IDs)

| Metric | Count |
|---|---|
| Old | 0 |
| New | 0 |
| Cleared | **0** |
| Introduced | **0** |

No HIGH/CRITICAL findings on either digest under current Trivy DB.

## Boundaries

- File-only compose pin change; no productive Redis start/migration, no BLUE stack mutation in this batch.
- Targeted Trivy delta is merge evidence.
